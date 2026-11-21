from __future__ import annotations

import json
from typing import Any
from uuid import UUID

import asyncpg

from backend.app.domain.models import EvalJob


async def claim_job(
    conn: asyncpg.Connection,
    worker_id: str,
    lease_sec: int = 60,
    max_per_tenant: int = 20,
) -> EvalJob | None:
    """Claim the next evaluation job using the SECURITY DEFINER claim_next_eval_job function.

    Enforces SKIP LOCKED, increments fence_token, and releases stale reservations.
    """
    row = await conn.fetchrow(
        "SELECT * FROM claim_next_eval_job($1, $2, $3)",
        worker_id,
        lease_sec,
        max_per_tenant,
    )
    if not row:
        return None

    return EvalJob(
        id=row["id"],
        tenant_id=row["tenant_id"],
        run_id=row["run_id"],
        scenario_id=row["scenario_id"],
        prompt_role=row["prompt_role"],
        prompt_version_id=row["prompt_version_id"],
        trial_index=row["trial_index"],
        priority=row["priority"],
        status=row["status"],
        worker_id=row["worker_id"],
        fence_token=row["fence_token"],
        attempt=row["attempt"],
        max_attempts=row["max_attempts"],
        run_after=row["run_after"],
        lease_expires_at=row["lease_expires_at"],
    )


async def extend_lease(
    conn: asyncpg.Connection,
    job_id: UUID,
    fence_token: int,
    lease_sec: int = 60,
) -> bool:
    """Extend lease expiration for an active job if fence_token matches."""
    result = await conn.execute(
        """
        UPDATE eval_jobs
        SET lease_expires_at = now() + make_interval(secs => $1),
            updated_at = now()
        WHERE id = $2 AND fence_token = $3 AND status = 'RUNNING'
        """,
        lease_sec,
        job_id,
        fence_token,
    )
    return result == "UPDATE 1"


async def fenced_persist_turn(
    conn: asyncpg.Connection,
    job_id: UUID,
    tenant_id: UUID,
    fence_token: int,
    turn_index: int,
    fsm_state: str,
    buyer_raw: str,
    buyer_perturbed: str,
    agent_text: str,
    tool_calls: list[dict[str, Any]],
    tool_outcomes: list[dict[str, Any]],
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    ttft_ms: int = 0,
    total_ms: int = 0,
) -> bool:
    """Persist a conversation turn under the fence_token CAS contract.

    Fails if the job's fence_token has moved (meaning a new worker reclaimed the lease).
    """
    # Verify fence_token is still valid
    valid = await conn.fetchval(
        "SELECT 1 FROM eval_jobs WHERE id = $1 AND fence_token = $2 AND status = 'RUNNING'",
        job_id,
        fence_token,
    )
    if not valid:
        return False

    await conn.execute(
        """
        INSERT INTO conversation_turns (
            tenant_id, job_id, turn_index, fsm_state, buyer_raw_text, buyer_perturbed_text,
            agent_text, tool_calls, tool_outcomes, ttft_ms, total_ms, input_tokens, output_tokens, cost_usd
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, $10, $11, $12, $13, $14)
        ON CONFLICT (job_id, turn_index) DO NOTHING
        """,
        tenant_id,
        job_id,
        turn_index,
        fsm_state,
        buyer_raw,
        buyer_perturbed,
        agent_text,
        json.dumps(tool_calls),
        json.dumps(tool_outcomes),
        ttft_ms,
        total_ms,
        input_tokens,
        output_tokens,
        cost_usd,
    )
    return True


async def fenced_complete_job(
    conn: asyncpg.Connection,
    job_id: UUID,
    fence_token: int,
    overall_pass: bool,
    hard_gate_pass: bool,
    extraction_f1: float = 1.0,
    cost_usd: float = 0.0,
    total_tokens: int = 0,
    p50_ttft_ms: int = 0,
    p95_ttft_ms: int = 0,
) -> bool:
    """Complete an eval_job if fence_token matches."""
    result = await conn.execute(
        """
        UPDATE eval_jobs
        SET status = 'COMPLETED',
            overall_pass = $1,
            hard_gate_pass = $2,
            extraction_f1 = $3,
            cost_usd = $4,
            total_tokens = $5,
            p50_ttft_ms = $6,
            p95_ttft_ms = $7,
            updated_at = now()
        WHERE id = $8 AND fence_token = $9 AND status = 'RUNNING'
        """,
        overall_pass,
        hard_gate_pass,
        extraction_f1,
        cost_usd,
        total_tokens,
        p50_ttft_ms,
        p95_ttft_ms,
        job_id,
        fence_token,
    )
    return result == "UPDATE 1"
