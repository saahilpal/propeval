from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from backend.app.engine.worker import release_worker_jobs
from backend.app.main import app
from backend.app.storage.db import get_pool


@pytest.mark.asyncio
async def test_empty_scenario_suite_returns_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/suites",
            json={
                "name": "empty_test_suite",
                "suite_tier": "smoke_pr",
                "version_tag": "v1.0",
                "scenarios_json": [],
            },
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "empty" in data.get("detail", "").lower()


@pytest.mark.asyncio
async def test_trials_k_boundary_validation_422():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Test trials_k = 0 (below min 1)
        resp_0 = await ac.post(
            "/api/v1/runs",
            json={
                "baseline_prompt_id": str(uuid.uuid4()),
                "candidate_prompt_id": str(uuid.uuid4()),
                "suite_id": str(uuid.uuid4()),
                "fixture_id": str(uuid.uuid4()),
                "trials_k": 0,
            },
        )
        assert resp_0.status_code == 422

        # Test trials_k = 11 (above max 10)
        resp_11 = await ac.post(
            "/api/v1/runs",
            json={
                "baseline_prompt_id": str(uuid.uuid4()),
                "candidate_prompt_id": str(uuid.uuid4()),
                "suite_id": str(uuid.uuid4()),
                "fixture_id": str(uuid.uuid4()),
                "trials_k": 11,
            },
        )
        assert resp_11.status_code == 422


@pytest.mark.asyncio
async def test_revoked_api_key_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Valid request but with revoked API key
        resp = await ac.get(
            "/api/v1/prompts",
            headers={"X-API-Key": "revoked-key-12345"},
        )
        assert resp.status_code == 401
        data = resp.json()
        assert "revoked" in data.get("detail", "").lower()

        # Bearer token format with stale key
        resp_bearer = await ac.get(
            "/api/v1/prompts",
            headers={"Authorization": "Bearer stale-test-key-expired"},
        )
        assert resp_bearer.status_code == 401


@pytest.mark.asyncio
async def test_idempotent_duplicate_prompt_registration_returns_200():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        body = {
            "name": f"idempotent_test_{uuid.uuid4().hex[:6]}",
            "version_tag": "v1.0.0",
            "system_prompt": "You are a helpful real estate assistant in Wakad.",
            "model_provider": "deterministic",
            "model_id": "test-v1",
            "temperature": 0.0,
            "tools_schema": [],
        }

        # First registration
        resp1 = await ac.post("/api/v1/prompts", json=body)
        assert resp1.status_code == 200
        data1 = resp1.json()

        # Second registration with identical content (same SHA-256)
        resp2 = await ac.post("/api/v1/prompts", json=body)
        assert resp2.status_code == 200
        data2 = resp2.json()

        # ID should be stable
        assert data1["id"] == data2["id"]
        assert data1["content_sha256"] == data2["content_sha256"]


@pytest.mark.asyncio
async def test_malformed_transcript_import_sanitization():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Import with malformed surrogates / null byte / Devanagari mix
        body = {
            "suite_name": f"import_test_{uuid.uuid4().hex[:6]}",
            "version_tag": "v1.0",
            "recordings": [
                {
                    "raw_transcript": "Customer: १२ लाख \x00 बजट hai. Phone 9876543210.",
                    "detected_language": "hinglish",
                }
            ],
        }
        resp = await ac.post("/api/v1/suites/replay/import", json=body)
        assert resp.status_code == 200
        data = resp.json()
        assert data["scenario_count"] == 1
        # Phone should be redacted per DPDP, Devanagari numerals preserved
        imported_text = data["scenarios_json"][0]["raw_text"]
        assert "१२ लाख" in imported_text
        assert "9876543210" not in imported_text
        assert "\x00" not in imported_text


@pytest.mark.asyncio
async def test_worker_graceful_shutdown_releases_running_jobs():
    pool = await get_pool()
    worker_id = f"test_worker_{uuid.uuid4().hex[:8]}"
    tenant_id = uuid.uuid4()
    prompt_id = uuid.uuid4()
    suite_id = uuid.uuid4()
    fixture_id = uuid.uuid4()
    run_id = uuid.uuid4()
    job_id = uuid.uuid4()
    sha_64 = uuid.uuid4().hex + uuid.uuid4().hex

    async with pool.acquire() as conn:
        # Seed isolated test tenant
        await conn.execute(
            "INSERT INTO tenants (id, name, encrypted_dek) VALUES ($1, 'Shutdown Tenant', $2)",
            tenant_id,
            b"fake_dek_bytes_32_bytes_long!!",
        )
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", str(tenant_id))

        await conn.execute(
            """
            INSERT INTO prompt_versions (id, tenant_id, name, version_tag, system_prompt, model_provider, model_id, content_sha256)
            VALUES ($1, $2, 'Shutdown Test Prompt', 'v1.0', 'Prompt', 'deterministic', 'test-v1', $3)
            """,
            prompt_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO project_fixtures (id, tenant_id, project_name, city, rera_id, effective_from, facts_json, content_sha256)
            VALUES ($1, $2, 'Test Project', 'Pune', 'P52100099999', '2026-11-01', '{"price": 10000000}'::jsonb, $3)
            """,
            fixture_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO scenario_suites (id, tenant_id, name, suite_tier, version_tag, scenarios_json, scenario_count, content_sha256)
            VALUES ($1, $2, 'Shutdown Suite', 'smoke_pr', 'v1', '[]'::jsonb, 1, $3)
            """,
            suite_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO eval_runs (
                id, tenant_id, baseline_prompt_id, candidate_prompt_id, suite_id, fixture_id,
                grader_prompt_sha256, max_budget_usd, simulator_model_id, judge_model_id
            ) VALUES (
                $1, $2, $3, $3, $4, $5, $6, 1.00, 'sim-model', 'judge-model'
            )
            """,
            run_id,
            tenant_id,
            prompt_id,
            suite_id,
            fixture_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO eval_jobs (
                id, tenant_id, run_id, scenario_id, prompt_role, prompt_version_id,
                status, worker_id, fence_token
            ) VALUES (
                $1, $2, $3, 'shutdown_scen_1', 'baseline', $4,
                'RUNNING', $5, 1
            )
            """,
            job_id,
            tenant_id,
            run_id,
            prompt_id,
            worker_id,
        )

    try:
        # Call release_worker_jobs (simulating SIGTERM handler)
        released = await release_worker_jobs(pool, worker_id)
        assert released >= 1

        # Verify job is reset to QUEUED with worker_id = NULL
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT status, worker_id FROM eval_jobs WHERE id = $1::uuid", job_id
            )
            assert row is not None
            assert row["status"] == "QUEUED"
            assert row["worker_id"] is None
    finally:
        async with pool.acquire() as conn:
            await conn.execute("DELETE FROM tenants WHERE id = $1::uuid", tenant_id)
