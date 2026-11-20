import json

import pytest

from backend.app.storage.db import close_db_pool, get_db_pool


@pytest.mark.asyncio
async def test_split_partial_indexes():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        await conn.execute("SET enable_seqscan = off")
        # Check queued jobs index
        plan_queued_raw = await conn.fetchval(
            "EXPLAIN (FORMAT JSON) SELECT * FROM eval_jobs WHERE status = 'QUEUED' ORDER BY priority DESC, run_after ASC"
        )
        plan_queued = json.loads(plan_queued_raw)
        plan_str = json.dumps(plan_queued)
        assert "idx_eval_jobs_queued" in plan_str, f"Expected idx_eval_jobs_queued in plan: {plan_str}"

        # Check expired lease index
        plan_expired_raw = await conn.fetchval(
            "EXPLAIN (FORMAT JSON) SELECT * FROM eval_jobs WHERE status = 'RUNNING' AND lease_expires_at < now()"
        )
        plan_expired = json.loads(plan_expired_raw)
        plan_str = json.dumps(plan_expired)
        assert "idx_eval_jobs_expired_lease" in plan_str, f"Expected idx_eval_jobs_expired_lease in plan: {plan_str}"

    await close_db_pool()
