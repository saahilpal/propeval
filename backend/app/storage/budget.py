from __future__ import annotations

from uuid import UUID

import asyncpg


async def reserve_budget(
    conn: asyncpg.Connection,
    tenant_id: str | UUID,
    run_id: str | UUID,
    job_id: str | UUID,
    fence_token: int,
    est_cost_usd: float,
) -> UUID:
    """Create an ACTIVE budget_reservation row.

    Raises RuntimeError if run's total spent + active reservations exceeds max_budget_usd.
    """
    row = await conn.fetchrow(
        """
        SELECT max_budget_usd, spent_usd,
               COALESCE((SELECT SUM(reserved_usd) FROM budget_reservations WHERE run_id = $1 AND status = 'ACTIVE'), 0) as active_reserved
        FROM eval_runs
        WHERE id = $1 AND tenant_id = $2
        FOR UPDATE
        """,
        UUID(str(run_id)),
        UUID(str(tenant_id)),
    )
    if not row:
        raise ValueError(f"Run {run_id} not found for tenant {tenant_id}")

    max_budget = float(row["max_budget_usd"])
    spent = float(row["spent_usd"])
    active_res = float(row["active_reserved"])

    if (spent + active_res + est_cost_usd) > max_budget:
        raise RuntimeError(
            f"Budget exceeded for run {run_id}: spent=${spent:.4f} + active=${active_res:.4f} + est=${est_cost_usd:.4f} > max=${max_budget:.4f}"
        )

    res_id = await conn.fetchval(
        """
        INSERT INTO budget_reservations (tenant_id, run_id, job_id, fence_token, reserved_usd, status)
        VALUES ($1, $2, $3, $4, $5, 'ACTIVE')
        RETURNING id
        """,
        UUID(str(tenant_id)),
        UUID(str(run_id)),
        UUID(str(job_id)),
        fence_token,
        est_cost_usd,
    )
    if not res_id:
        raise RuntimeError(f"Failed to create budget reservation for run {run_id}")
    return UUID(str(res_id))


async def settle_budget(
    conn: asyncpg.Connection,
    reservation_id: str | UUID,
    actual_cost_usd: float,
) -> None:
    """Mark budget_reservation as SETTLED and atomically update eval_runs.spent_usd."""
    res = await conn.fetchrow(
        """
        UPDATE budget_reservations
        SET status = 'SETTLED'
        WHERE id = $1 AND status = 'ACTIVE'
        RETURNING run_id, tenant_id
        """,
        UUID(str(reservation_id)),
    )
    if res:
        await conn.execute(
            """
            UPDATE eval_runs
            SET spent_usd = spent_usd + $1
            WHERE id = $2 AND tenant_id = $3
            """,
            actual_cost_usd,
            res["run_id"],
            res["tenant_id"],
        )


create_budget_reservation = reserve_budget
settle_budget_reservation = settle_budget

__all__ = [
    "reserve_budget",
    "settle_budget",
    "create_budget_reservation",
    "settle_budget_reservation",
]


