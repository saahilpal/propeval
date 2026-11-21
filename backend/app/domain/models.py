from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    name: str | None = None


class LLMResponse(BaseModel):
    text: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    ttft_ms: int = 0
    total_ms: int = 0
    cost_usd: float = 0.0
    provider: str = "deterministic"
    model_id: str = "deterministic-replay-v1"


class EvalJob(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID
    run_id: UUID
    scenario_id: str
    prompt_role: Literal["baseline", "candidate"]
    prompt_version_id: UUID
    trial_index: int = 0
    priority: int = 10
    status: Literal["QUEUED", "RUNNING", "COMPLETED", "QUARANTINED_SIM_FAULT", "DEAD_LETTERED"] = "QUEUED"
    worker_id: str | None = None
    fence_token: int = 0
    attempt: int = 0
    max_attempts: int = 5
    run_after: datetime = Field(default_factory=datetime.utcnow)
    lease_expires_at: datetime | None = None
    overall_pass: bool | None = None
    hard_gate_pass: bool | None = None
    extraction_f1: float | None = None
    p50_ttft_ms: int | None = None
    p95_ttft_ms: int | None = None
    total_tokens: int = 0
    cost_usd: float = 0.0
    mock_db_state_hash: str | None = None
    last_error_code: str | None = None
    last_error_detail: str | None = None


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str
    trace_id: str | None = None
