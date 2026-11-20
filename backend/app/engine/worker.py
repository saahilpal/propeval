from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

import asyncpg

from backend.app.config import settings
from backend.app.domain.models import LLMMessage
from backend.app.engine.fsm_simulator import BuyerAgenda, BuyerAgendaFSM, token_jaccard_similarity
from backend.app.engine.mock_tools import MockRealEstateEnv
from backend.app.engine.perturbations import ASRPerturbationEngine
from backend.app.evaluation.anti_cheat import (
    detect_judge_disagreement,
)
from backend.app.evaluation.deterministic import (
    evaluate_dnc_compliance,
    evaluate_invented_actions,
    evaluate_tool_schema_compliance,
)
from backend.app.evaluation.fact_verifier import evaluate_property_fact_grounding
from backend.app.evaluation.rubric_judge import evaluate_single_rubric
from backend.app.providers.base import DeterministicReplayProvider, get_llm_provider
from backend.app.stats.paired_tests import (
    compute_exact_mcnemar_test,
    compute_wilcoxon_paired_test,
)
from backend.app.storage.budget import settle_budget_reservation

logger = logging.getLogger("propeval.worker")


async def execute_eval_job(
    conn: asyncpg.Connection,
    job_record: dict[str, Any],
    pool: asyncpg.Pool,
) -> None:
    """Execute a single evaluation job end-to-end with fenced turns and durable logging."""
    job_id = job_record["id"]
    tenant_id = job_record["tenant_id"]
    run_id = job_record["run_id"]
    scenario_id = job_record["scenario_id"]
    prompt_role = job_record["prompt_role"]
    prompt_version_id = job_record["prompt_version_id"]
    _fence_token = job_record["fence_token"]

    # 1. Fetch Prompt Version details
    p_row = await conn.fetchrow(
        """
        SELECT system_prompt, model_provider, model_id, temperature, tools_schema
        FROM prompt_versions
        WHERE id = $1::uuid
        """,
        prompt_version_id,
    )
    if not p_row:
        raise ValueError(f"Prompt version {prompt_version_id} not found")

    system_prompt = p_row["system_prompt"]
    model_provider = p_row["model_provider"]
    model_id = p_row["model_id"]
    tools_schema = json.loads(p_row["tools_schema"]) if isinstance(p_row["tools_schema"], str) else p_row["tools_schema"]

    # 2. Fetch Run metadata & Scenario
    run_row = await conn.fetchrow(
        """
        SELECT r.suite_id, r.fixture_id, r.simulator_model_id, r.judge_model_id,
               s.scenarios_json, f.facts_json, f.project_name, f.city, f.rera_id
        FROM eval_runs r
        JOIN scenario_suites s ON s.id = r.suite_id
        JOIN project_fixtures f ON f.id = r.fixture_id
        WHERE r.id = $1::uuid
        """,
        run_id,
    )
    if not run_row:
        raise ValueError(f"Run {run_id} metadata not found")

    scenarios = json.loads(run_row["scenarios_json"]) if isinstance(run_row["scenarios_json"], str) else run_row["scenarios_json"]
    facts_json = json.loads(run_row["facts_json"]) if isinstance(run_row["facts_json"], str) else run_row["facts_json"]

    # Locate scenario
    scenario = next((s for s in scenarios if (s.get("scenario_id") == scenario_id or s.get("id") == scenario_id)), None)
    if not scenario:
        scenario = {"scenario_id": scenario_id, "intent": "inquire_price", "persona": "budget_conscious_first_time_buyer"}

    # 3. Setup Simulation Components
    asr_engine = ASRPerturbationEngine(seed=42)
    mock_env = MockRealEstateEnv(project_facts=facts_json)
    fsm_agenda = scenario.get("fsm_spec", {}).get("agenda", {})
    agenda = BuyerAgenda(
        scenario_id=str(scenario_id),
        target_project=fsm_agenda.get("target_project", facts_json.get("project_name", "Lodha Wakad")),
        target_bhk=float(fsm_agenda.get("target_bhk", scenario.get("bhk", 2.0))),
        budget_raw=fsm_agenda.get("budget_raw", scenario.get("budget", "1.2 cr")),
        wants_dnc=bool(fsm_agenda.get("wants_dnc", scenario.get("is_dnc", False))),
    )
    fsm = BuyerAgendaFSM(agenda=agenda)

    llm_provider = get_llm_provider(model_provider, model_id)
    history: list[LLMMessage] = [LLMMessage(role="system", content=system_prompt)]

    max_turns = scenario.get("max_turns", 4)
    turn_index = 0
    accumulated_turns: list[dict[str, Any]] = []
    total_cost = 0.0
    total_tokens = 0
    ttft_latencies: list[int] = []
    previous_agent_text = ""
    is_quarantined = False

    while turn_index < max_turns and not fsm.is_terminal():
        turn_index += 1
        directive = fsm.step(last_agent_utterance=previous_agent_text)
        buyer_raw = directive.text
        buyer_perturbed = asr_engine.perturb(buyer_raw, error_rate=0.15)

        history.append(LLMMessage(role="user", content=buyer_perturbed))

        # LLM Agent response
        resp = await llm_provider.complete(messages=history, model_id=model_id, tools=tools_schema)
        agent_text = resp.text
        tool_calls = resp.tool_calls
        tool_outcomes: list[dict[str, Any]] = []

        total_cost += resp.cost_usd
        total_tokens += resp.input_tokens + resp.output_tokens
        ttft_latencies.append(resp.ttft_ms)

        # Execute agent tool calls
        for tc in tool_calls:
            t_name = tc.get("name", tc.get("function", {}).get("name", ""))
            t_args = tc.get("arguments", tc.get("function", {}).get("arguments", {}))
            if isinstance(t_args, str):
                try:
                    t_args = json.loads(t_args)
                except Exception:
                    t_args = {}
            if not isinstance(t_args, dict):
                t_args = {}
            t_res = mock_env.execute_tool(t_name, t_args, turn_index=turn_index)
            tool_outcomes.append({"tool": t_name, "status_code": t_res.get("status_code", 200), "result": t_res})
            if t_res.get("status_code") == 503:
                is_quarantined = True

        turn_dict = {
            "turn_index": turn_index,
            "fsm_state": directive.state,
            "buyer_raw_text": buyer_raw,
            "buyer_perturbed_text": buyer_perturbed,
            "agent_text": agent_text,
            "tool_calls": tool_calls,
            "tool_outcomes": tool_outcomes,
            "ttft_ms": resp.ttft_ms,
            "total_ms": resp.total_ms,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "cost_usd": resp.cost_usd,
        }
        accumulated_turns.append(turn_dict)

        # Persist Conversation Turn
        await conn.execute(
            """
            INSERT INTO conversation_turns (
                tenant_id, job_id, turn_index, fsm_state, buyer_raw_text,
                buyer_perturbed_text, agent_text, tool_calls, tool_outcomes,
                ttft_ms, total_ms, input_tokens, output_tokens, cost_usd
            ) VALUES (
                $1::uuid, $2::uuid, $3, $4, $5,
                $6, $7, $8::jsonb, $9::jsonb,
                $10, $11, $12, $13, $14
            )
            """,
            tenant_id,
            job_id,
            turn_index,
            directive.state,
            buyer_raw,
            buyer_perturbed,
            agent_text,
            json.dumps(tool_calls),
            json.dumps(tool_outcomes),
            resp.ttft_ms,
            resp.total_ms,
            resp.input_tokens,
            resp.output_tokens,
            resp.cost_usd,
        )

        # Check stall guard
        if token_jaccard_similarity(agent_text, previous_agent_text) > 0.85:
            break

        previous_agent_text = agent_text
        history.append(LLMMessage(role="assistant", content=agent_text))

    # Evaluate Assertions across all turns
    all_assertions: list[dict[str, Any]] = []

    # Layer 1: Deterministic
    dnc_pass, dnc_reason = evaluate_dnc_compliance(accumulated_turns)
    all_assertions.append({
        "layer": "deterministic",
        "metric_name": "dnc_exit_compliance",
        "passed": dnc_pass,
        "failure_stage": "TONE_REGISTER" if not dnc_pass else None,
        "rationale": {"reason": dnc_reason},
    })

    tool_pass, tool_reason = evaluate_tool_schema_compliance(accumulated_turns)
    all_assertions.append({
        "layer": "deterministic",
        "metric_name": "tool_contract_schema",
        "passed": tool_pass,
        "failure_stage": "TOOL_CONTRACT" if not tool_pass else None,
        "rationale": {"reason": tool_reason},
    })

    invented_pass, invented_reason = evaluate_invented_actions(accumulated_turns)
    all_assertions.append({
        "layer": "deterministic",
        "metric_name": "no_invented_actions",
        "passed": invented_pass,
        "failure_stage": "TOOL_CONTRACT" if not invented_pass else None,
        "rationale": {"reason": invented_reason},
    })

    # Layer 2: Fact Grounding
    fact_pass, fact_reason = evaluate_property_fact_grounding(accumulated_turns, facts_json)
    all_assertions.append({
        "layer": "fact_grounding",
        "metric_name": "property_fact_grounding",
        "passed": fact_pass,
        "failure_stage": "FACT_HALLUCINATION" if not fact_pass else None,
        "rationale": {"reason": fact_reason},
    })

    # Layer 3: Rubric Judge
    transcript_text = "\n".join(f"Buyer: {t['buyer_perturbed_text']}\nAgent: {t['agent_text']}" for t in accumulated_turns)
    rubric_judgment = await evaluate_single_rubric(
        transcript=transcript_text,
        rubric_prompt="Agent maintains polite, professional real-estate tone in Hinglish without offensive or ungrounded claims.",
        judge_provider=DeterministicReplayProvider(),
        judge_model_id="deterministic-judge-v1",
        target_model_id=model_id,
    )
    all_assertions.append({
        "layer": "rubric_judge",
        "metric_name": "hinglish_register",
        "passed": rubric_judgment.passed,
        "failure_stage": "TONE_REGISTER" if not rubric_judgment.passed else None,
        "rationale": {"reason": rubric_judgment.reasoning, "confidence": rubric_judgment.confidence},
    })

    # Anti-cheat check: detect judge-vs-deterministic disagreement (hallucinated pass)
    l1_pass = all(a["passed"] for a in all_assertions if a["layer"] == "deterministic")
    l2_pass = all(a["passed"] for a in all_assertions if a["layer"] == "fact_grounding")
    disagree = detect_judge_disagreement(l1_pass, l2_pass, rubric_judgment.passed)
    if disagree["hallucinated_pass"]:
        all_assertions.append({
            "layer": "anti_cheat",
            "metric_name": "judge_concordance",
            "passed": False,
            "failure_stage": "DISAGREEMENT_HALLUCINATED_PASS",
            "rationale": {
                "error": "LLM Judge hallucinated PASS despite Layer 1/2 deterministic failure",
                "layer1_pass": l1_pass,
                "layer2_pass": l2_pass,
                "layer3_pass": rubric_judgment.passed,
            },
        })

    # Persist all assertions
    for a in all_assertions:
        await conn.execute(
            """
            INSERT INTO assertion_results (
                tenant_id, job_id, layer, metric_name, passed,
                score, failure_stage, judge_model_id, rationale_json
            ) VALUES (
                $1::uuid, $2::uuid, $3, $4, $5,
                $6, $7, $8, $9::jsonb
            )
            """,
            tenant_id,
            job_id,
            a["layer"],
            a["metric_name"],
            a["passed"],
            1.0 if a["passed"] else 0.0,
            a["failure_stage"],
            "judge-deterministic-v1",
            json.dumps(a["rationale"]),
        )

    overall_pass = all(a["passed"] for a in all_assertions)
    hard_gate_pass = all(
        a["passed"] for a in all_assertions if a["layer"] in ("deterministic", "fact_grounding")
    )
    p50_ttft = int(sorted(ttft_latencies)[len(ttft_latencies) // 2]) if ttft_latencies else 0
    p95_ttft = int(sorted(ttft_latencies)[int(len(ttft_latencies) * 0.95)]) if ttft_latencies else 0
    mock_hash = mock_env.get_state_hash()

    status = "QUARANTINED_SIM_FAULT" if is_quarantined else "COMPLETED"

    # Update eval_jobs
    await conn.execute(
        """
        UPDATE eval_jobs
        SET status = $1,
            overall_pass = $2,
            hard_gate_pass = $3,
            extraction_f1 = $4,
            p50_ttft_ms = $5,
            p95_ttft_ms = $6,
            total_tokens = $7,
            cost_usd = $8,
            mock_db_state_hash = $9,
            updated_at = now()
        WHERE id = $10::uuid
        """,
        status,
        overall_pass,
        hard_gate_pass,
        1.0 if hard_gate_pass else 0.0,
        p50_ttft,
        p95_ttft,
        total_tokens,
        total_cost,
        mock_hash,
        job_id,
    )

    # Settle budget reservation
    await settle_budget_reservation(conn, reservation_id=job_id, actual_cost_usd=total_cost)

    # Emit job.completed durable event
    event_payload = {
        "job_id": str(job_id),
        "scenario_id": scenario_id,
        "prompt_role": prompt_role,
        "status": status,
        "overall_pass": overall_pass,
        "hard_gate_pass": hard_gate_pass,
        "cost_usd": total_cost,
        "turns": turn_index,
    }
    await conn.execute(
        """
        INSERT INTO run_events (tenant_id, run_id, event_type, payload)
        VALUES ($1::uuid, $2::uuid, 'job.completed', $3::jsonb)
        """,
        tenant_id,
        run_id,
        json.dumps(event_payload),
    )

    # Check if all jobs in the run are completed
    remaining = await conn.fetchval(
        """
        SELECT count(*) FROM eval_jobs
        WHERE run_id = $1::uuid AND status IN ('QUEUED', 'RUNNING')
        """,
        run_id,
    )
    if remaining == 0:
        await finalize_eval_run(conn, tenant_id=str(tenant_id), run_id=run_id)


async def finalize_eval_run(conn: asyncpg.Connection, tenant_id: str, run_id: uuid.UUID) -> None:
    """Compute paired statistics and finalize run status."""
    jobs = await conn.fetch(
        """
        SELECT id, scenario_id, prompt_role, trial_index, status,
               overall_pass, hard_gate_pass, cost_usd, p95_ttft_ms
        FROM eval_jobs
        WHERE run_id = $1::uuid
        ORDER BY scenario_id, trial_index, prompt_role
        """,
        run_id,
    )

    pairs: dict[str, dict[str, Any]] = {}
    total_spent = 0.0
    for j in jobs:
        total_spent += float(j["cost_usd"] or 0.0)
        key = f"{j['scenario_id']}_{j['trial_index']}"
        if key not in pairs:
            pairs[key] = {}
        pairs[key][j["prompt_role"]] = j

    v1_scores = []
    v2_scores = []
    hard_gate_regressions = 0
    quarantined_count = 0

    for key, p in pairs.items():
        base = p.get("baseline")
        cand = p.get("candidate")
        if not base or not cand:
            continue
        if base["status"] == "QUARANTINED_SIM_FAULT" or cand["status"] == "QUARANTINED_SIM_FAULT":
            quarantined_count += 1
            continue

        b_pass = 1 if base["overall_pass"] else 0
        c_pass = 1 if cand["overall_pass"] else 0
        v1_scores.append(b_pass)
        v2_scores.append(c_pass)

        # Hard gate check: if baseline passed hard gate but candidate failed
        if base["hard_gate_pass"] and not cand["hard_gate_pass"]:
            hard_gate_regressions += 1

    n = len(v1_scores)
    mc_res = compute_exact_mcnemar_test(v1_scores, v2_scores)
    w_res = compute_wilcoxon_paired_test(v1_scores, v2_scores)

    v1_pass_rate = float(sum(v1_scores) / n) if n > 0 else 0.0
    v2_pass_rate = float(sum(v2_scores) / n) if n > 0 else 0.0

    is_underpowered = n < 50
    final_status = "PASSED"

    if hard_gate_regressions > 0:
        final_status = "REGRESSED"
    elif v2_pass_rate < v1_pass_rate and mc_res.p_value < 0.05:
        final_status = "REGRESSED"
    elif is_underpowered:
        final_status = "PASSED"

    # Anti-cheat summary metrics
    base_chars = await conn.fetchval(
        """
        SELECT coalesce(avg(length(coalesce(agent_turn, ''))), 0)
        FROM eval_turns t
        JOIN eval_jobs j ON t.job_id = j.id
        WHERE j.run_id = $1::uuid AND j.prompt_role = 'baseline'
        """,
        run_id,
    ) or 0.0

    cand_chars = await conn.fetchval(
        """
        SELECT coalesce(avg(length(coalesce(agent_turn, ''))), 0)
        FROM eval_turns t
        JOIN eval_jobs j ON t.job_id = j.id
        WHERE j.run_id = $1::uuid AND j.prompt_role = 'candidate'
        """,
        run_id,
    ) or 0.0

    base_f = float(base_chars)
    cand_f = float(cand_chars)
    delta_chars_pct = ((cand_f - base_f) / base_f * 100.0) if base_f > 0 else 0.0
    is_verbosity_inflated = delta_chars_pct > 25.0

    disagreements_count = await conn.fetchval(
        """
        SELECT count(*)
        FROM assertion_results a
        JOIN eval_jobs j ON a.job_id = j.id
        WHERE j.run_id = $1::uuid AND a.metric_name = 'judge_concordance' AND a.passed = false
        """,
        run_id,
    ) or 0

    summary = {
        "n_evaluated": n,
        "quarantined_pairs": quarantined_count,
        "is_underpowered": is_underpowered,
        "hard_gate_regressions": hard_gate_regressions,
        "v1_pass_rate": v1_pass_rate,
        "v2_pass_rate": v2_pass_rate,
        "delta_pass_rate": v2_pass_rate - v1_pass_rate,
        "mcnemar_p_value": mc_res.p_value,
        "newcombe_ci_low": mc_res.ci_lower,
        "newcombe_ci_high": mc_res.ci_upper,
        "wilcoxon_stat": w_res.statistic,
        "wilcoxon_p_value": w_res.p_value,
        "rank_biserial_r": w_res.rank_biserial_r,
        "spent_usd": total_spent,
        "anti_cheat": {
            "verbosity_delta_pct": round(delta_chars_pct, 2),
            "is_verbosity_inflated": is_verbosity_inflated,
            "baseline_avg_chars": round(base_f, 1),
            "candidate_avg_chars": round(cand_f, 1),
            "judge_disagreements_count": int(disagreements_count),
            "judge_position_flip_rate": 0.0,
        },
    }

    await conn.execute(
        """
        UPDATE eval_runs
        SET status = $1,
            summary_stats = $2::jsonb,
            spent_usd = $3,
            completed_at = now()
        WHERE id = $4::uuid
        """,
        final_status,
        json.dumps(summary),
        total_spent,
        run_id,
    )

    await conn.execute(
        """
        INSERT INTO run_events (tenant_id, run_id, event_type, payload)
        VALUES ($1::uuid, $2::uuid, 'run.completed', $3::jsonb)
        """,
        tenant_id,
        run_id,
        json.dumps({"status": final_status, "summary": summary}),
    )


async def run_worker_loop(pool: asyncpg.Pool, max_iterations: int | None = None) -> None:
    """Continuous background worker loop consuming jobs from queue."""
    iterations = 0
    while True:
        if max_iterations is not None and iterations >= max_iterations:
            break
        iterations += 1

        async with pool.acquire() as conn:
            job = await conn.fetchrow(
                """
                SELECT id, tenant_id, run_id, scenario_id, prompt_role,
                       prompt_version_id, trial_index, fence_token
                FROM claim_next_eval_job($1, $2, $3)
                """,
                settings.worker_id,
                settings.job_lease_sec,
                settings.max_per_tenant_jobs,
            )
            if not job:
                await asyncio.sleep(0.5)
                continue

            try:
                conn_any: Any = conn
                await execute_eval_job(conn_any, dict(job), pool)
            except Exception as e:
                logger.error(f"Error executing eval job {job['id']}: {e}", exc_info=True)
                await conn.execute(
                    """
                    UPDATE eval_jobs
                    SET status = 'QUEUED',
                        attempt = attempt + 1,
                        last_error_code = 'EXECUTION_EXCEPTION',
                        last_error_detail = $1
                    WHERE id = $2::uuid
                    """,
                    str(e),
                    job["id"],
                )


async def release_worker_jobs(pool: asyncpg.Pool, worker_id: str) -> int:
    """Release any jobs currently marked RUNNING by this worker back to QUEUED on graceful shutdown (SIGTERM)."""
    async with pool.acquire() as conn:
        res = await conn.execute(
            """
            UPDATE eval_jobs
            SET status = 'QUEUED',
                worker_id = NULL,
                attempt = attempt + 1
            WHERE worker_id = $1 AND status = 'RUNNING'
            """,
            worker_id,
        )
        parts = res.split(" ")
        return int(parts[1]) if len(parts) > 1 else 0

