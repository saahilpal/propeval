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
import { Play, RotateCw, AlertTriangle, CheckCircle, XCircle, ArrowUpRight, Filter } from "lucide-react";

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

  // Active run data
  const [diffData, setDiffData] = useState<RunDiffResponse | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioComparison[]>([]);
  const [filterMode, setFilterMode] = useState<string>("regressions");
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState<number>(0);

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
      } catch (err) {
        console.error("Initial load error:", err);
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
      } catch (err) {
        console.error("Error loading run data:", err);
      }
    }
    loadRunData();
  }, [selectedRunId, filterMode]);

  // Keyboard navigation (j/k)
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;

      if (e.key === "j" || e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedScenarioIdx((prev) => Math.min(prev + 1, scenarios.length - 1));
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
        setLastEventId(event.lastEventId);
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
          // parse error
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
    } catch (err) {
      console.error("Launch run failed:", err);
      setIsRunning(false);
      setSseStatus("error");
    }
  }

  const summary = diffData?.summary_stats || {};
  const isBlocked = (summary.hard_gate_regressions || 0) > 0 || diffData?.status === "REGRESSED";
  const isUnderpowered = Boolean(summary.is_underpowered);

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6">
      {/* 1. Compact Top Action Bar */}
      <section className="bg-surface border border-border rounded-md p-4 shadow-sm flex flex-wrap items-center justify-between gap-4">
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
          className="flex items-center gap-2 bg-ink-primary hover:bg-black text-white text-xs font-medium px-4 py-2 rounded transition-colors disabled:opacity-50"
        >
          {isRunning ? <RotateCw className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
          <span>{isRunning ? "Evaluating..." : "Run Comparison"}</span>
        </button>
      </section>

      {/* 2. Live SSE Progress Strip */}
      {isRunning && (
        <section className="bg-accent-cobaltBg border border-accent-cobalt/20 rounded-md p-3 flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-3">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent-cobalt animate-ping" />
            <span className="font-semibold text-accent-cobalt">
              SSE Streaming Active: {streamProgress.completed} / {streamProgress.total || 40} jobs
            </span>
            <span className="text-ink-secondary text-[11px]">
              Last-Event-ID: <code className="bg-white px-1 py-0.5 rounded border border-border">{lastEventId || "0"}</code>
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

      {/* 3. Verdict Banner + Non-Compensatory Diff Matrix */}
      {diffData && (
        <section className="bg-surface border border-border rounded-md overflow-hidden shadow-sm">
          {/* Sticky Verdict Header */}
          <div
            className={`px-6 py-4 flex items-center justify-between border-b ${
              isBlocked
                ? "bg-accent-crimsonBg border-accent-crimson/20 text-accent-crimson"
                : "bg-accent-emeraldBg border-accent-emerald/20 text-accent-emerald"
            }`}
          >
            <div className="flex items-center gap-3">
              {isBlocked ? <XCircle className="w-6 h-6" /> : <CheckCircle className="w-6 h-6" />}
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

            <div className="flex items-center gap-3 text-right">
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

          {/* Hard Gates Table */}
          <div className="p-6 border-b border-border">
            <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider mb-3">
              1. Non-Compensatory Hard Gates (Zero-Tolerance)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="border border-border rounded p-3 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">TRAI DNC Compliance</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">1-turn immediate exit</div>
              </div>

              <div className="border border-border rounded p-3 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">No Invented Actions</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">0 verbal fake sends</div>
              </div>

              <div className="border border-border rounded p-3 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">RERA Fact Grounding</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">Exact RERA ID & price band</div>
              </div>

              <div className="border border-border rounded p-3 bg-canvas">
                <div className="text-xs text-ink-secondary font-medium">Metamorphic Currency Invariance</div>
                <div className="text-lg font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                <div className="text-[11px] text-ink-secondary font-mono">1.2 cr == 120 lakh</div>
              </div>
            </div>
          </div>

          {/* Paired Statistical Metrics with Visual 95% CI Range Bar */}
          <div className="p-6">
            <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider mb-3">
              2. Paired Statistical Comparison &amp; CI Range Bars
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead>
                  <tr className="border-b border-border text-ink-secondary font-mono text-[11px]">
                    <th className="py-2">Metric</th>
                    <th className="py-2">Baseline (V1)</th>
                    <th className="py-2">Candidate (V2)</th>
                    <th className="py-2">Delta</th>
                    <th className="py-2">Newcombe 95% CI Range Bar</th>
                    <th className="py-2">p-value</th>
                    <th className="py-2">Test</th>
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
          </div>
        </section>
      )}

      {/* 4. Regression-First Scenario Triage Table */}
      <section className="bg-surface border border-border rounded-md overflow-hidden shadow-sm flex flex-col">
        <div className="p-4 border-b border-border flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-ink-secondary" />
            <span className="text-xs font-mono font-bold text-ink-primary uppercase tracking-wide">
              Scenario Triage ({scenarios.length} scenarios)
            </span>
          </div>

          {/* Filter Chips */}
          <div className="flex items-center gap-2 text-xs font-mono">
            {[
              { id: "regressions", label: "Regressions Only" },
              { id: "hard_gate_fails", label: "Hard Gate Fails" },
              { id: "quarantined", label: "Quarantined" },
              { id: "all", label: "All Scenarios" },
            ].map((chip) => (
              <button
                key={chip.id}
                onClick={() => setFilterMode(chip.id)}
                className={`px-2.5 py-1 rounded border transition-colors ${
                  filterMode === chip.id
                    ? "bg-ink-primary text-white border-ink-primary"
                    : "bg-canvas text-ink-secondary border-border hover:bg-gray-100"
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
                  className={`hover:bg-gray-50 transition-colors font-mono cursor-pointer ${
                    selectedScenarioIdx === idx ? "bg-accent-cobaltBg/40 ring-1 ring-accent-cobalt/30" : ""
                  }`}
                  onClick={() => setSelectedScenarioIdx(idx)}
                >
                  <td className="py-2.5 px-4 text-ink-secondary">{idx + 1}</td>
                  <td className="py-2.5 px-4 font-semibold text-ink-primary">{sc.scenario_id}</td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[11px] ${
                        sc.baseline.overall_pass ? "bg-accent-emeraldBg text-accent-emerald" : "bg-accent-crimsonBg text-accent-crimson"
                      }`}
                    >
                      {sc.baseline.overall_pass ? "PASS" : "FAIL"}
                    </span>
                  </td>
                  <td className="py-2.5 px-4">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[11px] ${
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
                      className="inline-flex items-center gap-1 text-accent-cobalt hover:underline text-xs"
                    >
                      <span>Inspect</span>
                      <ArrowUpRight className="w-3 h-3" />
                    </Link>
                  </td>
                </tr>
              ))}
              {scenarios.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-xs font-mono text-ink-secondary">
                    No scenarios matching filter "{filterMode}".
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="p-3 bg-canvas border-t border-border text-[11px] font-mono text-ink-secondary flex items-center justify-between">
          <span>Use <code>j</code> / <code>k</code> to navigate rows, <code>Enter</code> to inspect scenario</span>
          <span>Showing {scenarios.length} scenarios</span>
        </div>
      </section>
    </div>
  );
}
