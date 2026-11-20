from __future__ import annotations

import hashlib
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
import asyncpg
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db_connection, get_tenant_id

router = APIRouter(prefix="/suites", tags=["suites"])


class SuiteRegisterRequest(BaseModel):
    name: str
    suite_tier: str = "smoke_pr"  # 'smoke_pr', 'release_gate', 'metamorphic', 'canary_spc'
    version_tag: str
    scenarios_json: list[dict]


class SuiteResponse(BaseModel):
    id: str
    name: str
    suite_tier: str
    version_tag: str
    scenario_count: int
    scenarios_json: list[dict]
    content_sha256: str
    created_at: str


class TelephonyReplayImportRequest(BaseModel):
    suite_name: str
    version_tag: str
    recordings: list[dict]  # list of {audio_url, raw_transcript, detected_language, metadata}


def compute_suite_hash(name: str, version_tag: str, scenarios_json: list[dict]) -> str:
    canonical = {
        "name": name.strip(),
        "version_tag": version_tag.strip(),
        "scenarios_json": scenarios_json,
    }
    dumped = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.sha256(dumped).hexdigest()


@router.post("", response_model=SuiteResponse)
async def register_suite(
    body: SuiteRegisterRequest,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    if len(body.scenarios_json) == 0:
        raise HTTPException(status_code=400, detail="Scenario suite cannot be empty")

    content_sha = compute_suite_hash(body.name, body.version_tag, body.scenarios_json)
    scenarios_raw = json.dumps(body.scenarios_json)

    row = await conn.fetchrow(
        """
        INSERT INTO scenario_suites (
            tenant_id, name, suite_tier, version_tag,
            scenarios_json, scenario_count, content_sha256
        ) VALUES (
            $1::uuid, $2, $3, $4,
            $5::jsonb, $6, $7
        )
        ON CONFLICT (tenant_id, name, version_tag) DO UPDATE
            SET scenarios_json = EXCLUDED.scenarios_json,
                scenario_count = EXCLUDED.scenario_count
        RETURNING id, name, suite_tier, version_tag, scenarios_json,
                  scenario_count, content_sha256, created_at
        """,
        tenant_id,
        body.name,
        body.suite_tier,
        body.version_tag,
        scenarios_raw,
        len(body.scenarios_json),
        content_sha,
    )
    if not row:
        raise HTTPException(status_code=500, detail="Failed to register scenario suite")

    return SuiteResponse(
        id=str(row["id"]),
        name=row["name"],
        suite_tier=row["suite_tier"],
        version_tag=row["version_tag"],
        scenario_count=row["scenario_count"],
        scenarios_json=json.loads(row["scenarios_json"]) if isinstance(row["scenarios_json"], str) else row["scenarios_json"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )


@router.get("", response_model=list[SuiteResponse])
async def list_suites(
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    rows = await conn.fetch(
        """
        SELECT id, name, suite_tier, version_tag, scenarios_json,
               scenario_count, content_sha256, created_at
        FROM scenario_suites
        WHERE tenant_id = $1::uuid
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        SuiteResponse(
            id=str(r["id"]),
            name=r["name"],
            suite_tier=r["suite_tier"],
            version_tag=r["version_tag"],
            scenario_count=r["scenario_count"],
            scenarios_json=json.loads(r["scenarios_json"]) if isinstance(r["scenarios_json"], str) else r["scenarios_json"],
            content_sha256=r["content_sha256"],
            created_at=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.get("/{suite_id}", response_model=SuiteResponse)
async def get_suite(
    suite_id: str,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    row = await conn.fetchrow(
        """
        SELECT id, name, suite_tier, version_tag, scenarios_json,
               scenario_count, content_sha256, created_at
        FROM scenario_suites
        WHERE tenant_id = $1::uuid AND id = $2::uuid
        """,
        tenant_id,
        suite_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Suite not found")

    return SuiteResponse(
        id=str(row["id"]),
        name=row["name"],
        suite_tier=row["suite_tier"],
        version_tag=row["version_tag"],
        scenario_count=row["scenario_count"],
        scenarios_json=json.loads(row["scenarios_json"]) if isinstance(row["scenarios_json"], str) else row["scenarios_json"],
        content_sha256=row["content_sha256"],
        created_at=row["created_at"].isoformat(),
    )


@router.post("/replay/import", response_model=SuiteResponse)
async def import_telephony_recordings(
    body: TelephonyReplayImportRequest,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    scenarios = []
    for idx, rec in enumerate(body.recordings):
        scenarios.append({
            "id": f"rec_{idx+1}",
            "intent": "telephony_replay",
            "language": rec.get("detected_language", "hinglish"),
            "raw_text": rec.get("raw_transcript", ""),
            "metadata": rec.get("metadata", {}),
        })

    reg_req = SuiteRegisterRequest(
        name=body.suite_name,
        suite_tier="canary_spc",
        version_tag=body.version_tag,
        scenarios_json=scenarios,
    )
    return await register_suite(reg_req, tenant_id=tenant_id, conn=conn)
