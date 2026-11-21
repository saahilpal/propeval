from __future__ import annotations

import datetime
import hashlib
import json
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db_connection, get_tenant_id

router = APIRouter(prefix="/fixtures", tags=["fixtures"])


class FixtureRegisterRequest(BaseModel):
    project_name: str
    city: str
    rera_id: str
    effective_from: datetime.date = Field(default_factory=datetime.date.today)
    facts_json: dict
    supersedes_id: UUID | None = None


class FixtureResponse(BaseModel):
    id: str
    project_name: str
    city: str
    rera_id: str
    effective_from: str
    facts_json: dict
    content_sha256: str
    created_at: str


def compute_fixture_hash(project_name: str, rera_id: str, facts_json: dict) -> str:
    canonical = {
        "project_name": project_name.strip(),
        "rera_id": rera_id.strip(),
        "facts_json": facts_json,
    }
    dumped = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(dumped).hexdigest()


@router.post("", response_model=FixtureResponse)
async def register_fixture(
    body: FixtureRegisterRequest,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    content_sha = compute_fixture_hash(body.project_name, body.rera_id, body.facts_json)
    facts_raw = json.dumps(body.facts_json)

    row = await conn.fetchrow(
        """
        INSERT INTO project_fixtures (
            tenant_id, project_name, city, rera_id, effective_from,
            supersedes_id, facts_json, content_sha256
        ) VALUES (
            $1::uuid, $2, $3, $4, $5, $6::uuid, $7::jsonb, $8
        )
        ON CONFLICT (tenant_id, content_sha256) DO UPDATE
            SET project_name = EXCLUDED.project_name
        RETURNING id, project_name, city, rera_id, effective_from, facts_json,
                  content_sha256, created_at
        """,
        tenant_id,
        body.project_name,
        body.city,
        body.rera_id,
        body.effective_from,
        str(body.supersedes_id) if body.supersedes_id else None,
        facts_raw,
        content_sha,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to register fixture")

    return FixtureResponse(
        id=str(row["id"]),
        project_name=row["project_name"],
        city=row["city"],
        rera_id=row["rera_id"],
        effective_from=row["effective_from"].isoformat(),
        facts_json=json.loads(row["facts_json"]) if isinstance(row["facts_json"], str) else row["facts_json"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )


@router.get("", response_model=list[FixtureResponse])
async def list_fixtures(
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    rows = await conn.fetch(
        """
        SELECT id, project_name, city, rera_id, effective_from, facts_json,
               content_sha256, created_at
        FROM project_fixtures
        WHERE tenant_id = $1::uuid
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        FixtureResponse(
            id=str(r["id"]),
            project_name=r["project_name"],
            city=r["city"],
            rera_id=r["rera_id"],
            effective_from=r["effective_from"].isoformat(),
            facts_json=json.loads(r["facts_json"]) if isinstance(r["facts_json"], str) else r["facts_json"],
            content_sha256=r["content_sha256"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/{fixture_id}", response_model=FixtureResponse)
async def get_fixture(
    fixture_id: str,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    row = await conn.fetchrow(
        """
        SELECT id, project_name, city, rera_id, effective_from, facts_json,
               content_sha256, created_at
        FROM project_fixtures
        WHERE tenant_id = $1::uuid AND id = $2::uuid
        """,
        tenant_id,
        fixture_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Fixture not found")

    return FixtureResponse(
        id=str(row["id"]),
        project_name=row["project_name"],
        city=row["city"],
        rera_id=row["rera_id"],
        effective_from=row["effective_from"].isoformat(),
        facts_json=json.loads(row["facts_json"]) if isinstance(row["facts_json"], str) else row["facts_json"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )
