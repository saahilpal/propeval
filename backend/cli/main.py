from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from typing import Any
import uuid
import yaml

from backend.app.config import settings
from backend.app.engine.worker import execute_eval_job, finalize_eval_run
from backend.app.storage.budget import create_budget_reservation
from backend.app.storage.db import close_pool, get_pool


def parse_args():
    parser = argparse.ArgumentParser(description="PropEval Voice Agent Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run evaluation comparison between baseline and candidate")
    run_parser.add_argument("--baseline", required=True, help="Path to baseline prompt YAML")
    run_parser.add_argument("--candidate", required=True, help="Path to candidate prompt YAML")
    run_parser.add_argument("--suite", required=True, help="Path to scenario suite YAML")
    run_parser.add_argument("--fixture", required=True, help="Path to project truth fixture YAML")
    run_parser.add_argument("--trials-k", type=int, default=1, help="Trials per scenario (default: 1)")
    run_parser.add_argument("--budget", type=float, default=2.00, help="Max budget USD (default: 2.00)")
    run_parser.add_argument("--gate", action="store_true", help="Exit code 1 on regression / gate failure")

    return parser.parse_args()


async def run_cli_comparison(
    baseline_path: str,
    candidate_path: str,
    suite_path: str,
    fixture_path: str,
    trials_k: int = 1,
    budget_usd: float = 2.00,
    enforce_gate: bool = False,
) -> int:
    pool = await get_pool()
    tenant_id = settings.default_tenant_id

    # 1. Load YAML inputs
    with open(baseline_path, "r", encoding="utf-8") as f:
        b_data = yaml.safe_load(f)
    with open(candidate_path, "r", encoding="utf-8") as f:
        c_data = yaml.safe_load(f)
    with open(suite_path, "r", encoding="utf-8") as f:
        s_data = yaml.safe_load(f)
    with open(fixture_path, "r", encoding="utf-8") as f:
        f_data = yaml.safe_load(f)

    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, true)", tenant_id)

        # 2. Register baseline prompt
        b_row = await conn.fetchrow(
            """
            INSERT INTO prompt_versions (
                tenant_id, name, version_tag, system_prompt, model_provider,
                model_id, tools_schema, content_sha256
            ) VALUES (
                $1::uuid, $2, $3, $4, $5, $6, $7::jsonb, md5($4)
            )
            ON CONFLICT (tenant_id, content_sha256) DO UPDATE SET version_tag = EXCLUDED.version_tag
            RETURNING id
            """,
            tenant_id,
            b_data.get("name", "Baseline Prompt"),
            b_data.get("version_tag", "v1.0"),
            b_data["system_prompt"],
            b_data.get("model_provider", "deterministic"),
            b_data.get("model_id", "deterministic-replay-v1"),
            json.dumps(b_data.get("tools_schema", [])),
        )
        baseline_id = b_row["id"]

        # 3. Register candidate prompt
        c_row = await conn.fetchrow(
            """
            INSERT INTO prompt_versions (
                tenant_id, name, version_tag, system_prompt, model_provider,
                model_id, tools_schema, content_sha256
            ) VALUES (
                $1::uuid, $2, $3, $4, $5, $6, $7::jsonb, md5($4)
            )
            ON CONFLICT (tenant_id, content_sha256) DO UPDATE SET version_tag = EXCLUDED.version_tag
            RETURNING id
            """,
            tenant_id,
            c_data.get("name", "Candidate Prompt"),
            c_data.get("version_tag", "v2.0"),
            c_data["system_prompt"],
            c_data.get("model_provider", "deterministic"),
            c_data.get("model_id", "deterministic-replay-v1"),
            json.dumps(c_data.get("tools_schema", [])),
        )
        candidate_id = c_row["id"]

        # 4. Register fixture
        f_row = await conn.fetchrow(
            """
            INSERT INTO project_fixtures (
                tenant_id, project_name, city, rera_id, effective_from,
                facts_json, content_sha256
            ) VALUES (
                $1::uuid, $2, $3, $4, '2026-11-01', $5::jsonb, md5($2)
            )
            ON CONFLICT (tenant_id, content_sha256) DO UPDATE SET project_name = EXCLUDED.project_name
            RETURNING id
            """,
            tenant_id,
            f_data.get("project_name", "Test Project"),
            f_data.get("city", "Pune"),
            f_data.get("rera_id", "P52100012345"),
            json.dumps(f_data.get("facts", f_data)),
        )
        fixture_id = f_row["id"]

        # 5. Register suite
        scenarios = s_data.get("scenarios", [])
        s_row = await conn.fetchrow(
            """
            INSERT INTO scenario_suites (
                tenant_id, name, suite_tier, version_tag,
                scenarios_json, scenario_count, content_sha256
            ) VALUES (
                $1::uuid, $2, $3, $4, $5::jsonb, $6, md5($2)
            )
            ON CONFLICT (tenant_id, name, version_tag) DO UPDATE SET scenario_count = EXCLUDED.scenario_count
            RETURNING id
            """,
            tenant_id,
            s_data.get("name", "Test Suite"),
            s_data.get("suite_tier", "smoke_pr"),
            s_data.get("version_tag", "v1"),
            json.dumps(scenarios),
            len(scenarios),
        )
        suite_id = s_row["id"]

        # 6. Create run
        run_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO eval_runs (
                id, tenant_id, baseline_prompt_id, candidate_prompt_id,
                suite_id, fixture_id, grader_prompt_sha256, trials_k,
                simulator_model_id, judge_model_id, status, max_budget_usd
            ) VALUES (
                $1::uuid, $2::uuid, $3::uuid, $4::uuid,
                $5::uuid, $6::uuid, '00000000', $7,
                'deterministic', 'deterministic-judge', 'RUNNING', $8
            )
            """,
            run_id,
            tenant_id,
            baseline_id,
            candidate_id,
            suite_id,
            fixture_id,
            trials_k,
            budget_usd,
        )

        # 7. Create eval jobs
        cost_per_job = budget_usd / max(len(scenarios) * trials_k * 2, 1)
        job_records = []
        for trial in range(trials_k):
            for scen in scenarios:
                scen_id = scen.get("scenario_id") or scen.get("id", str(uuid.uuid4()))
                for role, p_id in [("baseline", baseline_id), ("candidate", candidate_id)]:
                    job_id = uuid.uuid4()
                    conn_any: Any = conn
                    await create_budget_reservation(
                        conn_any,
                        tenant_id=tenant_id,
                        run_id=run_id,
                        job_id=job_id,
                        fence_token=0,
                        est_cost_usd=cost_per_job,
                    )
                    await conn.execute(
                        """
                        INSERT INTO eval_jobs (
                            id, tenant_id, run_id, scenario_id, prompt_role,
                            prompt_version_id, trial_index, priority, status
                        ) VALUES (
                            $1::uuid, $2::uuid, $3::uuid, $4, $5, $6::uuid, $7, 10, 'RUNNING'
                        )
                        """,
                        job_id,
                        tenant_id,
                        run_id,
                        scen_id,
                        role,
                        p_id,
                        trial,
                    )
                    job_records.append({
                        "id": job_id,
                        "tenant_id": tenant_id,
                        "run_id": run_id,
                        "scenario_id": scen_id,
                        "prompt_role": role,
                        "prompt_version_id": p_id,
                        "fence_token": 0,
                    })

    # 8. Execute all jobs
    print(f"\n================================================================================")
    print(f"PropEval CLI: Executing {len(job_records)} jobs across {len(scenarios)} scenarios (K={trials_k})")
    print(f"================================================================================\n")

    for idx, jr in enumerate(job_records):
        async with pool.acquire() as conn:
            conn_any: Any = conn
            await conn_any.execute("SELECT set_config('app.current_tenant_id', $1::text, true)", tenant_id)
            await execute_eval_job(conn_any, jr, pool)
            sys.stdout.write(f"\rProgress: [{idx+1}/{len(job_records)}] jobs evaluated...")
            sys.stdout.flush()

    print("\n\nAll jobs completed. Computing non-compensatory diff & paired statistics...\n")

    # 9. Read final summary stats
    async with pool.acquire() as conn:
        await conn.execute("SELECT set_config('app.current_tenant_id', $1::text, true)", tenant_id)
        run_row = await conn.fetchrow(
            """
            SELECT status, summary_stats, spent_usd FROM eval_runs WHERE id = $1::uuid
            """,
            run_id,
        )

    summary = json.loads(run_row["summary_stats"]) if run_row["summary_stats"] else {}
    status = run_row["status"]
    spent = float(run_row["spent_usd"])

    # 10. Print Structured Evaluation Report
    print("--------------------------------------------------------------------------------")
    print("EVALUATION RUN REPORT & PAIRED STATISTICAL VERDICT")
    print("--------------------------------------------------------------------------------")
    print(f"Run ID:                 {run_id}")
    print(f"Final Status:           {status}")
    print(f"Total Spent:            ${spent:.4f} USD ($0.00 cloud)")
    print(f"Evaluated Scenarios N:  {summary.get('n_evaluated', 0)}")
    print(f"Underpowered Notice:    {'YES (N < 50)' if summary.get('is_underpowered') else 'NO'}")
    print(f"Hard-Gate Regressions:  {summary.get('hard_gate_regressions', 0)}")
    print(f"Baseline Pass Rate:     {summary.get('v1_pass_rate', 0.0) * 100:.1f}%")
    print(f"Candidate Pass Rate:    {summary.get('v2_pass_rate', 0.0) * 100:.1f}%")
    print(f"Delta Pass Rate:        {summary.get('delta_pass_rate', 0.0) * 100:+.1f}%")
    print(f"McNemar Exact p-value:  {summary.get('mcnemar_p_value', 1.0):.4f}")
    print(f"Newcombe 95% CI:        [{summary.get('newcombe_ci_low', 0.0):+.4f}, {summary.get('newcombe_ci_high', 0.0):+.4f}]")
    print(f"Wilcoxon Rank-Biserial: {summary.get('rank_biserial_r', 0.0):+.4f}")
    print("--------------------------------------------------------------------------------\n")

    if enforce_gate:
        if status == "REGRESSED" or summary.get("hard_gate_regressions", 0) > 0:
            print("🚨 GATE CHECK FAILED: Candidate regressed on hard gates or statistically fell behind baseline.")
            return 1
        print("✅ GATE CHECK PASSED: Zero hard-gate regressions detected.")
        return 0

    return 0


def main():
    args = parse_args()
    if args.command == "run":
        exit_code = asyncio.run(
            run_cli_comparison(
                baseline_path=args.baseline,
                candidate_path=args.candidate,
                suite_path=args.suite,
                fixture_path=args.fixture,
                trials_k=args.trials_k,
                budget_usd=args.budget,
                enforce_gate=args.gate,
            )
        )
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
