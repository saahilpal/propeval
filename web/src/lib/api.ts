export interface PromptVersion {
  id: string;
  name: string;
  version_tag: string;
  status: string;
  system_prompt: string;
  model_provider: string;
  model_id: string;
  temperature: number;
  tools_schema: any[];
  content_sha256: string;
  created_at: string;
}

export interface ProjectFixture {
  id: string;
  project_name: string;
  city: string;
  rera_id: string;
  effective_from: string;
  facts_json: Record<string, any>;
  content_sha256: string;
  created_at: string;
}

export interface ScenarioSuite {
  id: string;
  name: string;
  suite_tier: string;
  version_tag: string;
  scenario_count: number;
  scenarios_json: any[];
  content_sha256: string;
  created_at: string;
}

export interface EvalRun {
  id: string;
  status: string;
  baseline_prompt_id: string;
  candidate_prompt_id: string;
  suite_id: string;
  fixture_id: string;
  trials_k: number;
  spent_usd: number;
  max_budget_usd: number;
  summary_stats: {
    n_evaluated?: number;
    quarantined_pairs?: number;
    is_underpowered?: boolean;
    hard_gate_regressions?: number;
    v1_pass_rate?: number;
    v2_pass_rate?: number;
    delta_pass_rate?: number;
    mcnemar_p_value?: number;
    newcombe_ci_low?: number;
    newcombe_ci_high?: number;
    wilcoxon_stat?: number;
    wilcoxon_p_value?: number;
    rank_biserial_r?: number;
    spent_usd?: number;
  } | null;
  created_at: string;
  completed_at: string | null;
}

export interface RunDiffResponse {
  run_id: string;
  status: string;
  spent_usd: number;
  max_budget_usd: number;
  total_jobs: number;
  completed_jobs: number;
  summary_stats: Record<string, any>;
  failure_stage_breakdown: Record<string, { baseline: number; candidate: number }>;
}

export interface ScenarioComparison {
  scenario_id: string;
  trial_index: number;
  is_regression: boolean;
  is_hard_gate_fail: boolean;
  is_quarantined: boolean;
  has_anti_cheat_flag?: boolean;
  baseline: {
    job_id: string;
    status: string;
    overall_pass: boolean | null;
    hard_gate_pass: boolean | null;
    extraction_f1: number;
    cost_usd: number;
    p95_ttft_ms: number | null;
    has_anti_cheat_flag?: boolean;
  };
  candidate: {
    job_id: string;
    status: string;
    overall_pass: boolean | null;
    hard_gate_pass: boolean | null;
    extraction_f1: number;
    cost_usd: number;
    p95_ttft_ms: number | null;
    has_anti_cheat_flag?: boolean;
  };
}

export interface TurnDetail {
  turn_index: number;
  fsm_state: string;
  buyer_raw_text: string;
  buyer_perturbed_text: string;
  agent_text: string;
  tool_calls: any[];
  tool_outcomes: any[];
  ttft_ms: number;
  cost_usd: number;
}

export interface AssertionDetail {
  layer: string;
  metric_name: string;
  passed: boolean;
  score: number | null;
  failure_stage: string | null;
  rationale: Record<string, any>;
}

export interface ScenarioDetailResponse {
  run_id: string;
  scenario_id: string;
  trial_index: number;
  baseline?: {
    job_id: string;
    status: string;
    overall_pass: boolean;
    hard_gate_pass: boolean;
    cost_usd: number;
    turns: TurnDetail[];
    assertions: AssertionDetail[];
  };
  candidate?: {
    job_id: string;
    status: string;
    overall_pass: boolean;
    hard_gate_pass: boolean;
    cost_usd: number;
    turns: TurnDetail[];
    assertions: AssertionDetail[];
  };
}

const API_BASE = "/api/v1";

export async function fetchPrompts(): Promise<PromptVersion[]> {
  const res = await fetch(`${API_BASE}/prompts`);
  if (!res.ok) throw new Error("Failed to fetch prompts");
  return res.json();
}

export async function fetchFixtures(): Promise<ProjectFixture[]> {
  const res = await fetch(`${API_BASE}/fixtures`);
  if (!res.ok) throw new Error("Failed to fetch fixtures");
  return res.json();
}

export async function fetchSuites(): Promise<ScenarioSuite[]> {
  const res = await fetch(`${API_BASE}/suites`);
  if (!res.ok) throw new Error("Failed to fetch scenario suites");
  return res.json();
}

export async function fetchRuns(): Promise<EvalRun[]> {
  const res = await fetch(`${API_BASE}/runs`);
  if (!res.ok) throw new Error("Failed to fetch eval runs");
  return res.json();
}

export async function fetchRun(id: string): Promise<EvalRun> {
  const res = await fetch(`${API_BASE}/runs/${id}`);
  if (!res.ok) throw new Error("Failed to fetch run details");
  return res.json();
}

export async function fetchRunDiff(id: string): Promise<RunDiffResponse> {
  const res = await fetch(`${API_BASE}/runs/${id}/diff`);
  if (!res.ok) throw new Error("Failed to fetch run diff");
  return res.json();
}

export async function fetchRunScenarios(id: string, filterMode = "all"): Promise<ScenarioComparison[]> {
  const res = await fetch(`${API_BASE}/runs/${id}/scenarios?filter_mode=${filterMode}`);
  if (!res.ok) throw new Error("Failed to fetch run scenarios");
  return res.json();
}

export async function fetchScenarioDetail(runId: string, scenarioId: string, trialIndex = 0): Promise<ScenarioDetailResponse> {
  const res = await fetch(`${API_BASE}/runs/${runId}/scenarios/${scenarioId}?trial_index=${trialIndex}`);
  if (!res.ok) throw new Error("Failed to fetch scenario transcript");
  return res.json();
}

export async function createRun(payload: {
  baseline_prompt_id: string;
  candidate_prompt_id: string;
  suite_id: string;
  fixture_id: string;
  trials_k?: number;
  max_budget_usd?: number;
}): Promise<EvalRun> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to start comparison run");
  return res.json();
}
