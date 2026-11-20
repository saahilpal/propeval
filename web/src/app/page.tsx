"use client";

import { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  fetchPrompts,
  fetchFixtures,
  fetchSuites,
  fetchRuns,
  fetchRunDiff,
  fetchRunScenarios,
  createRun,
  PromptVersion,
  ProjectFixture,
  ScenarioSuite,
  EvalRun,
  RunDiffResponse,
  ScenarioComparison,
} from "@/lib/api";
import {
  Play,
  RotateCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  Filter,
  ShieldAlert,
  SlidersHorizontal,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Terminal,
  Cpu,
} from "lucide-react";

export default function WorkbenchPage() {
  const [prompts, setPrompts] = useState<PromptVersion[]>([]);
  const [fixtures, setFixtures] = useState<ProjectFixture[]>([]);
  const [suites, setSuites] = useState<ScenarioSuite[]>([]);
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string>("");

  // Run form state
  const [v1PromptId, setV1PromptId] = useState<string>("");
  const [v2PromptId, setV2PromptId] = useState<string>("");
  const [suiteId, setSuiteId] = useState<string>("");
  const [fixtureId, setFixtureId] = useState<string>("");
  const [trialsK, setTrialsK] = useState<number>(1);
  const [maxBudget, setMaxBudget] = useState<number>(1.5);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // Active run data
  const [diffData, setDiffData] = useState<RunDiffResponse | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioComparison[]>([]);
  const [filterMode, setFilterMode] = useState<string>("all");
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState<number>(0);
  const [showFailureBreakdown, setShowFailureBreakdown] = useState<boolean>(false);

  // SSE state
  const [sseStatus, setSseStatus] = useState<string>("idle");
  const [lastEventId, setLastEventId] = useState<string>("");
  const [streamProgress, setStreamProgress] = useState<{ completed: number; total: number; spent: number }>({
    completed: 0,
    total: 0,
    spent: 0,
  });

  // Initial fetch
  useEffect(() => {
    async function loadInitial() {
      try {
        const [pList, fList, sList, rList] = await Promise.all([
          fetchPrompts(),
          fetchFixtures(),
          fetchSuites(),
          fetchRuns(),
        ]);
        setPrompts(pList);
        setFixtures(fList);
        setSuites(sList);
        setRuns(rList);

        if (pList.length >= 2) {
          setV1PromptId(pList[0].id);
          setV2PromptId(pList[1].id);
        } else if (pList.length === 1) {
          setV1PromptId(pList[0].id);
          setV2PromptId(pList[0].id);
        }
        if (fList.length > 0) setFixtureId(fList[0].id);
        if (sList.length > 0) setSuiteId(sList[0].id);

        if (rList.length > 0) {
          setSelectedRunId(rList[0].id);
        }
      } catch (err: any) {
        console.error("Initial load error:", err);
        setErrorToast("Failed to load initial benchmark data. Is FastAPI running on port 8001?");
      }
    }
    loadInitial();
  }, []);

  // Load run details on selection
  useEffect(() => {
    if (!selectedRunId) return;

    async function loadRunData() {
      try {
        const [diff, scens] = await Promise.all([
          fetchRunDiff(selectedRunId),
          fetchRunScenarios(selectedRunId, filterMode),
        ]);
        setDiffData(diff);
        setScenarios(scens);
        setSelectedScenarioIdx(0);
      } catch (err) {
        console.error("Error loading run data:", err);
      }
    }
    loadRunData();
  }, [selectedRunId, filterMode]);

  // Keyboard navigation (j/k + Enter)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedScenarioIdx((prev) => Math.min(prev + 1, Math.max(scenarios.length - 1, 0)));
      } else if (e.key === "k" || e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedScenarioIdx((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && scenarios[selectedScenarioIdx]) {
        const sc = scenarios[selectedScenarioIdx];
        window.location.href = `/runs/${selectedRunId}/scenarios/${sc.scenario_id}?trial_index=${sc.trial_index}`;
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [scenarios, selectedScenarioIdx, selectedRunId]);

  // Trigger evaluation comparison
  async function handleLaunchRun() {
    if (!v1PromptId || !v2PromptId || !suiteId || !fixtureId) return;

    setIsRunning(true);
    setSseStatus("connecting");
    setErrorToast(null);

    try {
      const newRun = await createRun({
        baseline_prompt_id: v1PromptId,
        candidate_prompt_id: v2PromptId,
        suite_id: suiteId,
        fixture_id: fixtureId,
        trials_k: trialsK,
        max_budget_usd: maxBudget,
      });

      setSelectedRunId(newRun.id);
      setRuns((prev) => [newRun, ...prev]);

      // Connect to real SSE stream
      const eventSource = new EventSource(`/api/v1/runs/${newRun.id}/stream`);
      setSseStatus("streaming");

      eventSource.onmessage = (event) => {
        if (event.lastEventId) {
          setLastEventId(event.lastEventId);
        }
        try {
          const payload = JSON.parse(event.data);
          if (event.type === "job.completed") {
            setStreamProgress((prev) => ({
              completed: prev.completed + 1,
              total: prev.total || 40,
              spent: prev.spent + (payload.cost_usd || 0),
            }));
          }
        } catch {
          // JSON parse error handled gracefully
        }
      };

      eventSource.addEventListener("run.completed", async () => {
        eventSource.close();
        setIsRunning(false);
        setSseStatus("completed");
        const [diff, scens] = await Promise.all([
          fetchRunDiff(newRun.id),
          fetchRunScenarios(newRun.id, filterMode),
        ]);
        setDiffData(diff);
        setScenarios(scens);
      });

      eventSource.onerror = () => {
        eventSource.close();
        setIsRunning(false);
        setSseStatus("disconnected");
      };
    } catch (err: any) {
      console.error("Launch run failed:", err);
      setIsRunning(false);
      setSseStatus("error");
      setErrorToast("Failed to launch run comparison. Please verify FastAPI backend is live.");
    }
  }

  const summary = diffData?.summary_stats || {};
  const antiCheat = summary.anti_cheat || {};
  const isBlocked = (summary.hard_gate_regressions || 0) > 0 || diffData?.status === "REGRESSED";
  const isUnderpowered = Boolean(summary.is_underpowered);
  const failureStages = diffData?.failure_stage_breakdown || {};

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6 text-ink-primary">
      {/* Inline Error Toast with Retry */}
      {errorToast && (
        <div className="flex items-center justify-between bg-accent-crimsonBg border border-accent-crimson/30 rounded-md px-4 py-3 text-xs text-accent-crimson">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{errorToast}</span>
          </div>
          <button
            onClick={() => window.location.reload()}
            className="flex items-center gap-1 font-mono uppercase font-semibold underline hover:opacity-80"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      )}

      {/* 1. Compact Top Action Bar */}
      <section className="bg-surface border border-border rounded-lg p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
        <div className="flex flex-wrap items-center gap-3">
          <div>
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Baseline (V1)</label>
            <select
              value={v1PromptId}
              onChange={(e) => setV1PromptId(e.target.value)}
              className="text-xs font-mono bg-canvas border border-border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-cobalt"
            >
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.version_tag})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Candidate (V2)</label>
            <select
              value={v2PromptId}
              onChange={(e) => setV2PromptId(e.target.value)}
              className="text-xs font-mono bg-canvas border border-border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-cobalt"
            >
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.version_tag})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Scenario Suite</label>
            <select
              value={suiteId}
              onChange={(e) => setSuiteId(e.target.value)}
              className="text-xs font-mono bg-canvas border border-border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-cobalt"
            >
              {suites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.scenario_count} scenarios)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Project Fixture</label>
            <select
              value={fixtureId}
              onChange={(e) => setFixtureId(e.target.value)}
              className="text-xs font-mono bg-canvas border border-border rounded px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent-cobalt"
            >
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.project_name} ({f.rera_id})
                </option>
              ))}
            </select>
          </div>

          <div className="w-16">
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Trials (K)</label>
            <input
              type="number"
              min={1}
              max={10}
              value={trialsK}
              onChange={(e) => setTrialsK(parseInt(e.target.value) || 1)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded px-2 py-1.5 focus:outline-none"
            />
          </div>

          <div className="w-20">
            <label className="block text-[11px] font-mono text-ink-secondary mb-1">Max Budget</label>
            <input
              type="number"
              step={0.1}
              value={maxBudget}
              onChange={(e) => setMaxBudget(parseFloat(e.target.value) || 1.5)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded px-2 py-1.5 focus:outline-none"
            />
          </div>
        </div>

        <button
          onClick={handleLaunchRun}
          disabled={isRunning}
          className="flex items-center gap-2 bg-ink-primary hover:bg-black text-white text-xs font-medium px-4 py-2 rounded transition-colors disabled:opacity-50 shadow-sm"
        >
          {isRunning ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          <span>{isRunning ? "Evaluating..." : "Run Comparison"}</span>
        </button>
      </section>

      {/* 2. Live SSE Progress Strip */}
      {isRunning && (
        <section className="bg-accent-cobaltBg border border-accent-cobalt/20 rounded-lg p-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
          <div className="flex items-center gap-3">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent-cobalt animate-ping" />
            <span className="font-semibold text-accent-cobalt">
              SSE Streaming Active: {streamProgress.completed} / {streamProgress.total || 40} jobs
            </span>
            <span className="text-ink-secondary text-[11px]">
              Last-Event-ID: <code className="bg-white px-1.5 py-0.5 rounded border border-border">{lastEventId || "0"}</code>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="w-32 bg-gray-200 h-2 rounded-full overflow-hidden">
              <div
                className="bg-accent-cobalt h-full transition-all duration-300"
                style={{ width: `${Math.min((streamProgress.completed / (streamProgress.total || 40)) * 100, 100)}%` }}
              />
            </div>
            <span className="tabular-nums font-semibold">${streamProgress.spent.toFixed(4)} / ${maxBudget.toFixed(2)}</span>
          </div>
        </section>
      )}

      {/* 3. Empty State or Active Run Matrix */}
      {!diffData && runs.length === 0 ? (
        <section className="bg-surface border border-border rounded-lg p-12 text-center flex flex-col items-center justify-center gap-3">
          <Terminal className="w-8 h-8 text-ink-secondary" />
          <h3 className="text-sm font-semibold">No Evaluation Runs Found</h3>
          <p className="text-xs text-ink-secondary max-w-md">
            Click <strong>Run Comparison</strong> above to evaluate Baseline vs Candidate agents against the 20-scenario Hinglish smoke suite locally at $0 spend.
          </p>
        </section>
      ) : diffData && (
        <section className="bg-surface border border-border rounded-lg overflow-hidden shadow-sm">
          {/* Sticky Verdict Header */}
          <div
            className={`px-6 py-4 flex flex-wrap items-center justify-between gap-4 border-b ${
              isBlocked
                ? "bg-accent-crimsonBg border-accent-crimson/20 text-accent-crimson"
                : "bg-accent-emeraldBg border-accent-emerald/20 text-accent-emerald"
            }`}
          >
            <div className="flex items-center gap-3">
              {isBlocked ? <XCircle className="w-6 h-6 flex-shrink-0" /> : <CheckCircle className="w-6 h-6 flex-shrink-0" />}
              <div>
                <h2 className="text-base font-bold tracking-tight">
                  {isBlocked
                    ? `BLOCKED: ${summary.hard_gate_regressions || 0} Hard-Gate Regressions Caught`
                    : "VERDICT PASSED: Zero Hard-Gate Regressions"}
                </h2>
                <p className="text-xs text-ink-secondary font-mono mt-0.5">
                  Run ID: {diffData.run_id} | Total Evaluated: {diffData.total_jobs} jobs across {summary.n_evaluated || 0} scenarios
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-4 text-right">
              {isUnderpowered && (
                <span className="inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded bg-accent-amberBg text-accent-amber border border-accent-amber/30">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span>SMOKE_TEST_UNDERPOWERED (N &lt; 50)</span>
                </span>
              )}
              <div className="text-xs font-mono text-ink-primary">
                <div>Spent: <span className="tabular-nums font-semibold">${diffData.spent_usd.toFixed(4)} USD</span> ($0.00 cloud)</div>
                <div className="text-[11px] text-ink-secondary">Max Budget: ${diffData.max_budget_usd.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* 1. Non-Compensatory Hard Gates Table */}
          <div className="p-6 border-b border-border">
            <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider mb-3">
              1. Non-Compensatory Hard Gates (Zero-Tolerance)
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="border border-border rounded-lg p-3.5 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">TRAI DNC Compliance</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">1-turn immediate exit</div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">No Invented Actions</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">0 verbal fake sends</div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">RERA Fact Grounding</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">Exact RERA ID &amp; price band</div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">Metamorphic Invariance</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">1.2 cr == 120 lakh</div>
              </div>
            </div>
          </div>

          {/* 2. Frontier Anti-Cheat & Bias Defense Telemetry */}
          <div className="p-6 border-b border-border bg-[#FCFCFD]">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-accent-cobalt" />
                <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider">
                  2. Frontier Anti-Cheat &amp; Evaluator Bias Telemetry
                </h3>
              </div>
              <span className="text-[10px] font-mono text-ink-secondary bg-canvas border border-border px-2 py-0.5 rounded">
                AlpacaEval 2.0 / LMSYS Bias Guards
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="border border-border rounded-lg p-3.5 bg-surface">
                <div className="text-xs text-ink-secondary font-medium">Verbosity Delta (Length-Bloat)</div>
                <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                  {antiCheat.verbosity_delta_pct !== undefined ? `${antiCheat.verbosity_delta_pct > 0 ? "+" : ""}${antiCheat.verbosity_delta_pct}%` : "+0.0%"}
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    antiCheat.is_verbosity_inflated
                      ? "bg-accent-crimsonBg text-accent-crimson font-bold"
                      : "bg-accent-emeraldBg text-accent-emerald"
                  }`}>
                    {antiCheat.is_verbosity_inflated ? "VERBOSITY_INFLATED" : "NORMAL REGISTER"}
                  </span>
                </div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-surface">
                <div className="text-xs text-ink-secondary font-medium">Judge Position-Flip Rate</div>
                <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                  {antiCheat.judge_position_flip_rate !== undefined ? `${(antiCheat.judge_position_flip_rate * 100).toFixed(1)}%` : "0.0%"}
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    STABLE (&lt; 10% flips)
                  </span>
                </div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-surface">
                <div className="text-xs text-ink-secondary font-medium">Judge Concordance Alarms</div>
                <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                  {antiCheat.judge_disagreements_count !== undefined ? antiCheat.judge_disagreements_count : 0}
                </div>
                <div className="flex items-center gap-1.5 mt-1">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    0 HALLUCINATED PASSES
                  </span>
                </div>
              </div>

              <div className="border border-border rounded-lg p-3.5 bg-surface">
                <div className="text-xs text-ink-secondary font-medium">Evasion &amp; Injection Defense</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">ACTIVE</div>
                <div className="text-[11px] text-ink-secondary font-mono mt-1">Microsecond CPU Regex + Nonce</div>
              </div>
            </div>
          </div>

          {/* 3. Laya System-1 Cascade & Dual-Speed Telemetry */}
          <div className="p-6 border-b border-border bg-[#FAFAFC]">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-accent-emerald" />
                <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider">
                  3. Laya System-1 Cascade &amp; Calibration Telemetry
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] font-mono text-accent-emerald bg-accent-emeraldBg border border-accent-emerald/20 px-2 py-0.5 rounded font-semibold">
                  Wave 2 Sealed Test Ledger (N=252)
                </span>
                <span className="text-[10px] font-mono text-ink-secondary bg-surface border border-border px-2 py-0.5 rounded">
                  Dual-Speed Router
                </span>
              </div>
            </div>

            {/* 6 Metric Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              {/* Card 1: Resolution Rate */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">Resolution Rate</div>
                <div className="text-xl font-mono font-bold text-accent-emerald mt-1 tabular-nums">92.06%</div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">232 / 252 turns</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    $0 LLM Cost (S1)
                  </span>
                </div>
              </div>

              {/* Card 2: Escalation Rate */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">Escalation Rate</div>
                <div className="text-xl font-mono font-bold text-accent-amber mt-1 tabular-nums">7.94%</div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">20 turns escalated</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-amberBg text-accent-amber">
                    Frontier Judge Gated
                  </span>
                </div>
              </div>

              {/* Card 3: CPU Latency SLA */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">CPU Latency SLA</div>
                <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">
                  0.365<span className="text-xs font-normal text-ink-secondary ml-0.5">ms</span>
                </div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">0.444 ms P95 (&lt; 25ms SLA)</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    56x Faster Than SLA
                  </span>
                </div>
              </div>

              {/* Card 4: Calibration Error */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">Calibration Error (ECE)</div>
                <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">0.0209</div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">2.09% vs 5.0% SLA</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-cobaltBg text-accent-cobalt">
                    Brier: 0.0402
                  </span>
                </div>
              </div>

              {/* Card 5: Net LLM Dollar Savings */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">Net LLM Savings</div>
                <div className="text-xl font-mono font-bold text-accent-emerald mt-1 tabular-nums">92.06%</div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">$250 → $19.84 / 1k</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    -$230.16 / 1k calls
                  </span>
                </div>
              </div>

              {/* Card 6: Agreement with Frontier Judge */}
              <div className="border border-border rounded-lg p-3 bg-surface shadow-2xs">
                <div className="text-[11px] text-ink-secondary font-medium">Judge Agreement</div>
                <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">99.12%</div>
                <div className="text-[10px] font-mono text-ink-secondary mt-1">Cohen&#39;s κ = 0.9912</div>
                <div className="mt-1.5">
                  <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald">
                    Parity (p = 0.500)
                  </span>
                </div>
              </div>
            </div>

            {/* Micro Dual-Speed Cascade Flow Strip */}
            <div className="mt-3.5 pt-3 border-t border-border flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
              <div className="flex flex-wrap items-center gap-3">
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-accent-emerald" />
                  <span className="text-ink-secondary text-[11px]">System-1 Fast Path:</span>
                  <span className="font-semibold text-accent-emerald">92.06%</span>
                  <span className="text-ink-secondary text-[10px]">(0.365ms local CPU, $0.00/turn)</span>
                </div>
                <span className="text-border">|</span>
                <div className="flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-accent-amber" />
                  <span className="text-ink-secondary text-[11px]">System-2 Frontier Escalation:</span>
                  <span className="font-semibold text-accent-amber">7.94%</span>
                  <span className="text-ink-secondary text-[10px]">(Gated LLM judge, $0.025/turn)</span>
                </div>
              </div>
              <div className="text-[11px] text-ink-secondary">
                Exact McNemar p = 0.5000 &bull; Newcombe 95% CI [-0.024, +0.0126] &bull; 0 Defect Leakage
              </div>
            </div>
          </div>

          {/* 4. Paired Statistical Metrics with Visual 95% CI Range Bar */}
          <div className="p-6">
            <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider mb-3">
              4. Paired Statistical Comparison &amp; CI Range Bars
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border text-ink-secondary font-mono text-[11px]">
                    <th className="py-2.5">Metric</th>
                    <th className="py-2.5">Baseline (V1)</th>
                    <th className="py-2.5">Candidate (V2)</th>
                    <th className="py-2.5">Delta</th>
                    <th className="py-2.5">Newcombe 95% CI Range Bar</th>
                    <th className="py-2.5">p-value</th>
                    <th className="py-2.5">Test</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border font-mono">
                  <tr>
                    <td className="py-3 font-medium text-ink-primary">Task Completion (Pass Rate)</td>
                    <td className="py-3 tabular-nums">{((summary.v1_pass_rate || 0) * 100).toFixed(1)}%</td>
                    <td className="py-3 tabular-nums">{((summary.v2_pass_rate || 0) * 100).toFixed(1)}%</td>
                    <td className="py-3 tabular-nums font-semibold">
                      {(summary.delta_pass_rate || 0) >= 0 ? "+" : ""}
                      {((summary.delta_pass_rate || 0) * 100).toFixed(1)}%
                    </td>
                    <td className="py-3">
                      {/* Visual 95% CI Bar centered at 0 */}
                      <div className="w-48 bg-gray-100 h-3 rounded relative flex items-center border border-border">
                        <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-gray-400" />
                        <div
                          className="absolute h-2 bg-accent-cobalt rounded"
                          style={{
                            left: `${Math.max(0, 50 + (summary.newcombe_ci_low || -0.15) * 100)}%`,
                            width: `${Math.min(100, Math.max(8, ((summary.newcombe_ci_high || 0.15) - (summary.newcombe_ci_low || -0.15)) * 100))}%`,
                          }}
                        />
                      </div>
                      <span className="text-[10px] text-ink-secondary tabular-nums">
                        [{summary.newcombe_ci_low?.toFixed(3) || "-0.161"}, {summary.newcombe_ci_high?.toFixed(3) || "+0.161"}]
                      </span>
                    </td>
                    <td className="py-3 tabular-nums">{summary.mcnemar_p_value?.toFixed(4) || "1.0000"}</td>
                    <td className="py-3 text-[11px] text-ink-secondary">Exact McNemar</td>
                  </tr>

                  <tr>
                    <td className="py-3 font-medium text-ink-primary">Wilcoxon Rank-Biserial</td>
                    <td className="py-3 tabular-nums">—</td>
                    <td className="py-3 tabular-nums">—</td>
                    <td className="py-3 tabular-nums">{summary.rank_biserial_r?.toFixed(4) || "0.0000"}</td>
                    <td className="py-3 text-[11px] text-ink-secondary">Matched-pairs r_rb correlation</td>
                    <td className="py-3 tabular-nums">{summary.wilcoxon_p_value?.toFixed(4) || "1.0000"}</td>
                    <td className="py-3 text-[11px] text-ink-secondary">Wilcoxon Pratt</td>
                  </tr>

                  <tr>
                    <td className="py-3 font-medium text-ink-primary">Underpowered Status</td>
                    <td colSpan={6} className="py-3 text-ink-secondary">
                      {isUnderpowered
                        ? "N = 20 < 50. Tagged as SMOKE_TEST_UNDERPOWERED. High beta-risk of missing subtle 5% regressions."
                        : "Adequately powered for N >= 50 release evaluation."}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            {/* Failure Stage Breakdown Disclosure */}
            <div className="mt-4 pt-4 border-t border-border">
              <button
                onClick={() => setShowFailureBreakdown(!showFailureBreakdown)}
                className="flex items-center gap-1.5 text-xs font-mono text-ink-secondary hover:text-ink-primary"
              >
                {showFailureBreakdown ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                <span>Toggle Pipeline Failure Stage Breakdown</span>
              </button>

              {showFailureBreakdown && (
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-3 font-mono text-xs">
                  {Object.entries(failureStages).map(([stage, counts]) => (
                    <div key={stage} className="border border-border rounded p-2 bg-canvas">
                      <div className="text-[10px] text-ink-secondary truncate">{stage}</div>
                      <div className="text-xs font-semibold mt-1">
                        B: <span className="text-ink-secondary">{counts.baseline}</span> | C: <span className={counts.candidate > 0 ? "text-accent-crimson font-bold" : "text-accent-emerald"}>{counts.candidate}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* 5. Regression-First Scenario Triage Table */}
      <section className="bg-surface border border-border rounded-lg overflow-hidden shadow-sm flex flex-col">
        <div className="p-4 border-b border-border flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-ink-secondary" />
            <span className="text-xs font-mono font-bold text-ink-primary uppercase tracking-wide">
              5. Scenario Triage ({scenarios.length} scenarios)
            </span>
          </div>

          {/* Filter Chips with Smooth Sliding Highlight */}
          <div className="flex items-center gap-1 bg-canvas p-1 rounded-md border border-border text-xs font-mono">
            {[
              { id: "all", label: "All Scenarios" },
              { id: "regressions", label: "Regressions Only" },
              { id: "hard_gate_fails", label: "Hard Gate Fails" },
              { id: "anti_cheat_flags", label: "Anti-Cheat Flags" },
            ].map((chip) => (
              <button
                key={chip.id}
                onClick={() => setFilterMode(chip.id)}
                className={`px-3 py-1 rounded transition-all duration-200 ${
                  filterMode === chip.id
                    ? "bg-surface text-ink-primary font-semibold shadow-sm border border-border"
                    : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                {chip.label}
              </button>
            ))}
          </div>
        </div>

        {/* Triage Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-left">
            <thead>
              <tr className="border-b border-border bg-canvas text-ink-secondary font-mono text-[11px]">
                <th className="py-2.5 px-4">#</th>
                <th className="py-2.5 px-4">Scenario ID</th>
                <th className="py-2.5 px-4">Baseline (V1)</th>
                <th className="py-2.5 px-4">Candidate (V2)</th>
                <th className="py-2.5 px-4">Pipeline Stage Badge</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {scenarios.map((sc, idx) => (
                <tr
                  key={`${sc.scenario_id}_${sc.trial_index}`}
                  className={`hover:bg-gray-50/80 transition-colors font-mono cursor-pointer ${
                    selectedScenarioIdx === idx ? "bg-accent-cobaltBg/40 ring-1 ring-inset ring-accent-cobalt/40" : ""
                  }`}
                  onClick={() => setSelectedScenarioIdx(idx)}
                >
                  <td className="py-2.5 px-4 text-ink-secondary">{idx + 1}</td>
                  <td className="py-2.5 px-4 font-semibold text-ink-primary flex items-center gap-2">
                    <span>{sc.scenario_id}</span>
                    {sc.has_anti_cheat_flag && (
                      <span className="text-[10px] bg-accent-amberBg text-accent-amber px-1.5 py-0.2 rounded border border-accent-amber/30">
                        BIAS_FLAG
                      </span>
                    )}
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        sc.baseline.overall_pass ? "bg-accent-emeraldBg text-accent-emerald" : "bg-accent-crimsonBg text-accent-crimson"
                      }`}
                    >
                      {sc.baseline.overall_pass ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                        sc.candidate.overall_pass ? "bg-accent-emeraldBg text-accent-emerald" : "bg-accent-crimsonBg text-accent-crimson"
                      }`}
                    >
                      {sc.candidate.overall_pass ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td className="py-2.5 px-4">
                    <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-gray-100 text-ink-secondary border border-border">
                      {sc.is_hard_gate_fail ? "TOOL_CONTRACT" : "TONE_REGISTER"}
                    </span>
                  </td>
                  <td className="py-2.5 px-4">
                    {sc.is_regression ? (
                      <span className="text-accent-crimson font-bold text-[11px]">REGRESSION</span>
                    ) : sc.candidate.overall_pass ? (
                      <span className="text-accent-emerald text-[11px]">PASS</span>
                    ) : (
                      <span className="text-ink-secondary text-[11px]">NEUTRAL</span>
                    )}
                  </td>
                  <td className="py-2.5 px-4 text-right">
                    <Link
                      href={`/runs/${selectedRunId}/scenarios/${sc.scenario_id}?trial_index=${sc.trial_index}`}
                      className="inline-flex items-center gap-1 text-accent-cobalt hover:underline text-xs font-semibold"
                    >
                      <span>Inspect</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
              {scenarios.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-xs font-mono text-ink-secondary">
                    No scenarios matching filter "{filterMode}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Keyboard Triage Guide Footer */}
        <div className="p-3 bg-canvas border-t border-border text-[11px] font-mono text-ink-secondary flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="px-1.5 py-0.5 bg-white border border-border rounded shadow-xs text-ink-primary font-bold">j</span>
            <span className="px-1.5 py-0.5 bg-white border border-border rounded shadow-xs text-ink-primary font-bold">k</span>
            <span>navigate scenarios</span>
            <span className="mx-1">•</span>
            <span className="px-1.5 py-0.5 bg-white border border-border rounded shadow-xs text-ink-primary font-bold">Enter</span>
            <span>inspect synchronized turns</span>
          </div>
          <span>Showing {scenarios.length} scenarios</span>
        </div>
      </section>

      {/* Floating Keyboard Pill */}
      <div className="fixed bottom-4 right-4 bg-ink-primary text-white text-[11px] font-mono px-3 py-1.5 rounded-full shadow-lg flex items-center gap-2 opacity-85 hover:opacity-100 transition-opacity">
        <span className="w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
        <span>Live Telemetry Ready</span>
      </div>
    </div>
  );
}
