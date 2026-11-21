from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import sys
from typing import Any
import uuid
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

from backend.app.config import settings
from backend.app.engine.worker import execute_eval_job
from backend.app.storage.budget import create_budget_reservation
from backend.app.storage.db import get_pool

# ---------------------------------------------------------------------------
# Offline Validation Pydantic Models (Zero DB Dependency)
# ---------------------------------------------------------------------------

class PropertyTruthFixture(BaseModel):
    project_name: str
    city: str | None = None
    rera_id: str
    facts_json: dict[str, Any] | None = None
    facts: dict[str, Any] | None = None
    effective_from: str | None = None
    version_tag: str | None = None
    schema_version: str | None = None
    developer: str | None = None
    locality: str | None = None


class PromptVersionFixture(BaseModel):
    name: str
    version_tag: str
    system_prompt: str
    model_provider: str = "deterministic"
    model_id: str = "deterministic-replay-v1"
    temperature: float = 0.30
    tools_schema: list[dict[str, Any]] = Field(default_factory=list)


class ScenarioSuiteFixture(BaseModel):
    name: str | None = None
    suite_name: str | None = None
    suite_id: str | None = None
    suite_tier: str | None = "smoke_pr"
    version_tag: str | None = "v1"
    description: str | None = None
    scenarios: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name or self.suite_name or self.suite_id or "Scenario Suite"


def validate_fixture_file(path_str: str) -> int:
    """Validate a fixture, prompt, or suite YAML file offline without DB dependencies."""
    file_path = Path(path_str)
    if not file_path.exists():
        print(f"❌ Error: File not found at '{path_str}'")
        return 1

    try:
        raw_bytes = file_path.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        data = yaml.safe_load(raw_bytes.decode("utf-8"))
    except Exception as e:
        print(f"❌ Error reading or parsing YAML in '{path_str}': {e}")
        return 1

    if not isinstance(data, dict):
        print(f"❌ Error: Expected YAML dictionary in '{path_str}', got {type(data).__name__}")
        return 1

    # Detect model type
    model_cls: type[BaseModel]
    detected_type: str
    if "scenarios" in data:
        model_cls = ScenarioSuiteFixture
        detected_type = "ScenarioSuiteFixture"
    elif "system_prompt" in data:
        model_cls = PromptVersionFixture
        detected_type = "PromptVersionFixture"
    elif "project_name" in data or "rera_id" in data:
        model_cls = PropertyTruthFixture
        detected_type = "PropertyTruthFixture"
    else:
        print(f"❌ Error: Cannot identify schema type for '{path_str}'.")
        print("Expected keys for PropertyTruthFixture (project_name, rera_id), PromptVersionFixture (system_prompt), or ScenarioSuiteFixture (scenarios).")
        return 1

    try:
        validated = model_cls(**data)
    except ValidationError as ve:
        print("--------------------------------------------------------------------------------")
        print(f"VALIDATION FAILED: {detected_type} at '{path_str}'")
        print("--------------------------------------------------------------------------------")
        for err in ve.errors():
            loc = " -> ".join(str(p) for p in err.get("loc", []))
            msg = err.get("msg", "")
            print(f"  • [{loc}]: {msg}")
        print("--------------------------------------------------------------------------------")
        return 1

    print("--------------------------------------------------------------------------------")
    print("PROPEVAL FIXTURE & SCHEMA VALIDATION REPORT")
    print("--------------------------------------------------------------------------------")
    print(f"File:               {path_str}")
    print(f"Detected Model:     {detected_type}")
    print("Validation Status:  VALID / PASSED (100% Schema Compliant)")
    print(f"Content SHA-256:    {sha256}")

    if isinstance(validated, PropertyTruthFixture):
        print(f"Project Name:       {validated.project_name}")
        print(f"RERA Registration:  {validated.rera_id}")
        if validated.city:
            print(f"City:               {validated.city}")
        if validated.effective_from:
            print(f"Effective From:     {validated.effective_from}")
    elif isinstance(validated, PromptVersionFixture):
        print(f"Prompt Name:        {validated.name} ({validated.version_tag})")
        print(f"Model:              {validated.model_provider} / {validated.model_id}")
        print(f"Tools Defined:      {len(validated.tools_schema)}")
    elif isinstance(validated, ScenarioSuiteFixture):
        print(f"Suite Name:         {validated.display_name} ({validated.version_tag})")
        print(f"Suite Tier:         {validated.suite_tier}")
        print(f"Scenarios Count:    {len(validated.scenarios)}")
    print("--------------------------------------------------------------------------------\n")
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description="PropEval Voice Agent Evaluation CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate-fixture subcommand (DEF-01)
    validate_parser = subparsers.add_parser(
        "validate-fixture",
        help="Validate a fixture, prompt, or suite YAML file offline against Pydantic models (Zero DB dependency)",
    )
    validate_parser.add_argument("path", nargs="?", default=None, help="Path to fixture, prompt, or suite YAML file")
    validate_parser.add_argument("--path", dest="path_opt", default=None, help="Alternative path flag")

    # run subcommand (DEF-03 defaults & DEF-02 webhook)
    run_parser = subparsers.add_parser("run", help="Run evaluation comparison between baseline and candidate")
    run_parser.add_argument(
        "--baseline",
        default="fixtures/prompt_baseline_v1.yaml",
        help="Path to baseline prompt YAML (default: fixtures/prompt_baseline_v1.yaml)",
    )
    run_parser.add_argument(
        "--candidate",
        default="fixtures/prompt_candidate_v2.yaml",
        help="Path to candidate prompt YAML (default: fixtures/prompt_candidate_v2.yaml)",
    )
    run_parser.add_argument(
        "--candidate-webhook",
        default=None,
        help="Outbound webhook URL for candidate agent under test (configures model_provider='webhook')",
    )
    run_parser.add_argument(
        "--suite",
        default="suites/hinglish_smoke_20.yaml",
        help="Path to scenario suite YAML (default: suites/hinglish_smoke_20.yaml)",
    )
    run_parser.add_argument(
        "--fixture",
        default="fixtures/lodha_wakad_2026_11.yaml",
        help="Path to project truth fixture YAML (default: fixtures/lodha_wakad_2026_11.yaml)",
    )
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
    candidate_webhook: str | None = None,
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
        c_provider = "webhook" if candidate_webhook else c_data.get("model_provider", "deterministic")
        c_model_id = candidate_webhook if candidate_webhook else c_data.get("model_id", "deterministic-replay-v1")
        c_row = await conn.fetchrow(
            """
            INSERT INTO prompt_versions (
                tenant_id, name, version_tag, system_prompt, model_provider,
                model_id, tools_schema, content_sha256
            ) VALUES (
                $1::uuid, $2, $3, $4, $5, $6, $7::jsonb, md5($4)
            )
            ON CONFLICT (tenant_id, content_sha256) DO UPDATE SET
                version_tag = EXCLUDED.version_tag,
                model_provider = EXCLUDED.model_provider,
                model_id = EXCLUDED.model_id
            RETURNING id
            """,
            tenant_id,
            c_data.get("name", "Candidate Prompt"),
            c_data.get("version_tag", "v2.0"),
            c_data["system_prompt"],
            c_provider,
            c_model_id,
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
    print("\n================================================================================")
    print(f"PropEval CLI: Executing {len(job_records)} jobs across {len(scenarios)} scenarios (K={trials_k})")
    print("================================================================================\n")

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
    if args.command == "validate-fixture":
        path = args.path_opt or args.path
        if not path:
            print("❌ Error: Path to fixture/prompt/suite file is required.")
            sys.exit(1)
        exit_code = validate_fixture_file(path)
        sys.exit(exit_code)
    elif args.command == "run":
        exit_code = asyncio.run(
            run_cli_comparison(
                baseline_path=args.baseline,
                candidate_path=args.candidate,
                candidate_webhook=args.candidate_webhook,
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
