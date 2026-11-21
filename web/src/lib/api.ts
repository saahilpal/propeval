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
  executive_summary?: {
    verdict: string;
    headline: string;
    key_findings: string[];
    recommendation: string;
  };
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

export interface CascadeMetrics {
  resolution_rate_pct: number;
  escalation_rate_pct: number;
  p50_latency_ms?: number;
  expected_calibration_error?: number;
  cost_savings_pct?: number;
  total_evaluated_turns?: number;
  resolved_count: number;
  total_turns: number;
  escalated_count: number;
  cpu_latency_p50_ms: number;
  cpu_latency_p95_ms: number;
  cpu_latency_sla_ms: number;
  speedup_factor: number;
  ece: number;
  brier_score: number;
  net_dollar_savings_pct: number;
  cost_without_cascade_usd_per_1k: number;
  cost_with_cascade_usd_per_1k: number;
  dollar_savings_usd_per_1k: number;
  cohens_kappa: number;
  mcnemar_p_value: number;
  newcombe_ci_low: number;
  newcombe_ci_high: number;
  zero_defect_leakage: boolean;
  source?: string;
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
  cascade_status?: string;
  cascade_tier?: string;
  cascade_confidence?: number;
  cascade_latency_ms?: number;
  cascade_margin?: number;
  cascade_posterior?: number;
  metrics?: {
    confidence?: number;
    is_escalated?: boolean;
    margin?: number;
    posterior?: number;
  };
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

export const DEFAULT_PROMPTS: PromptVersion[] = [
  {
    id: "3f8d6ec7-a21a-405f-a38c-f7a773dde33e",
    name: "v1.0 — Production Baseline",
    version_tag: "v1.0",
    status: "PRODUCTION_BASELINE",
    system_prompt: `You are an expert, professional real estate sales assistant in India representing Lodha Crown Wakad in Pune.
You speak natural, fluent conversational Hinglish with a polite, helpful register.
Rules:
1. When asked about pricing, quote starting ₹1.2 Cr (120 lakh) for 2 BHK with possession in December 2026.
2. If customer requests DNC, opt-out, or says "call mat karo", stop immediately, apologize politely, and close call.
3. Only confirm booking or WhatsApp dispatch if tool call succeeded with status 200. Never invent confirmations.
4. Strictly verify all property details against RERA ID P52100024888.`,
    model_provider: "ollama",
    model_id: "qwen2.5:7b-instruct-q4_K_M",
    temperature: 0.3,
    tools_schema: [],
    content_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    created_at: "2026-11-20T00:00:00Z",
  },
  {
    id: "a5ea7a6c-54bd-4ca9-b7e3-d9592ed14a8d",
    name: "v2.0 — Aggressive Pitch [Regressed]",
    version_tag: "v2.0",
    status: "GATED_REGRESSED",
    system_prompt: `You are an aggressive high-conversion sales assistant for Lodha Crown Wakad.
Push for site visits immediately. Handle objections persistently. If buyer says 'call mat karo', pitch weekend discounts instead! If booking fails, claim WhatsApp confirmation sent.`,
    model_provider: "ollama",
    model_id: "qwen2.5:7b-instruct-q4_K_M",
    temperature: 0.7,
    tools_schema: [],
    content_sha256: "a1b2c3d4e5f67890123456789abcdef0123456789abcdef0123456789abcdef0",
    created_at: "2026-11-20T00:00:00Z",
  },
  {
    id: "c7ea8a1b-91de-4ba7-b89e-e8593ed25b9c",
    name: "v2.1 — Hardened Release Candidate",
    version_tag: "v2.1",
    status: "GATED_PASS",
    system_prompt: `You are a hardened, compliance-first real estate sales assistant for Lodha Crown Wakad in Pune.
Strict compliance with TRAI regulations. Immediate one-turn exit on DNC requests. Grounded against RERA P52100024888. 1.2 Crore parsed strictly as ₹1.2 Cr.`,
    model_provider: "ollama",
    model_id: "qwen2.5:7b-instruct-q4_K_M",
    temperature: 0.2,
    tools_schema: [],
    content_sha256: "f1e2d3c4b5a67890123456789abcdef0123456789abcdef0123456789abcdef0",
    created_at: "2026-11-20T00:00:00Z",
  },
];

export const DEFAULT_FIXTURES: ProjectFixture[] = [
  {
    id: "3fb5f027-ec7c-41c3-bb10-d920c9de8576",
    project_name: "Lodha Crown Wakad — Pune",
    city: "Pune",
    rera_id: "P52100024888",
    effective_from: "2025-01-01",
    facts_json: {
      developer: "Lodha Group",
      possession_date: "December 2026",
      starting_price_cr: 1.2,
      bhk_configs: ["2 BHK", "3 BHK"],
    },
    content_sha256: "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9",
    created_at: "2026-11-20T00:00:00Z",
  },
  {
    id: "4fc6a138-fd8d-42d4-cc21-ea31d9ef9687",
    project_name: "DLF Cyber City Phase 3 — Gurugram",
    city: "Gurugram",
    rera_id: "HRERA-PKL-GGM-1234",
    effective_from: "2025-01-01",
    facts_json: {
      developer: "DLF Limited",
      possession_date: "Ready to Move",
      starting_price_cr: 3.5,
      bhk_configs: ["3 BHK", "4 BHK"],
    },
    content_sha256: "c1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2",
    created_at: "2026-11-20T00:00:00Z",
  },
];

export const DEFAULT_SUITES: ScenarioSuite[] = [
  {
    id: "d6d4ef4c-e872-4c44-ab95-4a98bf7c44e1",
    name: "Hinglish 20-Scenario Smoke Suite",
    suite_tier: "smoke_pr",
    version_tag: "v1.0.0",
    scenario_count: 20,
    scenarios_json: [],
    content_sha256: "d5a8b6c4e2f0123456789abcdef0123456789abcdef0123456789abcdef01234",
    created_at: "2026-11-20T00:00:00Z",
  },
  {
    id: "e7e5fa5d-f983-4d55-bc11-5b09cf8d55f2",
    name: "Hinglish 50-Scenario Release Gate",
    suite_tier: "release_gate",
    version_tag: "v1.0.0",
    scenario_count: 50,
    scenarios_json: [],
    content_sha256: "e6b9c7d5f3a123456789abcdef0123456789abcdef0123456789abcdef012345",
    created_at: "2026-11-20T00:00:00Z",
  },
];

export const DEFAULT_RUNS: EvalRun[] = [
  {
    id: "b1a2c3d4-e5f6-7890-abcd-ef1234567890",
    status: "REGRESSED",
    baseline_prompt_id: "3f8d6ec7-a21a-405f-a38c-f7a773dde33e",
    candidate_prompt_id: "a5ea7a6c-54bd-4ca9-b7e3-d9592ed14a8d",
    suite_id: "d6d4ef4c-e872-4c44-ab95-4a98bf7c44e1",
    fixture_id: "3fb5f027-ec7c-41c3-bb10-d920c9de8576",
    trials_k: 1,
    spent_usd: 0.004,
    max_budget_usd: 1.5,
    summary_stats: {
      n_evaluated: 20,
      quarantined_pairs: 0,
      is_underpowered: true,
      hard_gate_regressions: 3,
      v1_pass_rate: 1.0,
      v2_pass_rate: 0.85,
      delta_pass_rate: -0.15,
      mcnemar_p_value: 0.25,
      newcombe_ci_low: -0.32,
      newcombe_ci_high: 0.02,
      spent_usd: 0.004,
    },
    created_at: "2026-11-20T12:32:16Z",
    completed_at: "2026-11-20T12:32:19Z",
  },
  {
    id: "c1a2c3d4-e5f6-7890-abcd-ef1234567891",
    status: "PASSED",
    baseline_prompt_id: "3f8d6ec7-a21a-405f-a38c-f7a773dde33e",
    candidate_prompt_id: "c7ea8a1b-91de-4ba7-b89e-e8593ed25b9c",
    suite_id: "d6d4ef4c-e872-4c44-ab95-4a98bf7c44e1",
    fixture_id: "3fb5f027-ec7c-41c3-bb10-d920c9de8576",
    trials_k: 1,
    spent_usd: 0.004,
    max_budget_usd: 1.5,
    summary_stats: {
      n_evaluated: 20,
      quarantined_pairs: 0,
      is_underpowered: true,
      hard_gate_regressions: 0,
      v1_pass_rate: 1.0,
      v2_pass_rate: 1.0,
      delta_pass_rate: 0.0,
      mcnemar_p_value: 1.0,
      newcombe_ci_low: -0.05,
      newcombe_ci_high: 0.05,
      spent_usd: 0.004,
    },
    created_at: "2026-11-20T13:27:24Z",
    completed_at: "2026-11-20T13:27:27Z",
  },
];

export async function fetchPrompts(): Promise<PromptVersion[]> {
  try {
    const res = await fetch(`${API_BASE}/prompts`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (err) {
    console.warn("Using fallback prompts due to API error:", err);
  }
  return DEFAULT_PROMPTS;
}

export async function fetchFixtures(): Promise<ProjectFixture[]> {
  try {
    const res = await fetch(`${API_BASE}/fixtures`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (err) {
    console.warn("Using fallback fixtures due to API error:", err);
  }
  return DEFAULT_FIXTURES;
}

export async function fetchSuites(): Promise<ScenarioSuite[]> {
  try {
    const res = await fetch(`${API_BASE}/suites`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (err) {
    console.warn("Using fallback suites due to API error:", err);
  }
  return DEFAULT_SUITES;
}

export async function createPrompt(payload: {
  name: string;
  version_tag: string;
  system_prompt: string;
  model_provider?: string;
  model_id?: string;
  temperature?: number;
  tools_schema?: any[];
}): Promise<PromptVersion> {
  const res = await fetch(`${API_BASE}/prompts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    // If backend fails, create a local object for immediate UI preview
    const fallback: PromptVersion = {
      id: "prompt-" + Date.now().toString(16),
      name: payload.name,
      version_tag: payload.version_tag,
      status: "DRAFT",
      system_prompt: payload.system_prompt,
      model_provider: payload.model_provider || "ollama",
      model_id: payload.model_id || "qwen2.5:7b-instruct-q4_K_M",
      temperature: payload.temperature ?? 0.2,
      tools_schema: payload.tools_schema || [],
      content_sha256: "local-draft-" + Date.now(),
      created_at: new Date().toISOString(),
    };
    return fallback;
  }
  return res.json();
}

export async function fetchRuns(): Promise<EvalRun[]> {
  try {
    const res = await fetch(`${API_BASE}/runs`);
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) return data;
    }
  } catch (err) {
    console.warn("Using fallback runs due to API error:", err);
  }
  return DEFAULT_RUNS;
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

export async function fetchCascadeMetrics(): Promise<CascadeMetrics> {
  const res = await fetch(`${API_BASE}/metrics/cascade`);
  if (!res.ok) throw new Error("Failed to fetch live cascade telemetry");
  return res.json();
}

export interface CustomScenarioPayload {
  name: string;
  language: string;
  budget_phrase?: string;
  bhk?: number;
  mood?: string;
  opening_line: string;
  inject_asr_noise?: boolean;
  inject_tool_503?: boolean;
  trigger_dnc?: boolean;
  rera_trap?: boolean;
  buyer_profile?: {
    budget: string;
    configuration: string;
    mood: string;
  };
  stress_switches?: {
    asr_noise: boolean;
    tool_503: boolean;
    dnc_trigger: boolean;
    rera_trap: boolean;
  };
  expected_hard_gates?: Record<string, boolean> | string[];
}

export async function createCustomScenario(payload: CustomScenarioPayload): Promise<ScenarioSuite> {
  try {
    const res = await fetch(`${API_BASE}/suites/custom-scenario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Custom scenario API fallback:", err);
  }

  // Client-side fallback suite so user can evaluate immediately
  const id = "suite-custom-" + Date.now().toString(16);
  const fallbackSuite: ScenarioSuite = {
    id,
    name: payload.name ? `Custom: ${payload.name}` : "Custom Interactive Scenario",
    suite_tier: "custom_interactive",
    version_tag: "v1.0.0-custom",
    scenario_count: 1,
    scenarios_json: [
      {
        scenario_id: "custom_" + Date.now().toString(16).slice(-6),
        name: payload.name,
        buyer_profile: payload.buyer_profile,
        opening_line: payload.opening_line,
        stress_switches: payload.stress_switches,
        expected_hard_gates: payload.expected_hard_gates,
      },
    ],
    content_sha256: "custom-" + Date.now(),
    created_at: new Date().toISOString(),
  };
  return fallbackSuite;
}

export interface LayaPredictResponse {
  text: string;
  task: string;
  predicted_label: string;
  confidence: number;
  margin: number;
  system_tier: string;
  status: string;
  latency_ms: number;
  cost_usd: number;
  escalation_reason?: string | null;
}

export async function predictLayaTurn(text: string): Promise<LayaPredictResponse> {
  try {
    const res = await fetch(`${API_BASE}/metrics/laya/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (res.ok) {
      return await res.json();
    }
  } catch (err) {
    console.warn("Laya predict API fallback:", err);
  }

  // Defensive client-side heuristic fallback
  const t = text.toLowerCase();
  const isEscalated =
    t.includes("done samjho") ||
    t.includes("pakka done") ||
    (t.includes("kya") && (t.includes("dnc") || t.includes("call")));
  return {
    text,
    task: t.includes("ignore")
      ? "prompt_injection"
      : t.includes("call") || t.includes("mat")
      ? "dnc_refusal"
      : "action_confirmation",
    predicted_label: isEscalated ? "ESCALATED" : "RESOLVED",
    confidence: isEscalated ? 0.62 : 0.985,
    margin: isEscalated ? 0.24 : 0.88,
    system_tier: isEscalated ? "SYSTEM_2" : "SYSTEM_1",
    status: isEscalated ? "ESCALATED_SYSTEM2" : "SYSTEM1_RESOLVED",
    latency_ms: 0.38,
    cost_usd: isEscalated ? 0.025 : 0.0,
    escalation_reason: isEscalated
      ? "Colloquial idiom detected: requires System-2 frontier reasoning"
      : null,
  };
}
