from __future__ import annotations

import hashlib
import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db_connection, get_tenant_id

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptRegisterRequest(BaseModel):
    name: str
    version_tag: str
    system_prompt: str
    model_provider: str = "deterministic"
    model_id: str = "deterministic-replay-v1"
    temperature: float = 0.30
    tools_schema: list[dict] = Field(default_factory=list)
    parent_version_id: UUID | None = None


class PromptResponse(BaseModel):
    id: str
    name: str
    version_tag: str
    status: str
    system_prompt: str
    model_provider: str
    model_id: str
    temperature: float
    tools_schema: list[dict]
    content_sha256: str
    created_at: str


def compute_prompt_hash(system_prompt: str, model_id: str, tools_schema: list[dict]) -> str:
    canonical = {
        "system_prompt": system_prompt.strip(),
        "model_id": model_id.strip(),
        "tools_schema": tools_schema,
    }
    dumped = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(dumped).hexdigest()


@router.post("", response_model=PromptResponse)
async def register_prompt(
    body: PromptRegisterRequest,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    content_sha = compute_prompt_hash(body.system_prompt, body.model_id, body.tools_schema)
    tools_json = json.dumps(body.tools_schema)

    row = await conn.fetchrow(
        """
        INSERT INTO prompt_versions (
            tenant_id, name, version_tag, parent_version_id, status,
            system_prompt, model_provider, model_id, temperature,
            tools_schema, content_sha256
        ) VALUES (
            $1::uuid, $2, $3, $4::uuid, 'REGISTERED',
            $5, $6, $7, $8, $9::jsonb, $10
        )
        ON CONFLICT (tenant_id, content_sha256) DO UPDATE
            SET version_tag = EXCLUDED.version_tag
        RETURNING id, name, version_tag, status, system_prompt, model_provider,
                  model_id, temperature, tools_schema, content_sha256, created_at
        """,
        tenant_id,
        body.name,
        body.version_tag,
        str(body.parent_version_id) if body.parent_version_id else None,
        body.system_prompt,
        body.model_provider,
        body.model_id,
        body.temperature,
        tools_json,
        content_sha,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to register prompt")

    return PromptResponse(
        id=str(row["id"]),
        name=row["name"],
        version_tag=row["version_tag"],
        status=row["status"],
        system_prompt=row["system_prompt"],
        model_provider=row["model_provider"],
        model_id=row["model_id"],
        temperature=float(row["temperature"]),
        tools_schema=json.loads(row["tools_schema"]) if isinstance(row["tools_schema"], str) else row["tools_schema"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )


@router.get("", response_model=list[PromptResponse])
async def list_prompts(
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    rows = await conn.fetch(
        """
        SELECT id, name, version_tag, status, system_prompt, model_provider,
               model_id, temperature, tools_schema, content_sha256, created_at
        FROM prompt_versions
        WHERE tenant_id = $1::uuid
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        PromptResponse(
            id=str(r["id"]),
            name=r["name"],
            version_tag=r["version_tag"],
            status=r["status"],
            system_prompt=r["system_prompt"],
            model_provider=r["model_provider"],
            model_id=r["model_id"],
            temperature=float(r["temperature"]),
            tools_schema=json.loads(r["tools_schema"]) if isinstance(r["tools_schema"], str) else r["tools_schema"],
            content_sha256=r["content_sha256"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/models/available")
async def list_available_execution_models():
    """List available execution models (Fast Local Engine, Ollama, etc.)."""
    from backend.app.api.models import get_available_models

    return await get_available_models()


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    row = await conn.fetchrow(
        """
        SELECT id, name, version_tag, status, system_prompt, model_provider,
               model_id, temperature, tools_schema, content_sha256, created_at
        FROM prompt_versions
        WHERE tenant_id = $1::uuid AND id = $2::uuid
        """,
        tenant_id,
        prompt_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Prompt version not found")

    return PromptResponse(
        id=str(row["id"]),
        name=row["name"],
        version_tag=row["version_tag"],
        status=row["status"],
        system_prompt=row["system_prompt"],
        model_provider=row["model_provider"],
        model_id=row["model_id"],
        temperature=float(row["temperature"]),
        tools_schema=json.loads(row["tools_schema"]) if isinstance(row["tools_schema"], str) else row["tools_schema"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )
