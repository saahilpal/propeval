from __future__ import annotations

import asyncio
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.main import app
from backend.app.storage.budget import reserve_budget
from backend.app.storage.db import get_pool
from backend.app.storage.queue import claim_job


@pytest.fixture
async def seeded_eval_entities():
    """Seed test tenant and related entities for eval run creation."""
    pool = await get_pool()
    tenant_id = uuid.uuid4()
    prompt_id = uuid.uuid4()
    suite_id = uuid.uuid4()
    fixture_id = uuid.uuid4()
    sha_64 = "f" * 64

    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO tenants (id, name, encrypted_dek)
            VALUES ($1, 'Concurrency Test Tenant', '\\x01020304')
            ON CONFLICT (id) DO NOTHING
            """,
            tenant_id,
        )
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", str(tenant_id))

        await conn.execute(
            """
            INSERT INTO prompt_versions (id, tenant_id, name, version_tag, system_prompt, model_provider, model_id, content_sha256)
            VALUES ($1, $2, 'Prompt V1', 'v1.0.0', 'System prompt', 'deterministic', 'deterministic-v1', $3)
            """,
            prompt_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO project_fixtures (id, tenant_id, project_name, city, rera_id, effective_from, facts_json, content_sha256)
            VALUES ($1, $2, 'Godrej Woods', 'Gurugram', 'HRERA-PKL-123', '2026-11-01', '{"price": 15000000}'::jsonb, $3)
            """,
            fixture_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO scenario_suites (id, tenant_id, name, suite_tier, version_tag, scenarios_json, scenario_count, content_sha256)
            VALUES ($1, $2, 'Concurrency Suite', 'smoke_pr', 'v1.0.0', '[{"id": "scen_1"}]'::jsonb, 1, $3)
            """,
            suite_id,
            tenant_id,
            sha_64,
        )
        await conn.execute("SELECT set_config('app.current_tenant_id', '', false)")

    yield {
        "tenant_id": str(tenant_id),
        "prompt_id": str(prompt_id),
        "suite_id": str(suite_id),
        "fixture_id": str(fixture_id),
    }

    # Clean up test tenant and cascade delete runs & queue jobs
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM tenants WHERE id = $1", tenant_id)


@pytest.mark.asyncio
async def test_idempotency_key_burst_creates_single_run(seeded_eval_entities):
    """10 concurrent requests with the identical Idempotency-Key create exactly 1 eval run."""
    entities = seeded_eval_entities
    tenant_id = entities["tenant_id"]
    shared_key = f"idemp-burst-{uuid.uuid4().hex}"

    req_body = {
        "baseline_prompt_id": entities["prompt_id"],
        "candidate_prompt_id": entities["prompt_id"],
        "suite_id": entities["suite_id"],
        "fixture_id": entities["fixture_id"],
        "trials_k": 1,
        "max_budget_usd": 1.00,
    }

    async def fire_request():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.post(
                "/api/v1/runs",
                json=req_body,
                headers={"X-Tenant-ID": tenant_id, "Idempotency-Key": shared_key},
            )

    # Burst of 10 concurrent requests
    responses = await asyncio.gather(*[fire_request() for _ in range(10)])

    # All must return HTTP 200
    for r in responses:
        assert r.status_code == 200

    run_ids = {r.json()["id"] for r in responses}
    # Exactly one run ID across all responses
    assert len(run_ids) == 1, f"Expected 1 unique run ID, got: {run_ids}"

    # Verify database has exactly 1 run for this tenant
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval(
            "SELECT count(*) FROM eval_runs WHERE tenant_id = $1::uuid AND id = $2::uuid",
            uuid.UUID(tenant_id),
            uuid.UUID(run_ids.pop()),
        )
        assert count == 1


@pytest.mark.asyncio
async def test_idempotency_conflict_returns_422(seeded_eval_entities):
    """Reusing an Idempotency-Key with different payload parameters returns HTTP 422."""
    entities = seeded_eval_entities
    tenant_id = entities["tenant_id"]
    shared_key = f"idemp-conflict-{uuid.uuid4().hex}"

    req_body_1 = {
        "baseline_prompt_id": entities["prompt_id"],
        "candidate_prompt_id": entities["prompt_id"],
        "suite_id": entities["suite_id"],
        "fixture_id": entities["fixture_id"],
        "trials_k": 1,
        "max_budget_usd": 1.00,
    }

    req_body_2 = dict(req_body_1)
    req_body_2["max_budget_usd"] = 5.00  # Altered payload

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post(
            "/api/v1/runs",
            json=req_body_1,
            headers={"X-Tenant-ID": tenant_id, "Idempotency-Key": shared_key},
        )
        assert r1.status_code == 200

        r2 = await client.post(
            "/api/v1/runs",
            json=req_body_2,
            headers={"X-Tenant-ID": tenant_id, "Idempotency-Key": shared_key},
        )
        assert r2.status_code == 422
        assert "Idempotency conflict" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_sigkill_tight_budget_reclamation():
    """Worker SIGKILL under tight budget ($0.05): claim_next_eval_job releases orphaned reservation."""
    pool = await get_pool()
    tenant_id = uuid.uuid4()
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()
    prompt_id = uuid.uuid4()
    suite_id = uuid.uuid4()
    fixture_id = uuid.uuid4()
    sha_64 = "e" * 64

    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO tenants (id, name, encrypted_dek) VALUES ($1, 'Budget Tenant', '\\x0102')",
                tenant_id,
            )
            await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", str(tenant_id))

            await conn.execute(
                """
                INSERT INTO prompt_versions (id, tenant_id, name, version_tag, system_prompt, model_provider, model_id, content_sha256)
                VALUES ($1, $2, 'Prompt', 'v1', 'Sys', 'deterministic', 'det-v1', $3)
                """,
                prompt_id,
                tenant_id,
                sha_64,
            )
            await conn.execute(
                """
                INSERT INTO project_fixtures (id, tenant_id, project_name, city, rera_id, effective_from, facts_json, content_sha256)
                VALUES ($1, $2, 'Project', 'City', 'RERA1', '2026-11-01', '{}'::jsonb, $3)
                """,
                fixture_id,
                tenant_id,
                sha_64,
            )
            await conn.execute(
                """
                INSERT INTO scenario_suites (id, tenant_id, name, suite_tier, version_tag, scenarios_json, scenario_count, content_sha256)
                VALUES ($1, $2, 'Suite', 'smoke_pr', 'v1', '[]'::jsonb, 1, $3)
                """,
                suite_id,
                tenant_id,
                sha_64,
            )

            # Create run with strict $0.05 budget
            await conn.execute(
                """
                INSERT INTO eval_runs (id, tenant_id, baseline_prompt_id, candidate_prompt_id, suite_id, fixture_id,
                                       grader_prompt_sha256, simulator_model_id, judge_model_id, max_budget_usd, status)
                VALUES ($1, $2, $3, $3, $4, $5, $6, 'deterministic', 'deterministic-judge', 0.05, 'RUNNING')
                """,
                run_id,
                tenant_id,
                prompt_id,
                suite_id,
                fixture_id,
                sha_64,
            )

            # Worker 1 reserves $0.035 under fence_token 1, then crashes (lease expired in past)
            # Use priority 999 to guarantee claim_next_eval_job picks this exact job
            await conn.execute(
                """
                INSERT INTO eval_jobs (id, tenant_id, run_id, scenario_id, prompt_role, prompt_version_id,
                                       priority, status, worker_id, fence_token, lease_expires_at)
                VALUES ($1, $2, $3, 'scen_1', 'candidate', $4, 999, 'RUNNING', 'worker-crashed', 1, now() - interval '10 seconds')
                """,
                job_id,
                tenant_id,
                run_id,
                prompt_id,
            )
            # Orphaned active reservation from crashed fence_token 1
            await reserve_budget(conn, tenant_id=tenant_id, run_id=run_id, job_id=job_id, fence_token=1, est_cost_usd=0.035)

            # Attempting a second reservation without reclamation would fail ($0.035 + $0.035 = $0.07 > $0.05)
            with pytest.raises(RuntimeError):
                await reserve_budget(conn, tenant_id=tenant_id, run_id=run_id, job_id=uuid.uuid4(), fence_token=1, est_cost_usd=0.035)

            # New worker claims the job: claim_next_eval_job must auto-release old reservation
            reclaimed_job = await claim_job(conn, worker_id="worker-survivor", lease_sec=60)
            assert reclaimed_job is not None
            assert reclaimed_job.fence_token == 2

            # Verify old reservation is marked RELEASED
            res_status = await conn.fetchval(
                "SELECT status FROM budget_reservations WHERE job_id = $1 AND fence_token = 1",
                job_id,
            )
            assert res_status == "RELEASED"

            # Now worker 2 can reserve budget under fence_token 2 within the $0.05 cap!
            res_id_2 = await reserve_budget(conn, tenant_id=tenant_id, run_id=run_id, job_id=job_id, fence_token=2, est_cost_usd=0.035)
            assert res_id_2 is not None
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM tenants WHERE id = $1", tenant_id)


@pytest.mark.asyncio
async def test_sse_stream_handles_stale_and_negative_event_ids(seeded_eval_entities):
    """SSE stream handles negative or malformed Last-Event-ID and terminates cleanly when run completes."""
    entities = seeded_eval_entities
    tenant_id = entities["tenant_id"]
    pool = await get_pool()
    run_id = uuid.uuid4()
    sha_64 = "d" * 64

    # Seed completed run with 2 events
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", tenant_id)
        await conn.execute(
            """
            INSERT INTO eval_runs (id, tenant_id, baseline_prompt_id, candidate_prompt_id, suite_id, fixture_id,
                                   grader_prompt_sha256, simulator_model_id, judge_model_id, max_budget_usd, status)
            VALUES ($1, $2::uuid, $3::uuid, $3::uuid, $4::uuid, $5::uuid, $6, 'deterministic', 'deterministic-judge', 1.00, 'PASSED')
            """,
            run_id,
            tenant_id,
            entities["prompt_id"],
            entities["suite_id"],
            entities["fixture_id"],
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO run_events (tenant_id, run_id, event_type, payload)
            VALUES ($1::uuid, $2, 'job.completed', '{"job_id": "j1"}'::jsonb),
                   ($1::uuid, $2, 'run.completed', '{"status": "PASSED"}'::jsonb)
            """,
            tenant_id,
            run_id,
        )
        await conn.execute("SELECT set_config('app.current_tenant_id', '', false)")

    # 1. Connect with negative Last-Event-ID: -5
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/api/v1/runs/{run_id}/stream",
            headers={"X-Tenant-ID": tenant_id, "Last-Event-ID": "-5"},
        )
        assert resp.status_code == 200
        text = resp.text
        assert "event: job.completed" in text
        assert "event: run.completed" in text

    # 2. Connect with non-numeric Last-Event-ID: "invalid_id"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_invalid = await client.get(
            f"/api/v1/runs/{run_id}/stream",
            headers={"X-Tenant-ID": tenant_id, "Last-Event-ID": "invalid_id"},
        )
        assert resp_invalid.status_code == 200
        assert "event: run.completed" in resp_invalid.text
