from __future__ import annotations

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db_connection, get_tenant_id
from backend.app.evaluation.rubric_judge import sanitize_untrusted_transcript
from backend.app.security.pii_redactor import redact_pii_dpdp

router = APIRouter(prefix="/suites", tags=["suites"])


class SuiteRegisterRequest(BaseModel):
    name: str
    suite_tier: str = "smoke_pr"  # 'smoke_pr', 'release_gate', 'metamorphic', 'canary_spc', 'custom'
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


class CreateCustomScenarioRequest(BaseModel):
    name: str = "Wakad Skeptic Buyer"
    language: str = "hinglish"
    budget_phrase: str = "ek point do crore"
    bhk: int = 2
    mood: str = "price_skeptic"
    opening_line: str = "Namaste, kya Wakad mein flat available hai?"
    inject_asr_noise: bool = False
    inject_tool_503: bool = False
    trigger_dnc: bool = False
    rera_trap: bool = False
    expected_hard_gates: list[str] = Field(
        default_factory=lambda: ["SLOT_EXTRACT", "DNC_COMPLIANCE", "TOOL_CONTRACT", "FACT_GROUNDING"]
    )
    # Optional nested payloads for frontend compatibility
    buyer_profile: dict[str, Any] | None = None
    stress_switches: dict[str, Any] | None = None


class CustomScenarioResponse(BaseModel):
    suite_id: str
    suite_name: str
    scenario_id: str
    scenario_preview: dict[str, Any]
    id: str
    name: str
    suite_tier: str = "custom"
    version_tag: str = "v1.0.0-custom"
    scenario_count: int = 1
    scenarios_json: list[dict[str, Any]]
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
        raise HTTPException(status_code=422, detail="Scenario suite cannot be empty: at least 1 scenario required")

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


@router.post("/custom-scenario", response_model=CustomScenarioResponse)
async def create_custom_scenario(
    body: CreateCustomScenarioRequest,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Compile structured scenario into BuyerAgendaFSM format and persist to Custom Scenarios suite."""
    name = body.name.strip() or "Custom Interactive Buyer"
    language = body.language.strip() or "hinglish"
    budget_phrase = body.budget_phrase.strip() or "1.2 crore"
    bhk = body.bhk
    mood = body.mood.strip() or "price_skeptic"
    opening_line = body.opening_line.strip() or "Namaste, kya Wakad mein flat available hai?"
    inject_asr_noise = body.inject_asr_noise
    inject_tool_503 = body.inject_tool_503
    trigger_dnc = body.trigger_dnc
    rera_trap = body.rera_trap
    expected_hard_gates = list(body.expected_hard_gates)

    # Reconcile optional nested frontend payloads
    if body.buyer_profile:
        bp = body.buyer_profile
        if bp.get("budget"):
            budget_phrase = str(bp["budget"]).strip()
        if bp.get("mood"):
            mood = str(bp["mood"]).strip()
        cfg = bp.get("configuration")
        if cfg:
            cfg_str = str(cfg).lower()
            if "3" in cfg_str:
                bhk = 3
            elif "4" in cfg_str:
                bhk = 4
            elif "1" in cfg_str:
                bhk = 1
            else:
                bhk = 2

    if body.stress_switches:
        sw = body.stress_switches
        if "asr_noise" in sw:
            inject_asr_noise = bool(sw["asr_noise"])
        if "tool_503" in sw:
            inject_tool_503 = bool(sw["tool_503"])
        if "dnc_trigger" in sw:
            trigger_dnc = bool(sw["dnc_trigger"])
        if "rera_trap" in sw:
            rera_trap = bool(sw["rera_trap"])

    # Sanitize untrusted input against prompt injections and redact PII
    sanitized_opening = sanitize_untrusted_transcript(opening_line)
    redacted_opening = redact_pii_dpdp(sanitized_opening)

    clean_slug = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower().strip())
    clean_slug = re.sub(r"_+", "_", clean_slug).strip("_") or "buyer"
    scenario_id = f"custom_{clean_slug}_{uuid.uuid4().hex[:6]}"

    scenario_entry = {
        "scenario_id": scenario_id,
        "name": name,
        "max_turns": 6,
        "asr_noise_profile": "telephony_8khz" if inject_asr_noise else "clean",
        "inject_asr_noise": inject_asr_noise,
        "inject_tool_503": inject_tool_503,
        "fault_config": {"book_site_visit": 503} if inject_tool_503 else {},
        "expected_tools": ["mark_dnc"] if trigger_dnc else ["book_site_visit"],
        "expected_hard_gates": expected_hard_gates,
        "fsm_spec": {
            "agenda": {
                "scenario_id": scenario_id,
                "target_project": "Lodha Wakad",
                "target_bhk": float(bhk),
                "budget_raw": budget_phrase,
                "wants_rera_check": rera_trap,
                "wants_site_visit": not trigger_dnc,
                "wants_dnc": trigger_dnc,
                "language_register": language,
                "objection_type": mood,
                "opening_line": redacted_opening,
            }
        },
        "metadata": {
            "mood": mood,
            "budget_phrase": budget_phrase,
            "opening_line": redacted_opening,
            "trigger_dnc": trigger_dnc,
            "rera_trap": rera_trap,
            "inject_asr_noise": inject_asr_noise,
            "inject_tool_503": inject_tool_503,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    suite_name = "Custom Scenarios (User Created)"
    version_tag = "v1.0.0-custom"

    # Check for existing custom scenarios suite
    existing_row = await conn.fetchrow(
        """
        SELECT id, name, suite_tier, version_tag, scenarios_json, scenario_count, created_at
        FROM scenario_suites
        WHERE tenant_id = $1::uuid AND name = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        tenant_id,
        suite_name,
    )

    if existing_row:
        suite_id = str(existing_row["id"])
        existing_scens = (
            json.loads(existing_row["scenarios_json"])
            if isinstance(existing_row["scenarios_json"], str)
            else (existing_row["scenarios_json"] or [])
        )
        updated_scens = list(existing_scens) + [scenario_entry]
        scen_count = len(updated_scens)
        content_sha = compute_suite_hash(suite_name, str(existing_row["version_tag"]), updated_scens)

        await conn.execute(
            """
            UPDATE scenario_suites
            SET scenarios_json = $1::jsonb,
                scenario_count = $2,
                content_sha256 = $3
            WHERE id = $4::uuid
            """,
            json.dumps(updated_scens),
            scen_count,
            content_sha,
            suite_id,
        )
        created_at_str = existing_row["created_at"].isoformat()
    else:
        suite_id = str(uuid.uuid4())
        updated_scens = [scenario_entry]
        scen_count = 1
        content_sha = compute_suite_hash(suite_name, version_tag, updated_scens)

        insert_row = await conn.fetchrow(
            """
            INSERT INTO scenario_suites (
                id, tenant_id, name, suite_tier, version_tag,
                scenarios_json, scenario_count, content_sha256
            ) VALUES (
                $1::uuid, $2::uuid, $3, 'custom', $4,
                $5::jsonb, $6, $7
            )
            RETURNING id, created_at
            """,
            suite_id,
            tenant_id,
            suite_name,
            version_tag,
            json.dumps(updated_scens),
            scen_count,
            content_sha,
        )
        if not insert_row:
            raise HTTPException(status_code=500, detail="Failed to initialize custom scenario suite")
        created_at_str = insert_row["created_at"].isoformat()

    return CustomScenarioResponse(
        id=suite_id,
        suite_id=suite_id,
        name=suite_name,
        suite_name=suite_name,
        scenario_id=scenario_id,
        scenario_count=scen_count,
        suite_tier="custom",
        version_tag=version_tag,
        scenarios_json=updated_scens,
        scenario_preview=scenario_entry,
        content_sha256=content_sha,
        created_at=created_at_str,
    )


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
    if len(body.recordings) == 0:
        raise HTTPException(status_code=422, detail="No recordings provided for import")

    scenarios = []
    for idx, rec in enumerate(body.recordings):
        raw_text = rec.get("raw_transcript", "")
        # Protect against malformed UTF-8 surrogates or control null bytes
        if isinstance(raw_text, str):
            raw_text = raw_text.encode("utf-8", "surrogateescape").decode("utf-8", "replace").replace("\x00", "")
        else:
            raw_text = str(raw_text)

        # Sanitize against prompt injection special tokens & redact DPDP PII before saving
        sanitized = sanitize_untrusted_transcript(raw_text)
        redacted = redact_pii_dpdp(sanitized)
        scenarios.append({
            "id": f"rec_{idx+1}",
            "intent": "telephony_replay",
            "language": rec.get("detected_language", "hinglish"),
            "raw_text": redacted,
            "metadata": rec.get("metadata", {}),
        })

    reg_req = SuiteRegisterRequest(
        name=body.suite_name,
        suite_tier="canary_spc",
        version_tag=body.version_tag,
        scenarios_json=scenarios,
    )
    return await register_suite(reg_req, tenant_id=tenant_id, conn=conn)
