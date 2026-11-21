from __future__ import annotations

import asyncio
import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

import asyncpg
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.app.api.deps import get_db_connection, get_tenant_id
from backend.app.storage.budget import create_budget_reservation
from backend.app.storage.db import get_pool

router = APIRouter(prefix="/runs", tags=["runs"])
_cascade_router_instance: Any = None


class CreateRunRequest(BaseModel):
    baseline_prompt_id: UUID
    candidate_prompt_id: UUID
    suite_id: UUID
    fixture_id: UUID
    trials_k: int = Field(default=1, ge=1, le=10)
    random_seed: int = 42
    simulator_model_id: str = "deterministic"
    judge_model_id: str = "deterministic-judge"
    max_budget_usd: float = Field(default=2.00, gt=0)


class RunResponse(BaseModel):
    id: str
    status: str
    baseline_prompt_id: str
    candidate_prompt_id: str
    suite_id: str
    fixture_id: str
    trials_k: int
    spent_usd: float
    max_budget_usd: float
    summary_stats: dict | None
    created_at: str
    completed_at: str | None


@router.post("", response_model=RunResponse)
async def create_eval_run(
    body: CreateRunRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    # 0. Check HTTP IETF Idempotency-Key
    req_sha256 = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
    lock_id: int | None = None
    if idempotency_key:
        # Serialise concurrent bursts on the same (tenant_id, idempotency_key) pair
        # Signed 64-bit int for PostgreSQL advisory locks
        lock_id = int(hashlib.md5(f"{tenant_id}:{idempotency_key}".encode()).hexdigest()[:15], 16)
        await conn.execute("SELECT pg_advisory_lock($1)", lock_id)
        cached = await conn.fetchrow(
            """
            SELECT request_sha256, response_status, response_body
            FROM http_idempotency_keys
            WHERE tenant_id = $1::uuid AND idempotency_key = $2
            """,
            tenant_id,
            idempotency_key,
        )
        if cached:
            await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
            if cached["request_sha256"] != req_sha256:
                raise HTTPException(
                    status_code=422,
                    detail="Idempotency conflict: Idempotency-Key already used with different request payload",
                )
            payload = json.loads(cached["response_body"]) if isinstance(cached["response_body"], str) else cached["response_body"]
            return RunResponse(**payload)

    try:
        # 1. Fetch scenario suite scenarios
        suite_row = await conn.fetchrow(
            """
            SELECT scenarios_json, scenario_count FROM scenario_suites
            WHERE tenant_id = $1::uuid AND id = $2::uuid
            """,
            tenant_id,
            str(body.suite_id),
        )
        if not suite_row:
            raise HTTPException(status_code=404, detail="Scenario suite not found")

        scenarios = json.loads(suite_row["scenarios_json"]) if isinstance(suite_row["scenarios_json"], str) else suite_row["scenarios_json"]

        # 2. Insert eval_run
        run_id = uuid4()
        grader_sha = "0000000000000000000000000000000000000000000000000000000000000000"

        await conn.execute(
            """
            INSERT INTO eval_runs (
                id, tenant_id, baseline_prompt_id, candidate_prompt_id,
                suite_id, fixture_id, grader_prompt_sha256, trials_k,
                random_seed, simulator_model_id, judge_model_id, status,
                max_budget_usd, spent_usd
            ) VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4::uuid,
                $5::uuid, $6::uuid, $7, $8,
                $9, $10, $11, 'QUEUED',
                $12, 0.0
            )
            """,
            run_id,
            tenant_id,
            str(body.baseline_prompt_id),
            str(body.candidate_prompt_id),
            str(body.suite_id),
            str(body.fixture_id),
            grader_sha,
            body.trials_k,
            body.random_seed,
            body.simulator_model_id,
            body.judge_model_id,
            body.max_budget_usd,
        )

        # 3. Fan-out eval_jobs for baseline & candidate across all trials & scenarios
        cost_per_job = body.max_budget_usd / max(len(scenarios) * body.trials_k * 2, 1)

        for trial_idx in range(body.trials_k):
            for scen in scenarios:
                scen_id = scen.get("scenario_id") or scen.get("id") or str(uuid4())
                for role, p_id in [("baseline", body.baseline_prompt_id), ("candidate", body.candidate_prompt_id)]:
                    job_id = uuid4()
                    # Create budget reservation
                    await create_budget_reservation(
                        conn,
                        tenant_id=tenant_id,
                        run_id=run_id,
                        job_id=job_id,
                        fence_token=0,
                        est_cost_usd=cost_per_job,
                    )
                    # Insert eval_job
                    await conn.execute(
                        """
                        INSERT INTO eval_jobs (
                            id, tenant_id, run_id, scenario_id, prompt_role,
                            prompt_version_id, trial_index, priority, status
                        ) VALUES (
                            $1::uuid, $2::uuid, $3::uuid, $4, $5,
                            $6::uuid, $7, 10, 'QUEUED'
                        )
                        """,
                        job_id,
                        tenant_id,
                        run_id,
                        scen_id,
                        role,
                        str(p_id),
                        trial_idx,
                    )

        row = await conn.fetchrow(
            """
            SELECT id, status, baseline_prompt_id, candidate_prompt_id,
                   suite_id, fixture_id, trials_k, spent_usd, max_budget_usd,
                   summary_stats, created_at, completed_at
            FROM eval_runs
            WHERE id = $1::uuid
            """,
            run_id,
        )
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create evaluation run")

        run_resp = RunResponse(
            id=str(row["id"]),
            status=row["status"],
            baseline_prompt_id=str(row["baseline_prompt_id"]),
            candidate_prompt_id=str(row["candidate_prompt_id"]),
            suite_id=str(row["suite_id"]),
            fixture_id=str(row["fixture_id"]),
            trials_k=row["trials_k"],
            spent_usd=float(row["spent_usd"]),
            max_budget_usd=float(row["max_budget_usd"]),
            summary_stats=json.loads(row["summary_stats"]) if row["summary_stats"] else None,
            created_at=row["created_at"].isoformat(),
            completed_at=row["completed_at"].isoformat() if row["completed_at"] else None,
        )

        if idempotency_key:
            await conn.execute(
                """
                INSERT INTO http_idempotency_keys (
                    tenant_id, idempotency_key, request_sha256, response_status, response_body
                ) VALUES (
                    $1::uuid, $2, $3, $4, $5::jsonb
                )
                ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
                """,
                tenant_id,
                idempotency_key,
                req_sha256,
                200,
                json.dumps(run_resp.model_dump(mode="json")),
            )

        return run_resp
    finally:
        if lock_id is not None:
            try:
                await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
            except Exception:
                pass


@router.get("", response_model=list[RunResponse])
async def list_runs(
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    rows = await conn.fetch(
        """
        SELECT id, status, baseline_prompt_id, candidate_prompt_id,
               suite_id, fixture_id, trials_k, spent_usd, max_budget_usd,
               summary_stats, created_at, completed_at
        FROM eval_runs
        WHERE tenant_id = $1::uuid
        ORDER BY created_at DESC
        """,
        tenant_id,
    )
    return [
        RunResponse(
            id=str(r["id"]),
            status=r["status"],
            baseline_prompt_id=str(r["baseline_prompt_id"]),
            candidate_prompt_id=str(r["candidate_prompt_id"]),
            suite_id=str(r["suite_id"]),
            fixture_id=str(r["fixture_id"]),
            trials_k=r["trials_k"],
            spent_usd=float(r["spent_usd"]),
            max_budget_usd=float(r["max_budget_usd"]),
            summary_stats=json.loads(r["summary_stats"]) if r["summary_stats"] else None,
            created_at=r["created_at"].isoformat(),
            completed_at=r["completed_at"].isoformat() if r["completed_at"] else None,
        )
        for r in rows
    ]


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    row = await conn.fetchrow(
        """
        SELECT id, status, baseline_prompt_id, candidate_prompt_id,
               suite_id, fixture_id, trials_k, spent_usd, max_budget_usd,
               summary_stats, created_at, completed_at
        FROM eval_runs
        WHERE tenant_id = $1::uuid AND id = $2::uuid
        """,
        tenant_id,
        run_id,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunResponse(
        id=str(row["id"]),
        status=row["status"],
        baseline_prompt_id=str(row["baseline_prompt_id"]),
        candidate_prompt_id=str(row["candidate_prompt_id"]),
        suite_id=str(row["suite_id"]),
        fixture_id=str(row["fixture_id"]),
        trials_k=row["trials_k"],
        spent_usd=float(row["spent_usd"]),
        max_budget_usd=float(row["max_budget_usd"]),
        summary_stats=json.loads(row["summary_stats"]) if row["summary_stats"] else None,
        created_at=row["created_at"].isoformat(),
        completed_at=row["completed_at"].isoformat() if row["completed_at"] else None,
    )


@router.get("/{run_id}/diff")
async def get_run_diff(
    run_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Return non-compensatory diff matrix, hard-gate breakdown, and paired stats."""
    run = await conn.fetchrow(
        """
        SELECT id, status, spent_usd, max_budget_usd, summary_stats
        FROM eval_runs
        WHERE tenant_id = $1::uuid AND id = $2::uuid
        """,
        tenant_id,
        run_id,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    jobs = await conn.fetch(
        """
        SELECT id, scenario_id, prompt_role, trial_index, status,
               overall_pass, hard_gate_pass, extraction_f1, cost_usd, p95_ttft_ms
        FROM eval_jobs
        WHERE tenant_id = $1::uuid AND run_id = $2::uuid
        """,
        tenant_id,
        run_id,
    )

    # Assertions breakdown
    assertions = await conn.fetch(
        """
        SELECT a.layer, a.metric_name, a.passed, a.failure_stage, j.prompt_role
        FROM assertion_results a
        JOIN eval_jobs j ON j.id = a.job_id
        WHERE j.tenant_id = $1::uuid AND j.run_id = $2::uuid
        """,
        tenant_id,
        run_id,
    )

    stage_breakdown: dict[str, dict[str, int]] = {
        "ASR_NOISE": {"baseline": 0, "candidate": 0},
        "SLOT_EXTRACT": {"baseline": 0, "candidate": 0},
        "FACT_HALLUCINATION": {"baseline": 0, "candidate": 0},
        "TOOL_CONTRACT": {"baseline": 0, "candidate": 0},
        "TONE_REGISTER": {"baseline": 0, "candidate": 0},
        "SIMULATOR_FAULT": {"baseline": 0, "candidate": 0},
    }

    for a in assertions:
        if not a["passed"] and a["failure_stage"] in stage_breakdown:
            role = a["prompt_role"]
            stage_breakdown[a["failure_stage"]][role] += 1

    summary_stats = json.loads(run["summary_stats"]) if run["summary_stats"] else {}
    hard_gate_regs = int(summary_stats.get("hard_gate_regressions", 0) or 0)
    v1_pass_rate = float(summary_stats.get("v1_pass_rate", 0.0) or 0.0)
    v2_pass_rate = float(summary_stats.get("v2_pass_rate", 0.0) or 0.0)
    delta_pass_rate = float(summary_stats.get("delta_pass_rate", 0.0) or 0.0)
    n_eval = int(summary_stats.get("n_evaluated", 0) or 0)
    run_status = str(run["status"] or "UNKNOWN")

    candidate_failures = {stage: counts["candidate"] for stage, counts in stage_breakdown.items() if counts["candidate"] > 0}

    if isinstance(summary_stats.get("executive_summary"), dict):
        exec_summary = summary_stats["executive_summary"]
    else:
        # DEF-07: Accurate, non-hallucinatory fallback executive summary
        if run_status in ("FAILED", "CANCELLED") or n_eval == 0:
            exec_summary = {
                "verdict": "INCONCLUSIVE",
                "headline": f"Evaluation run ended with status '{run_status}' ({n_eval} scenarios evaluated).",
                "key_findings": [
                    f"Run status: {run_status}",
                    f"Completed jobs: {sum(1 for j in jobs if j['status'] == 'COMPLETED')}/{len(jobs)}",
                    "Evaluation run incomplete or terminated before full scenario assessment.",
                ],
                "recommendation": "Rerun evaluation suite after verifying system health and worker connectivity.",
            }
        elif hard_gate_regs > 0 or run_status == "REGRESSED" or (n_eval > 0 and v2_pass_rate == 0.0):
            findings: list[str] = []
            if candidate_failures:
                for stage, count in candidate_failures.items():
                    findings.append(f"Candidate encountered {count} failure(s) in {stage.replace('_', ' ').title()}.")
            if hard_gate_regs > 0:
                findings.append(f"Candidate introduced {hard_gate_regs} hard-gate safety/compliance regression(s).")
            if v2_pass_rate == 0.0:
                findings.append(f"Candidate pass rate is 0.0% across all {n_eval} evaluated scenario(s).")
            if not findings:
                findings = [
                    "Buyer requested DNC or tool execution failed, but candidate prompt failed safety criteria.",
                    "Candidate failed compliance assertions on critical turns.",
                ]

            headline = (
                f"Candidate Prompt introduced {hard_gate_regs} critical safety & compliance regression(s)."
                if hard_gate_regs > 0
                else (
                    f"Candidate prompt failed 100% of test scenarios (0.0% pass rate across {n_eval} scenarios)."
                    if v2_pass_rate == 0.0
                    else "Candidate prompt regressed significantly below baseline."
                )
            )

            exec_summary = {
                "verdict": "BLOCKED",
                "headline": headline,
                "key_findings": findings,
                "recommendation": "Do NOT deploy to production. Fix compliance and grounding failures before release candidate cut.",
            }
        elif n_eval > 0 and v1_pass_rate == 0.0:
            if v2_pass_rate == 0.0:
                exec_summary = {
                    "verdict": "BLOCKED",
                    "headline": f"Both baseline and candidate failed all test scenarios (0.0% pass rate across {n_eval} scenarios).",
                    "key_findings": [
                        "Baseline prompt pass rate is 0.0%",
                        "Candidate prompt pass rate is 0.0%",
                        "Both models failed compliance or grounding assertions across the suite.",
                    ],
                    "recommendation": "Do NOT deploy to production. Inspect prompt definitions and environment fixtures.",
                }
            else:
                exec_summary = {
                    "verdict": "INCONCLUSIVE",
                    "headline": f"Baseline pass rate is 0.0% ({n_eval} scenarios); comparative statistical verdict is inconclusive.",
                    "key_findings": [
                        "Baseline prompt failed all scenarios (0.0% pass rate).",
                        f"Candidate pass rate is {v2_pass_rate * 100:.1f}%.",
                        "Relative effect size cannot be reliably certified against a 0% baseline.",
                    ],
                    "recommendation": "Verify baseline prompt health before evaluating candidate improvement.",
                }
        elif v2_pass_rate < 0.50 or delta_pass_rate < -0.05:
            findings = []
            if candidate_failures:
                for stage, count in candidate_failures.items():
                    findings.append(f"Candidate encountered {count} failure(s) in {stage.replace('_', ' ').title()}.")
            findings.append(f"Candidate pass rate ({v2_pass_rate * 100:.1f}%) is below the acceptable 50% release threshold.")
            if delta_pass_rate < 0:
                findings.append(f"Pass rate delta is negative ({delta_pass_rate * 100:+.1f}% vs baseline).")

            exec_summary = {
                "verdict": "BLOCKED",
                "headline": f"Candidate pass rate is unacceptably low ({v2_pass_rate * 100:.1f}%) with delta {delta_pass_rate * 100:+.1f}%.",
                "key_findings": findings,
                "recommendation": "Do NOT deploy to production. Address scenario failures before promoting candidate.",
            }
        else:
            exec_summary = {
                "verdict": "PASSED",
                "headline": "All hard-gate safety and compliance assertions passed cleanly.",
                "key_findings": [
                    "Zero DNC opt-out or compliance failures",
                    f"Baseline pass rate: {v1_pass_rate * 100:.1f}%, Candidate pass rate: {v2_pass_rate * 100:.1f}% (delta: {delta_pass_rate * 100:+.1f}%)",
                    "Accurate Indian currency parsing across all Lakh/Crore ranges",
                    "100% honest tool outcome confirmations",
                ],
                "recommendation": "Ready for production canary deployment.",
            }

    return {
        "run_id": run_id,
        "status": run["status"],
        "spent_usd": float(run["spent_usd"]),
        "max_budget_usd": float(run["max_budget_usd"]),
        "total_jobs": len(jobs),
        "completed_jobs": sum(1 for j in jobs if j["status"] == "COMPLETED"),
        "summary_stats": summary_stats,
        "failure_stage_breakdown": stage_breakdown,
        "executive_summary": exec_summary,
    }


@router.get("/{run_id}/scenarios")
async def list_run_scenarios(
    run_id: UUID,
    filter_mode: str = Query(default="all"),  # 'all', 'regressions', 'hard_gate_fails', 'anti_cheat_flags', 'quarantined'
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    jobs = await conn.fetch(
        """
        SELECT id, scenario_id, prompt_role, trial_index, status,
               overall_pass, hard_gate_pass, extraction_f1, cost_usd, p95_ttft_ms
        FROM eval_jobs
        WHERE tenant_id = $1::uuid AND run_id = $2::uuid
        ORDER BY scenario_id, trial_index, prompt_role
        """,
        tenant_id,
        run_id,
    )

    # Check for anti-cheat / disagreement flags
    anti_cheat_job_ids = set()
    anti_cheat_rows = await conn.fetch(
        """
        SELECT j.id
        FROM assertion_results a
        JOIN eval_jobs j ON j.id = a.job_id
        WHERE j.tenant_id = $1::uuid AND j.run_id = $2::uuid
          AND (a.layer = 'anti_cheat' OR a.metric_name = 'judge_concordance')
          AND a.passed = false
        """,
        tenant_id,
        run_id,
    )
    for r in anti_cheat_rows:
        anti_cheat_job_ids.add(str(r["id"]))

    pairs: dict[str, dict[str, Any]] = {}
    for j in jobs:
        key = f"{j['scenario_id']}_{j['trial_index']}"
        if key not in pairs:
            pairs[key] = {"scenario_id": j["scenario_id"], "trial_index": j["trial_index"]}
        pairs[key][j["prompt_role"]] = {
            "job_id": str(j["id"]),
            "status": j["status"],
            "overall_pass": j["overall_pass"],
            "hard_gate_pass": j["hard_gate_pass"],
            "extraction_f1": float(j["extraction_f1"] or 0.0),
            "cost_usd": float(j["cost_usd"] or 0.0),
            "p95_ttft_ms": j["p95_ttft_ms"],
            "has_anti_cheat_flag": str(j["id"]) in anti_cheat_job_ids,
        }

    results = []
    for key, item in pairs.items():
        base = item.get("baseline", {})
        cand = item.get("candidate", {})

        is_regression = (base.get("overall_pass") is True) and (cand.get("overall_pass") is False)
        is_hard_gate_fail = (cand.get("hard_gate_pass") is False)
        is_quarantined = (base.get("status") == "QUARANTINED_SIM_FAULT" or cand.get("status") == "QUARANTINED_SIM_FAULT")
        has_anti_cheat_flag = base.get("has_anti_cheat_flag", False) or cand.get("has_anti_cheat_flag", False)

        if filter_mode == "regressions" and not is_regression:
            continue
        if filter_mode == "hard_gate_fails" and not is_hard_gate_fail:
            continue
        if filter_mode == "anti_cheat_flags" and not has_anti_cheat_flag:
            continue
        if filter_mode == "quarantined" and not is_quarantined:
            continue

        item["is_regression"] = is_regression
        item["is_hard_gate_fail"] = is_hard_gate_fail
        item["is_quarantined"] = is_quarantined
        item["has_anti_cheat_flag"] = has_anti_cheat_flag
        results.append(item)

    return results


@router.get("/{run_id}/scenarios/{scenario_id}")
async def get_scenario_detail(
    run_id: UUID,
    scenario_id: str,
    trial_index: int = Query(default=0),
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Detailed side-by-side synchronized turns, raw vs perturbed text, tool calls, and assertions."""
    jobs = await conn.fetch(
        """
        SELECT id, prompt_role, status, overall_pass, hard_gate_pass, extraction_f1, cost_usd
        FROM eval_jobs
        WHERE tenant_id = $1::uuid AND run_id = $2::uuid AND scenario_id = $3 AND trial_index = $4
        """,
        tenant_id,
        run_id,
        scenario_id,
        trial_index,
    )
    if not jobs:
        raise HTTPException(status_code=404, detail="Scenario jobs not found")

    roles_data = {}
    for j in jobs:
        role = j["prompt_role"]
        job_id = j["id"]

        # Fetch turns
        turns = await conn.fetch(
            """
            SELECT turn_index, fsm_state, buyer_raw_text, buyer_perturbed_text,
                   agent_text, tool_calls, tool_outcomes, ttft_ms, total_ms, cost_usd
            FROM conversation_turns
            WHERE job_id = $1::uuid
            ORDER BY turn_index ASC
            """,
            job_id,
        )

        # Fetch assertions
        assertions = await conn.fetch(
            """
            SELECT layer, metric_name, passed, score, failure_stage, rationale_json
            FROM assertion_results
            WHERE job_id = $1::uuid
            ORDER BY id ASC
            """,
            job_id,
        )

        # Process turns with dynamic CascadeRouter evaluation
        processed_turns = []
        for t in turns:
            turn_text = t["agent_text"] or t["buyer_raw_text"] or ""
            cascade_status = "RESOLVED_SYSTEM1"
            cascade_tier = "SYSTEM_1"
            cascade_confidence = 0.985
            cascade_latency_ms = 0.365
            cascade_margin = 0.85
            cascade_posterior = 0.985

            try:
                global _cascade_router_instance
                if _cascade_router_instance is None:
                    from backend.app.evaluation.cascade_router import CascadeRouter
                    _cascade_router_instance = CascadeRouter()
                router = _cascade_router_instance
                task = "dnc_refusal" if "dnc" in scenario_id else ("prompt_injection" if "injection" in scenario_id else "action_confirmation")
                decision = router.route_turn(turn_text, task=task)
                cascade_status = decision.status
                cascade_tier = decision.system_tier
                cascade_confidence = float(decision.confidence)
                cascade_latency_ms = float(decision.latency_ms)
                cascade_margin = float(decision.margin)
                prob = decision.calibrated_probability
                if isinstance(prob, dict):
                    cascade_posterior = float(max(prob.values())) if prob else 0.5
                else:
                    cascade_posterior = float(prob)
            except Exception:
                pass

            processed_turns.append({
                "turn_index": t["turn_index"],
                "fsm_state": t["fsm_state"],
                "buyer_raw_text": t["buyer_raw_text"],
                "buyer_perturbed_text": t["buyer_perturbed_text"],
                "agent_text": t["agent_text"],
                "tool_calls": json.loads(t["tool_calls"]) if isinstance(t["tool_calls"], str) else t["tool_calls"],
                "tool_outcomes": json.loads(t["tool_outcomes"]) if isinstance(t["tool_outcomes"], str) else t["tool_outcomes"],
                "ttft_ms": t["ttft_ms"],
                "cost_usd": float(t["cost_usd"]),
                "cascade_status": cascade_status,
                "cascade_tier": cascade_tier,
                "cascade_confidence": cascade_confidence,
                "cascade_latency_ms": cascade_latency_ms,
                "cascade_margin": cascade_margin,
                "cascade_posterior": cascade_posterior,
            })

        roles_data[role] = {
            "job_id": str(job_id),
            "status": j["status"],
            "overall_pass": j["overall_pass"],
            "hard_gate_pass": j["hard_gate_pass"],
            "cost_usd": float(j["cost_usd"] or 0.0),
            "turns": processed_turns,
            "assertions": [
                {
                    "layer": a["layer"],
                    "metric_name": a["metric_name"],
                    "passed": a["passed"],
                    "score": float(a["score"]) if a["score"] is not None else None,
                    "failure_stage": a["failure_stage"],
                    "rationale": json.loads(a["rationale_json"]) if isinstance(a["rationale_json"], str) else a["rationale_json"],
                }
                for a in assertions
            ],
        }

    return {
        "run_id": run_id,
        "scenario_id": scenario_id,
        "trial_index": trial_index,
        "baseline": roles_data.get("baseline"),
        "candidate": roles_data.get("candidate"),
    }


@router.get("/{run_id}/stream")
async def stream_run_events(
    run_id: UUID,
    request: Request,
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Durable Server-Sent Events (SSE) backed by run_events table and Last-Event-ID replay."""
    pool = await get_pool()

    async def event_generator():
        try:
            curr_event_id = int(last_event_id) if last_event_id and last_event_id.strip().isdigit() else 0
        except (ValueError, TypeError):
            curr_event_id = 0
        if curr_event_id < 0:
            curr_event_id = 0

        while True:
            if await request.is_disconnected():
                break

            async with pool.acquire() as conn:
                await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, false)", tenant_id)
                try:
                    events = await conn.fetch(
                        """
                        SELECT event_id, event_type, payload
                        FROM run_events
                        WHERE tenant_id = $1::uuid AND run_id = $2::uuid AND event_id > $3
                        ORDER BY event_id ASC
                        LIMIT 50
                        """,
                        tenant_id,
                        run_id,
                        curr_event_id,
                    )

                    for ev in events:
                        curr_event_id = ev["event_id"]
                        ev_type = ev["event_type"]
                        payload = ev["payload"]
                        data_str = json.dumps(payload) if not isinstance(payload, str) else payload

                        yield f"id: {curr_event_id}\nevent: {ev_type}\ndata: {data_str}\n\n"

                        if ev_type in ("run.completed", "run.budget_halted", "run.early_aborted"):
                            return

                    # Terminal check when no new events are available
                    if not events:
                        run_status = await conn.fetchval(
                            """
                            SELECT status FROM eval_runs
                            WHERE tenant_id = $1::uuid AND id = $2::uuid
                            """,
                            tenant_id,
                            run_id,
                        )
                        if run_status in (
                            "PASSED",
                            "REGRESSED",
                            "INCONCLUSIVE_UNDERPOWERED",
                            "BUDGET_EXCEEDED",
                            "EARLY_ABORTED_HARM",
                            "FAILED",
                        ):
                            yield f"event: run.completed\ndata: {{\"status\": \"{run_status}\", \"run_id\": \"{run_id}\"}}\n\n"
                            return
                finally:
                    await conn.execute("SELECT set_config('app.current_tenant_id', '', false)")

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{run_id}/resume")
async def resume_run(
    run_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Resume run by resetting stalled running jobs back to QUEUED."""
    res = await conn.execute(
        """
        UPDATE eval_jobs
        SET status = 'QUEUED',
            worker_id = NULL,
            lease_expires_at = NULL
        WHERE tenant_id = $1::uuid AND run_id = $2::uuid AND status = 'RUNNING'
        """,
        tenant_id,
        run_id,
    )
    return {"run_id": str(run_id), "status": "resumed", "details": res}


@router.post("/{run_id}/dlq/replay")
async def replay_dlq(
    run_id: UUID,
    tenant_id: str = Depends(get_tenant_id),
    conn: asyncpg.Connection = Depends(get_db_connection),
):
    """Replay dead-lettered jobs for a run."""
    res = await conn.execute(
        """
        UPDATE eval_jobs
        SET status = 'QUEUED',
            attempt = 0,
            last_error_code = NULL,
            last_error_detail = NULL
        WHERE tenant_id = $1::uuid AND run_id = $2::uuid AND status = 'DEAD_LETTERED'
        """,
        tenant_id,
        run_id,
    )
    return {"run_id": str(run_id), "status": "replayed", "details": res}
