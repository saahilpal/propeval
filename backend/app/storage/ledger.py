from __future__ import annotations

import json
from uuid import UUID

import asyncpg

from backend.app.domain.models import LLMResponse


async def get_completed_ledger(
    conn: asyncpg.Connection,
    tenant_id: str | UUID,
    idempotency_key: str,
) -> LLMResponse | None:
    """Check if an LLM call was already completed and cached in llm_call_ledger."""
    row = await conn.fetchrow(
        """
        SELECT response_payload, input_tokens, output_tokens, cost_usd, provider, model_id
        FROM llm_call_ledger
        WHERE tenant_id = $1 AND idempotency_key = $2 AND status = 'COMPLETED'
        """,
        UUID(str(tenant_id)),
        idempotency_key,
    )
    if not row or not row["response_payload"]:
        return None

    payload = row["response_payload"]
    if isinstance(payload, str):
        payload = json.loads(payload)

    return LLMResponse(
        text=payload.get("text", ""),
        tool_calls=payload.get("tool_calls", []),
        input_tokens=row["input_tokens"] or 0,
        output_tokens=row["output_tokens"] or 0,
        ttft_ms=payload.get("ttft_ms", 0),
        total_ms=payload.get("total_ms", 0),
        cost_usd=float(row["cost_usd"] or 0.0),
        provider=row["provider"],
        model_id=row["model_id"],
    )


async def record_completed_ledger(
    conn: asyncpg.Connection,
    tenant_id: str | UUID,
    idempotency_key: str,
    provider: str,
    model_id: str,
    response: LLMResponse,
) -> None:
    """Record completed LLM call in llm_call_ledger."""
    payload = json.dumps({
        "text": response.text,
        "tool_calls": response.tool_calls,
        "ttft_ms": response.ttft_ms,
        "total_ms": response.total_ms,
    })
    await conn.execute(
        """
        INSERT INTO llm_call_ledger (
            tenant_id, idempotency_key, status, provider, model_id, response_payload,
            input_tokens, output_tokens, cost_usd
        )
        VALUES ($1, $2, 'COMPLETED', $3, $4, $5::jsonb, $6, $7, $8)
        ON CONFLICT (tenant_id, idempotency_key) DO UPDATE
        SET status = 'COMPLETED',
            response_payload = EXCLUDED.response_payload,
            input_tokens = EXCLUDED.input_tokens,
            output_tokens = EXCLUDED.output_tokens,
            cost_usd = EXCLUDED.cost_usd
        """,
        UUID(str(tenant_id)),
        idempotency_key,
        provider,
        model_id,
        payload,
        response.input_tokens,
        response.output_tokens,
        response.cost_usd,
    )
