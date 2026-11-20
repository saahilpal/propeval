import asyncio
from uuid import uuid4

import pytest

from backend.app.domain.models import LLMResponse
from backend.app.storage.budget import reserve_budget
from backend.app.storage.db import close_db_pool, get_db_pool
from backend.app.storage.ledger import get_completed_ledger, record_completed_ledger
from backend.app.storage.queue import (
    claim_job,
    fenced_complete_job,
    fenced_persist_turn,
)


@pytest.mark.asyncio
async def test_worker_sigkill_reclamation_and_fencing():
    pool = await get_db_pool()
    tenant_id = uuid4()
    run_id = uuid4()
    prompt_id = uuid4()
    suite_id = uuid4()
    fixture_id = uuid4()

    async with pool.acquire() as conn:
        # 1. Seed tenant and prerequisite rows
        await conn.execute(
            "INSERT INTO tenants (id, name, encrypted_dek) VALUES ($1, 'Test Tenant', $2)",
            tenant_id,
            b"fake_dek_bytes_32_bytes_long!!",
        )
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", str(tenant_id))

        sha_64 = "a" * 64
        await conn.execute(
            """
            INSERT INTO prompt_versions (id, tenant_id, name, version_tag, system_prompt, model_provider, model_id, content_sha256)
            VALUES ($1, $2, 'Test Prompt', 'v1.0', 'Prompt text', 'openai', 'gpt-4o', $3)
            """,
            prompt_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO project_fixtures (id, tenant_id, project_name, city, rera_id, effective_from, facts_json, content_sha256)
            VALUES ($1, $2, 'Lodha Wakad', 'Pune', 'P52100012345', '2026-11-01', '{"price": 12000000}'::jsonb, $3)
            """,
            fixture_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO scenario_suites (id, tenant_id, name, suite_tier, version_tag, scenarios_json, scenario_count, content_sha256)
            VALUES ($1, $2, 'Smoke Suite', 'smoke_pr', 'v1', '[]'::jsonb, 1, $3)
            """,
            suite_id,
            tenant_id,
            sha_64,
        )
        await conn.execute(
            """
            INSERT INTO eval_runs (id, tenant_id, baseline_prompt_id, candidate_prompt_id, suite_id, fixture_id,
                                  grader_prompt_sha256, max_budget_usd, simulator_model_id, judge_model_id)
            VALUES ($1, $2, $3, $3, $4, $5, $6, 5.00, 'sim-model', 'judge-model')
            """,
            run_id,
            tenant_id,
            prompt_id,
            suite_id,
            fixture_id,
            sha_64,
        )

        # 2. Enqueue an eval_job
        job_id = uuid4()
        await conn.execute(
            """
            INSERT INTO eval_jobs (id, tenant_id, run_id, scenario_id, prompt_role, prompt_version_id, status)
            VALUES ($1, $2, $3, 'scen-01', 'baseline', $4, 'QUEUED')
            """,
            job_id,
            tenant_id,
            run_id,
            prompt_id,
        )

        # 3. Worker 1 claims job with a short lease of 1 second
        job1 = await claim_job(conn, worker_id="worker-crash-01", lease_sec=1)
        assert job1 is not None
        assert job1.id == job_id
        assert job1.fence_token == 1
        assert job1.worker_id == "worker-crash-01"

        # Worker 1 reserves budget
        res_id1 = await reserve_budget(
            conn,
            tenant_id=tenant_id,
            run_id=run_id,
            job_id=job_id,
            fence_token=job1.fence_token,
            est_cost_usd=0.05,
        )
        assert res_id1 is not None

        # Worker 1 persists turn 1 and records into ledger
        turn1_ok = await fenced_persist_turn(
            conn,
            job_id=job_id,
            tenant_id=tenant_id,
            fence_token=job1.fence_token,
            turn_index=1,
            fsm_state="INTRO",
            buyer_raw="Namaste",
            buyer_perturbed="Namaste",
            agent_text="Hello, how can I help?",
            tool_calls=[],
            tool_outcomes=[],
            input_tokens=10,
            output_tokens=15,
            cost_usd=0.001,
        )
        assert turn1_ok is True

        await record_completed_ledger(
            conn,
            tenant_id=tenant_id,
            idempotency_key=f"turn_{job_id}_1",
            provider="deterministic",
            model_id="deterministic-v1",
            response=LLMResponse(text="Hello, how can I help?", input_tokens=10, output_tokens=15, cost_usd=0.001),
        )

        # 4. SIMULATE SIGKILL: Worker 1 dies immediately without cleaning up or heartbeating
        # Wait 1.2s so lease expires
        await asyncio.sleep(1.2)

        # 5. Worker 2 wakes up and reclaims the expired lease
        job2 = await claim_job(conn, worker_id="worker-alive-02", lease_sec=60)
        assert job2 is not None
        assert job2.id == job_id
        assert job2.fence_token == 2  # Fence advanced!
        assert job2.worker_id == "worker-alive-02"

        # 6. Verify Worker 1's orphaned reservation was automatically RELEASED
        res_status = await conn.fetchval(
            "SELECT status FROM budget_reservations WHERE id = $1", res_id1
        )
        assert res_status == "RELEASED", f"Expected RELEASED, got {res_status}"

        # 7. Verify stale Worker 1 attempting fenced persist is rejected by fence_token CAS
        zombie_turn_ok = await fenced_persist_turn(
            conn,
            job_id=job_id,
            tenant_id=tenant_id,
            fence_token=1,  # Stale fence token from dead Worker 1
            turn_index=2,
            fsm_state="BUDGET",
            buyer_raw="My budget is 1.2 cr",
            buyer_perturbed="My budget is 1.2 cr",
            agent_text="Great",
            tool_calls=[],
            tool_outcomes=[],
            input_tokens=20,
            output_tokens=10,
            cost_usd=0.002,
        )
        assert zombie_turn_ok is False, "Zombie worker must be rejected by fence_token CAS"

        # 8. Verify Worker 2 recovers turn 1 from ledger ($0 duplicate cost)
        cached_turn1 = await get_completed_ledger(conn, tenant_id=tenant_id, idempotency_key=f"turn_{job_id}_1")
        assert cached_turn1 is not None
        assert cached_turn1.text == "Hello, how can I help?"

        # 9. Worker 2 completes the job cleanly
        done = await fenced_complete_job(
            conn,
            job_id=job_id,
            fence_token=2,
            overall_pass=True,
            hard_gate_pass=True,
            extraction_f1=1.0,
        )
        assert done is True

    await close_db_pool()
