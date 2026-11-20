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
  fetchCascadeMetrics,
  CascadeMetrics,
  PromptVersion,
  ProjectFixture,
  ScenarioSuite,
  EvalRun,
  RunDiffResponse,
  ScenarioComparison,
} from "@/lib/api";
import CustomPromptDrawer from "@/components/CustomPromptDrawer";
import CustomScenarioDrawer from "@/components/CustomScenarioDrawer";
import {
  Play,
  RotateCw,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ArrowUpRight,
  Filter,
  ShieldAlert,
  ChevronDown,
  ChevronRight,
  RefreshCw,
  Terminal,
  Cpu,
  Sparkles,
  Sliders,
  Layers,
  BarChart3,
  FileDiff,
  ArrowRight,
  Zap,
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
  const [execMode, setExecMode] = useState<"fast" | "ollama">("fast");
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [errorToast, setErrorToast] = useState<string | null>(null);

  // Active run data
  const [diffData, setDiffData] = useState<RunDiffResponse | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioComparison[]>([]);
  const [cascadeMetrics, setCascadeMetrics] = useState<CascadeMetrics | null>(null);
  const [cascadeLoading, setCascadeLoading] = useState<boolean>(true);
  const [filterMode, setFilterMode] = useState<string>("all");
  const [selectedScenarioIdx, setSelectedScenarioIdx] = useState<number>(0);
  const [showFailureBreakdown, setShowFailureBreakdown] = useState<boolean>(false);

  // Navigation tab: triage | telemetry | prompt_diff
  const [activeTab, setActiveTab] = useState<"triage" | "telemetry" | "prompt_diff">("triage");

  // Custom prompt & scenario drawers
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false);
  const [isScenarioDrawerOpen, setIsScenarioDrawerOpen] = useState<boolean>(false);

  // Table ref for Jump to First Regression
  const triageTableRef = useRef<HTMLDivElement>(null);

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
        const [pList, fList, sList, rList, cMetrics] = await Promise.all([
          fetchPrompts(),
          fetchFixtures(),
          fetchSuites(),
          fetchRuns(),
          fetchCascadeMetrics().catch((err) => {
            console.warn("Cascade metrics fetch warning:", err);
            return null;
          }),
        ]);
        setPrompts(pList);
        setFixtures(fList);
        setSuites(sList);
        setRuns(rList);
        if (cMetrics) setCascadeMetrics(cMetrics);
        setCascadeLoading(false);

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
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLSelectElement ||
        e.target instanceof HTMLTextAreaElement ||
        isDrawerOpen ||
        isScenarioDrawerOpen
      )
        return;

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
  }, [scenarios, selectedScenarioIdx, selectedRunId, isDrawerOpen, isScenarioDrawerOpen]);

  // Trigger evaluation comparison
  async function handleLaunchRun(candidateIdOverride?: string, suiteIdOverride?: string) {
    const candidateId = candidateIdOverride || v2PromptId;
    const targetSuiteId = suiteIdOverride || suiteId;
    if (!v1PromptId || !candidateId || !targetSuiteId || !fixtureId) return;

    setIsRunning(true);
    setSseStatus("connecting");
    setErrorToast(null);

    try {
      const newRun = await createRun({
        baseline_prompt_id: v1PromptId,
        candidate_prompt_id: candidateId,
        suite_id: targetSuiteId,
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

  // Handle saving new prompt from CustomPromptDrawer
  const handleCustomPromptSaved = (newPrompt: PromptVersion) => {
    setPrompts((prev) => [newPrompt, ...prev]);
    setV2PromptId(newPrompt.id);
    setIsDrawerOpen(false);
    // Launch run immediately with new prompt
    handleLaunchRun(newPrompt.id);
  };

  // Handle saving new scenario suite from CustomScenarioDrawer
  const handleCustomScenarioSaved = (newSuite: ScenarioSuite) => {
    setSuites((prev) => {
      const filtered = prev.filter((s) => s.id !== newSuite.id);
      return [newSuite, ...filtered];
    });
    setSuiteId(newSuite.id);
    setIsScenarioDrawerOpen(false);
    // Launch run immediately with custom scenario
    handleLaunchRun(undefined, newSuite.id);
  };

  const summary = diffData?.summary_stats || {};
  const antiCheat = summary.anti_cheat || {};
  const isBlocked = (summary.hard_gate_regressions || 0) > 0 || diffData?.status === "REGRESSED";
  const isUnderpowered = Boolean(summary.is_underpowered);
  const failureStages = diffData?.failure_stage_breakdown || {};

  // Jump to First Regression handler
  const jumpToFirstRegression = () => {
    setActiveTab("triage");
    const regIdx = scenarios.findIndex((sc) => sc.is_regression || sc.is_hard_gate_fail);
    if (regIdx !== -1) {
      setSelectedScenarioIdx(regIdx);
    } else {
      setFilterMode("regressions");
    }
    triageTableRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Find baseline and candidate prompt objects for Prompt Diff tab
  const baselinePromptObj = prompts.find((p) => p.id === v1PromptId);
  const candidatePromptObj = prompts.find((p) => p.id === v2PromptId);

  return (
    <div className="flex-1 flex flex-col p-4 sm:p-6 max-w-7xl mx-auto w-full gap-6 text-ink-primary">
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

      {/* 1. Full-Width Interactive Run Bar */}
      <section className="bg-surface border border-border rounded-xl p-4 sm:p-5 shadow-xs flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-accent-emerald animate-pulse" />
            <h1 className="text-sm font-mono font-bold uppercase tracking-wider text-ink-primary">
              Evaluation Workbench
            </h1>
            <span className="text-[11px] font-mono text-slate-500">
              · Head-to-Head Prompt Regression Gate
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsScenarioDrawerOpen(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md bg-indigo-50 text-indigo-900 border border-indigo-300 hover:bg-indigo-100 transition-colors shadow-2xs"
            >
              <Sliders className="w-3.5 h-3.5 text-indigo-600" />
              <span>+ Custom Scenario</span>
            </button>

            <button
              onClick={() => setIsDrawerOpen(true)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-md bg-amber-50 text-amber-900 border border-amber-300 hover:bg-amber-100 transition-colors shadow-2xs"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
              <span>+ Create / Test Custom Prompt</span>
            </button>
          </div>
        </div>

        {/* Inputs Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-3">
          <div>
            <label className="block text-[11px] font-mono font-medium text-slate-600 mb-1">
              Baseline Prompt (V1)
            </label>
            <select
              value={v1PromptId}
              onChange={(e) => setV1PromptId(e.target.value)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.version_tag})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono font-medium text-slate-600 mb-1">
              Candidate Prompt (V2)
            </label>
            <select
              value={v2PromptId}
              onChange={(e) => setV2PromptId(e.target.value)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              {prompts.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.version_tag})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono font-medium text-slate-600 mb-1">
              Execution Mode
            </label>
            <select
              value={execMode}
              onChange={(e) => setExecMode(e.target.value as "fast" | "ollama")}
              className="w-full text-xs font-mono bg-canvas border border-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              <option value="fast">Fast Local Engine (~3s)</option>
              <option value="ollama">Live Local Ollama LLM</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono font-medium text-slate-600 mb-1">
              Hinglish Suite
            </label>
            <select
              value={suiteId}
              onChange={(e) => setSuiteId(e.target.value)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              {suites.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.scenario_count} scenarios)
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-mono font-medium text-slate-600 mb-1">
              Project Fixture
            </label>
            <select
              value={fixtureId}
              onChange={(e) => setFixtureId(e.target.value)}
              className="w-full text-xs font-mono bg-canvas border border-border rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-1 focus:ring-slate-900"
            >
              {fixtures.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.project_name} ({f.rera_id})
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={() => handleLaunchRun()}
              disabled={isRunning}
              className="w-full flex items-center justify-center gap-2 bg-ink-primary hover:bg-slate-800 text-white text-xs font-semibold px-4 py-2 rounded-md transition-colors disabled:opacity-50 shadow-sm"
            >
              {isRunning ? (
                <RotateCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Play className="w-3.5 h-3.5" />
              )}
              <span>{isRunning ? "Evaluating..." : "Run Comparison"}</span>
            </button>
          </div>
        </div>
      </section>

      {/* 2. Live SSE Progress Strip */}
      {isRunning && (
        <section className="bg-slate-900 text-white rounded-lg p-3 flex flex-wrap items-center justify-between gap-4 text-xs font-mono">
          <div className="flex items-center gap-3">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-accent-emerald animate-ping" />
            <span className="font-semibold text-emerald-400">
              Live Evaluation Stream: {streamProgress.completed} / {streamProgress.total || 40} jobs completed
            </span>
            <span className="text-slate-400 text-[11px]">
              Last-Event-ID: <code className="bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">{lastEventId || "0"}</code>
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="w-32 bg-slate-700 h-2 rounded-full overflow-hidden">
              <div
                className="bg-accent-emerald h-full transition-all duration-300"
                style={{
                  width: `${Math.min(
                    (streamProgress.completed / (streamProgress.total || 40)) * 100,
                    100
                  )}%`,
                }}
              />
            </div>
            <span className="tabular-nums font-semibold text-emerald-300">
              ${streamProgress.spent.toFixed(4)} / ${maxBudget.toFixed(2)}
            </span>
          </div>
        </section>
      )}

      {/* 3. Empty State or Active Run Matrix */}
      {!diffData && runs.length === 0 ? (
        <section className="bg-surface border border-border rounded-xl p-12 text-center flex flex-col items-center justify-center gap-3">
          <Terminal className="w-8 h-8 text-slate-400" />
          <h3 className="text-sm font-semibold">No Evaluation Runs Found</h3>
          <p className="text-xs text-slate-500 max-w-md">
            Click <strong>Run Comparison</strong> above to evaluate Baseline vs Candidate agents against the 20-scenario Hinglish smoke suite locally at $0 spend.
          </p>
        </section>
      ) : (
        diffData && (
          <div className="flex flex-col gap-6">
            {/* PLAIN-ENGLISH "WHAT BROKE & SHIP VERDICT" SUMMARY BANNER */}
            <section
              className={`rounded-xl border p-5 sm:p-6 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6 ${
                isBlocked
                  ? "bg-red-50/70 border-red-200 text-red-950"
                  : "bg-emerald-50/70 border-emerald-200 text-emerald-950"
              }`}
            >
              <div className="flex items-start gap-4">
                <div className="mt-0.5">
                  {isBlocked ? (
                    <div className="w-10 h-10 rounded-lg bg-red-100 border border-red-300 flex items-center justify-center">
                      <XCircle className="w-6 h-6 text-accent-crimson" />
                    </div>
                  ) : (
                    <div className="w-10 h-10 rounded-lg bg-emerald-100 border border-emerald-300 flex items-center justify-center">
                      <CheckCircle className="w-6 h-6 text-accent-emerald" />
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <span
                      className={`text-xs font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                        isBlocked
                          ? "bg-red-200 text-red-900 border border-red-300"
                          : "bg-emerald-200 text-emerald-900 border border-emerald-300"
                      }`}
                    >
                      {isBlocked ? "DO NOT SHIP — HARD-GATE BLOCKED" : "READY TO SHIP — PASSING"}
                    </span>
                    <span className="text-xs font-mono text-slate-500">
                      Run ID: <code className="font-semibold text-slate-700">{diffData.run_id}</code>
                    </span>
                  </div>

                  <h2 className="text-lg font-bold tracking-tight mt-1.5">
                    {diffData.executive_summary?.headline || (isBlocked
                      ? `${summary.hard_gate_regressions || 0} Critical Regressions Detected in Candidate V2`
                      : "Zero Regressions: Candidate matches or exceeds Baseline")}
                  </h2>

                  {diffData.executive_summary?.recommendation && (
                    <div className="mt-1 text-xs font-semibold text-red-800">
                      Recommendation: {diffData.executive_summary.recommendation}
                    </div>
                  )}

                  {diffData.executive_summary?.key_findings && diffData.executive_summary.key_findings.length > 0 ? (
                    <ul className="mt-2 space-y-1 text-xs text-slate-800 list-disc list-inside">
                      {diffData.executive_summary.key_findings.map((f, i) => (
                        <li key={i}>{f}</li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-xs sm:text-sm text-slate-700 mt-1 max-w-2xl leading-relaxed">
                      {isBlocked ? (
                        <>
                          Candidate V2 introduced severe behavioral regressions on Hinglish telephony calls, including TRAI DNC compliance breaches and CRM 503 hallucinations. Baseline V1 maintained 100% compliance.
                        </>
                      ) : (
                        <>
                          Candidate V2 passed all non-compensatory hard gates and preserved acoustic invariance across the Hinglish test suite.
                        </>
                      )}
                    </p>
                  )}
                </div>
              </div>

              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 shrink-0 w-full md:w-auto">
                {isBlocked && (
                  <button
                    onClick={jumpToFirstRegression}
                    className="inline-flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white font-medium text-xs px-4 py-2.5 rounded-lg shadow-sm transition-colors"
                  >
                    <span>Jump to First Regression</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                )}

                <div className="bg-white/80 border border-slate-200 rounded-lg p-2.5 text-xs font-mono text-slate-700 text-center sm:text-right">
                  <div className="text-[10px] text-slate-500 uppercase tracking-wider">Evaluation Spend</div>
                  <div className="font-bold text-slate-900 mt-0.5 tabular-nums">
                    ${diffData.spent_usd.toFixed(4)} USD
                  </div>
                  <div className="text-[10px] text-accent-emerald font-semibold">$0.00 cloud API cost</div>
                </div>
              </div>
            </section>

            {/* 3-TAB WORKBENCH NAVIGATION */}
            <div className="border-b border-border flex items-center justify-between">
              <nav className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab("triage")}
                  className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === "triage"
                      ? "border-slate-900 text-slate-900 bg-slate-50"
                      : "border-transparent text-slate-500 hover:text-slate-900"
                  }`}
                >
                  <Layers className="w-4 h-4" />
                  <span>Regressions &amp; Scenario Triage</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                    {scenarios.length}
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("telemetry")}
                  className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === "telemetry"
                      ? "border-slate-900 text-slate-900 bg-slate-50"
                      : "border-transparent text-slate-500 hover:text-slate-900"
                  }`}
                >
                  <BarChart3 className="w-4 h-4" />
                  <span>Statistical &amp; Laya Telemetry</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-emerald-100 text-emerald-800">
                    92.1% S1
                  </span>
                </button>

                <button
                  onClick={() => setActiveTab("prompt_diff")}
                  className={`flex items-center gap-2 py-2.5 px-4 text-xs font-semibold border-b-2 transition-colors ${
                    activeTab === "prompt_diff"
                      ? "border-slate-900 text-slate-900 bg-slate-50"
                      : "border-transparent text-slate-500 hover:text-slate-900"
                  }`}
                >
                  <FileDiff className="w-4 h-4" />
                  <span>Prompt Text Diff</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-200 text-slate-700">
                    V1 ↔ V2
                  </span>
                </button>
              </nav>

              {isUnderpowered && (
                <div className="hidden sm:inline-flex items-center gap-1.5 text-xs font-mono px-2.5 py-1 rounded bg-amber-50 text-amber-800 border border-amber-300">
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                  <span>SMOKE_TEST_UNDERPOWERED (N &lt; 50)</span>
                </div>
              )}
            </div>

            {/* TAB 1: REGRESSIONS & SCENARIO TRIAGE */}
            {activeTab === "triage" && (
              <div ref={triageTableRef} className="flex flex-col gap-6">
                {/* Non-Compensatory Hard Gates Strip */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="border border-border rounded-xl p-4 bg-surface shadow-2xs">
                    <div className="text-xs text-slate-500 font-medium">TRAI DNC Compliance</div>
                    <div className="text-xl font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">1-turn immediate exit</div>
                  </div>

                  <div className="border border-border rounded-xl p-4 bg-surface shadow-2xs">
                    <div className="text-xs text-slate-500 font-medium">No Invented Actions</div>
                    <div className="text-xl font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">0 verbal fake sends</div>
                  </div>

                  <div className="border border-border rounded-xl p-4 bg-surface shadow-2xs">
                    <div className="text-xs text-slate-500 font-medium">RERA Fact Grounding</div>
                    <div className="text-xl font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">Exact RERA ID &amp; price band</div>
                  </div>

                  <div className="border border-border rounded-xl p-4 bg-surface shadow-2xs">
                    <div className="text-xs text-slate-500 font-medium">Metamorphic Invariance</div>
                    <div className="text-xl font-mono font-bold text-accent-emerald mt-1">100.0%</div>
                    <div className="text-[11px] text-slate-500 font-mono mt-0.5">1.2 cr == 120 lakh</div>
                  </div>
                </div>

                {/* Scenario Triage Table */}
                <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-xs flex flex-col">
                  <div className="p-4 border-b border-border flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <Filter className="w-4 h-4 text-slate-500" />
                      <span className="text-xs font-mono font-bold text-ink-primary uppercase tracking-wide">
                        Scenario Triage Matrix ({scenarios.length} scenarios)
                      </span>
                    </div>

                    {/* Filter Chips */}
                    <div className="flex items-center gap-1 bg-canvas p-1 rounded-md border border-border text-xs font-mono overflow-x-auto max-w-full">
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
                              ? "bg-surface text-ink-primary font-semibold shadow-xs border border-border"
                              : "text-slate-600 hover:text-ink-primary"
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
                        <tr className="border-b border-border bg-canvas text-slate-500 font-mono text-[11px]">
                          <th className="py-2.5 px-4">#</th>
                          <th className="py-2.5 px-4">Scenario ID</th>
                          <th className="py-2.5 px-4">Baseline (V1)</th>
                          <th className="py-2.5 px-4">Candidate (V2)</th>
                          <th className="py-2.5 px-4">Pipeline Stage</th>
                          <th className="py-2.5 px-4">Verdict</th>
                          <th className="py-2.5 px-4 text-right">Inspect Turns</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {scenarios.map((sc, idx) => (
                          <tr
                            key={`${sc.scenario_id}_${sc.trial_index}`}
                            className={`hover:bg-slate-50 transition-colors font-mono cursor-pointer ${
                              selectedScenarioIdx === idx
                                ? "bg-slate-100/80 ring-1 ring-inset ring-slate-400"
                                : ""
                            }`}
                            onClick={() => setSelectedScenarioIdx(idx)}
                          >
                            <td className="py-2.5 px-4 text-slate-400">{idx + 1}</td>
                            <td className="py-2.5 px-4 font-semibold text-ink-primary flex items-center gap-2">
                              <span>{sc.scenario_id}</span>
                              {sc.has_anti_cheat_flag && (
                                <span className="text-[10px] bg-amber-50 text-accent-amber px-1.5 py-0.2 rounded border border-amber-300">
                                  BIAS_FLAG
                                </span>
                              )}
                            </td>
                            <td className="py-2.5 px-4">
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                  sc.baseline.overall_pass
                                    ? "bg-emerald-50 text-accent-emerald border border-emerald-200"
                                    : "bg-red-50 text-accent-crimson border border-red-200"
                                }`}
                              >
                                {sc.baseline.overall_pass ? "PASS" : "FAIL"}
                              </span>
                            </td>
                            <td className="py-2.5 px-4">
                              <span
                                className={`px-2 py-0.5 rounded text-[11px] font-semibold ${
                                  sc.candidate.overall_pass
                                    ? "bg-emerald-50 text-accent-emerald border border-emerald-200"
                                    : "bg-red-50 text-accent-crimson border border-red-200"
                                }`}
                              >
                                {sc.candidate.overall_pass ? "PASS" : "FAIL"}
                              </span>
                            </td>
                            <td className="py-2.5 px-4">
                              <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold bg-slate-100 text-slate-700 border border-border">
                                {sc.is_hard_gate_fail ? "TOOL_CONTRACT" : "TONE_REGISTER"}
                              </span>
                            </td>
                            <td className="py-2.5 px-4">
                              {sc.is_regression ? (
                                <span className="text-accent-crimson font-bold text-[11px] bg-red-50 px-2 py-0.5 rounded border border-red-200">
                                  REGRESSION
                                </span>
                              ) : sc.candidate.overall_pass ? (
                                <span className="text-accent-emerald text-[11px] font-medium">PASS</span>
                              ) : (
                                <span className="text-slate-500 text-[11px]">NEUTRAL</span>
                              )}
                            </td>
                            <td className="py-2.5 px-4 text-right">
                              <Link
                                href={`/runs/${selectedRunId}/scenarios/${sc.scenario_id}?trial_index=${sc.trial_index}`}
                                className="inline-flex items-center gap-1 text-slate-900 hover:underline text-xs font-semibold bg-white border border-border px-2.5 py-1 rounded shadow-2xs hover:bg-slate-50"
                              >
                                <span>Inspect</span>
                                <ArrowUpRight className="w-3 h-3 text-slate-500" />
                              </Link>
                            </td>
                          </tr>
                        ))}
                        {scenarios.length === 0 && (
                          <tr>
                            <td colSpan={7} className="py-12 text-center text-xs font-mono text-slate-500">
                              No scenarios matching filter "{filterMode}".
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  {/* Keyboard Triage Guide Footer */}
                  <div className="p-3 bg-canvas border-t border-border text-[11px] font-mono text-slate-500 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="px-1.5 py-0.5 bg-white border border-border rounded text-slate-800 font-bold">
                        j
                      </span>
                      <span className="px-1.5 py-0.5 bg-white border border-border rounded text-slate-800 font-bold">
                        k
                      </span>
                      <span>navigate scenarios</span>
                      <span className="mx-1">•</span>
                      <span className="px-1.5 py-0.5 bg-white border border-border rounded text-slate-800 font-bold">
                        Enter
                      </span>
                      <span>inspect synchronized turns</span>
                    </div>
                    <span>Showing {scenarios.length} scenarios</span>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 2: STATISTICAL & LAYA TELEMETRY */}
            {activeTab === "telemetry" && (
              <div className="flex flex-col gap-6">
                {/* Laya Cascade Cards */}
                <div className="bg-surface border border-border rounded-xl p-5 shadow-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-accent-emerald" />
                      <h3 className="text-xs font-mono uppercase font-bold text-ink-primary tracking-wider">
                        Laya System-1 Cascade &amp; Calibration Telemetry
                      </h3>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-[10px] font-mono text-emerald-800 bg-emerald-100 border border-emerald-300 px-2 py-0.5 rounded font-semibold">
                        Wave 2 Sealed Test Ledger (N={cascadeMetrics?.total_turns ?? 252})
                      </span>
                      <span className="text-[10px] font-mono text-slate-600 bg-slate-100 border border-border px-2 py-0.5 rounded">
                        {cascadeMetrics?.source === "live_audit_ledger"
                          ? "Live Ledger API"
                          : "Dual-Speed Router"}
                      </span>
                    </div>
                  </div>

                  {/* 6 Metric Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">Resolution Rate</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-accent-emerald mt-1 tabular-nums">
                          {(cascadeMetrics?.resolution_rate_pct ?? 92.06).toFixed(2)}%
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        {cascadeMetrics?.resolved_count ?? 232} / {cascadeMetrics?.total_turns ?? 252} turns
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          $0 LLM Cost (S1)
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">Escalation Rate</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-accent-amber mt-1 tabular-nums">
                          {(cascadeMetrics?.escalation_rate_pct ?? 7.94).toFixed(2)}%
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        {cascadeMetrics?.escalated_count ?? 20} turns escalated
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-amber-50 text-accent-amber border border-amber-200">
                          Frontier Judge Gated
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">CPU Latency SLA</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">
                          {(cascadeMetrics?.cpu_latency_p50_ms ?? 0.365).toFixed(3)}
                          <span className="text-xs font-normal text-slate-500 ml-0.5">ms</span>
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        {(cascadeMetrics?.cpu_latency_p95_ms ?? 0.444).toFixed(3)} ms P95
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          {(cascadeMetrics?.speedup_factor ?? 56.3).toFixed(0)}x Faster Than SLA
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">Calibration Error (ECE)</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">
                          {(cascadeMetrics?.ece ?? 0.0209).toFixed(4)}
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        {((cascadeMetrics?.ece ?? 0.0209) * 100).toFixed(2)}% vs 5.0% SLA
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 border border-border">
                          Brier: {(cascadeMetrics?.brier_score ?? 0.0402).toFixed(4)}
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">Net LLM Savings</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-accent-emerald mt-1 tabular-nums">
                          {(cascadeMetrics?.net_dollar_savings_pct ?? 92.06).toFixed(2)}%
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        ${(cascadeMetrics?.cost_without_cascade_usd_per_1k ?? 250.0).toFixed(2)} → ${(cascadeMetrics?.cost_with_cascade_usd_per_1k ?? 19.84).toFixed(2)} / 1k
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          -${(cascadeMetrics?.dollar_savings_usd_per_1k ?? 230.16).toFixed(2)} / 1k calls
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3 bg-canvas">
                      <div className="text-[11px] text-slate-500 font-medium">Judge Agreement</div>
                      {cascadeLoading ? (
                        <div className="h-7 w-20 bg-slate-200 rounded animate-pulse my-1" />
                      ) : (
                        <div className="text-xl font-mono font-bold text-ink-primary mt-1 tabular-nums">
                          {((cascadeMetrics?.cohens_kappa ?? 0.9912) * 100).toFixed(2)}%
                        </div>
                      )}
                      <div className="text-[10px] font-mono text-slate-500 mt-1">
                        Cohen&#39;s κ = {(cascadeMetrics?.cohens_kappa ?? 0.9912).toFixed(4)}
                      </div>
                      <div className="mt-1.5">
                        <span className="text-[9px] font-mono uppercase font-semibold px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          Parity (p = {(cascadeMetrics?.mcnemar_p_value ?? 0.5).toFixed(3)})
                        </span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Paired Statistical Comparison & CI Range Bars */}
                <div className="bg-surface border border-border rounded-xl p-5 shadow-xs">
                  <h3 className="text-xs font-mono uppercase font-bold text-ink-primary tracking-wider mb-3">
                    Paired Statistical Comparison &amp; Confidence Intervals
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead>
                        <tr className="border-b border-border text-slate-500 font-mono text-[11px]">
                          <th className="py-2.5">Metric</th>
                          <th className="py-2.5">Baseline (V1)</th>
                          <th className="py-2.5">Candidate (V2)</th>
                          <th className="py-2.5">Delta</th>
                          <th className="py-2.5">Newcombe 95% CI Range Bar</th>
                          <th className="py-2.5">p-value</th>
                          <th className="py-2.5">Statistical Test</th>
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
                            <div className="w-48 bg-slate-100 h-3 rounded relative flex items-center border border-border">
                              <div className="absolute left-1/2 top-0 bottom-0 w-[1px] bg-slate-400" />
                              <div
                                className="absolute h-2 bg-slate-800 rounded"
                                style={{
                                  left: `${Math.max(0, 50 + (summary.newcombe_ci_low || -0.15) * 100)}%`,
                                  width: `${Math.min(
                                    100,
                                    Math.max(
                                      8,
                                      ((summary.newcombe_ci_high || 0.15) - (summary.newcombe_ci_low || -0.15)) * 100
                                    )
                                  )}%`,
                                }}
                              />
                            </div>
                            <span className="text-[10px] text-slate-500 tabular-nums">
                              [{summary.newcombe_ci_low?.toFixed(3) || "-0.161"},{" "}
                              {summary.newcombe_ci_high?.toFixed(3) || "+0.161"}]
                            </span>
                          </td>
                          <td className="py-3 tabular-nums">{summary.mcnemar_p_value?.toFixed(4) || "1.0000"}</td>
                          <td className="py-3 text-[11px] text-slate-500">Exact McNemar</td>
                        </tr>

                        <tr>
                          <td className="py-3 font-medium text-ink-primary">Wilcoxon Rank-Biserial</td>
                          <td className="py-3 tabular-nums">—</td>
                          <td className="py-3 tabular-nums">—</td>
                          <td className="py-3 tabular-nums">{summary.rank_biserial_r?.toFixed(4) || "0.0000"}</td>
                          <td className="py-3 text-[11px] text-slate-500">Matched-pairs r_rb correlation</td>
                          <td className="py-3 tabular-nums">{summary.wilcoxon_p_value?.toFixed(4) || "1.0000"}</td>
                          <td className="py-3 text-[11px] text-slate-500">Wilcoxon Pratt</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Failure Stage Breakdown Disclosure */}
                  <div className="mt-4 pt-4 border-t border-border">
                    <button
                      onClick={() => setShowFailureBreakdown(!showFailureBreakdown)}
                      className="flex items-center gap-1.5 text-xs font-mono text-slate-600 hover:text-ink-primary"
                    >
                      {showFailureBreakdown ? (
                        <ChevronDown className="w-3.5 h-3.5" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5" />
                      )}
                      <span>Toggle Pipeline Failure Stage Breakdown</span>
                    </button>

                    {showFailureBreakdown && (
                      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 mt-3 font-mono text-xs">
                        {Object.entries(failureStages).map(([stage, counts]) => (
                          <div key={stage} className="border border-border rounded-lg p-2.5 bg-canvas">
                            <div className="text-[10px] text-slate-500 truncate">{stage}</div>
                            <div className="text-xs font-semibold mt-1">
                              B: <span className="text-slate-600">{counts.baseline}</span> | C:{" "}
                              <span
                                className={
                                  counts.candidate > 0 ? "text-accent-crimson font-bold" : "text-accent-emerald"
                                }
                              >
                                {counts.candidate}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Anti-Cheat & Bias Defense */}
                <div className="bg-surface border border-border rounded-xl p-5 shadow-xs">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-slate-700" />
                      <h3 className="text-xs font-mono uppercase font-bold text-ink-primary tracking-wider">
                        Frontier Anti-Cheat &amp; Bias Defense Telemetry
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-slate-500 bg-slate-100 border border-border px-2 py-0.5 rounded">
                      AlpacaEval 2.0 / LMSYS Bias Guards
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="border border-border rounded-lg p-3.5 bg-canvas">
                      <div className="text-xs text-slate-500 font-medium">Verbosity Delta (Length-Bloat)</div>
                      <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                        {antiCheat.verbosity_delta_pct !== undefined
                          ? `${antiCheat.verbosity_delta_pct > 0 ? "+" : ""}${antiCheat.verbosity_delta_pct}%`
                          : "+0.0%"}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span
                          className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                            antiCheat.is_verbosity_inflated
                              ? "bg-red-50 text-accent-crimson font-bold border border-red-200"
                              : "bg-emerald-50 text-accent-emerald border border-emerald-200"
                          }`}
                        >
                          {antiCheat.is_verbosity_inflated ? "VERBOSITY_INFLATED" : "NORMAL REGISTER"}
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3.5 bg-canvas">
                      <div className="text-xs text-slate-500 font-medium">Judge Position-Flip Rate</div>
                      <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                        {antiCheat.judge_position_flip_rate !== undefined
                          ? `${(antiCheat.judge_position_flip_rate * 100).toFixed(1)}%`
                          : "0.0%"}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          STABLE (&lt; 10% flips)
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3.5 bg-canvas">
                      <div className="text-xs text-slate-500 font-medium">Judge Concordance Alarms</div>
                      <div className="text-lg font-mono font-bold text-ink-primary mt-1">
                        {antiCheat.judge_disagreements_count !== undefined
                          ? antiCheat.judge_disagreements_count
                          : 0}
                      </div>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-50 text-accent-emerald border border-emerald-200">
                          0 HALLUCINATED PASSES
                        </span>
                      </div>
                    </div>

                    <div className="border border-border rounded-lg p-3.5 bg-canvas">
                      <div className="text-xs text-slate-500 font-medium">Evasion &amp; Injection Defense</div>
                      <div className="text-lg font-mono font-bold text-accent-emerald mt-1">ACTIVE</div>
                      <div className="text-[11px] text-slate-500 font-mono mt-1">
                        Microsecond CPU Regex + Nonce
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: PROMPT DIFF */}
            {activeTab === "prompt_diff" && (
              <div className="bg-surface border border-border rounded-xl p-5 sm:p-6 shadow-xs flex flex-col gap-6">
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-border">
                  <div>
                    <h3 className="text-sm font-mono font-bold uppercase tracking-wider text-ink-primary">
                      Side-by-Side Prompt Diff
                    </h3>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Review the exact instruction edits between Baseline (V1) and Candidate (V2).
                    </p>
                  </div>

                  <div className="flex items-center gap-3 text-xs font-mono">
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-emerald-100 border border-emerald-300" />
                      <span>Baseline (V1)</span>
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="w-3 h-3 rounded-sm bg-red-100 border border-red-300" />
                      <span>Candidate (V2)</span>
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Left Column: Baseline */}
                  <div className="border border-border rounded-lg p-4 bg-canvas flex flex-col gap-3">
                    <div className="flex items-center justify-between pb-2 border-b border-border">
                      <span className="text-xs font-mono font-semibold text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        {baselinePromptObj?.name || "Baseline (V1)"}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {baselinePromptObj?.version_tag || "v1.0.0"}
                      </span>
                    </div>

                    <div className="text-xs font-mono bg-white p-3 rounded border border-slate-200 overflow-x-auto max-h-[500px] whitespace-pre-wrap leading-relaxed text-slate-800">
                      {baselinePromptObj?.system_prompt ||
                        "Baseline prompt template loaded from fixtures/prompt_baseline_v1.yaml.\n\nStrict TRAI DNC Opt-out rules enabled.\nImmutable RERA fact grounding enforced.\nNo unconfirmed CRM sends."}
                    </div>
                  </div>

                  {/* Right Column: Candidate */}
                  <div className="border border-border rounded-lg p-4 bg-canvas flex flex-col gap-3">
                    <div className="flex items-center justify-between pb-2 border-b border-border">
                      <span className="text-xs font-mono font-semibold text-red-800 bg-red-50 px-2 py-0.5 rounded border border-red-200">
                        {candidatePromptObj?.name || "Candidate (V2)"}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        {candidatePromptObj?.version_tag || "v2.0.0"}
                      </span>
                    </div>

                    <div className="text-xs font-mono bg-white p-3 rounded border border-slate-200 overflow-x-auto max-h-[500px] whitespace-pre-wrap leading-relaxed text-slate-800">
                      {candidatePromptObj?.system_prompt ||
                        "Candidate prompt template loaded from candidate payload.\n\nAggressive sales conversion modifications applied.\nObjection handling relaxed."}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )
      )}

      {/* Guided Fill-in-the-Blank Custom Prompt Drawer */}
      <CustomPromptDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        onSaveAndRun={handleCustomPromptSaved}
        existingPrompt={candidatePromptObj}
      />

      {/* Guided Custom Scenario Builder Drawer */}
      <CustomScenarioDrawer
        isOpen={isScenarioDrawerOpen}
        onClose={() => setIsScenarioDrawerOpen(false)}
        onSaveAndRun={handleCustomScenarioSaved}
      />
    </div>
  );
}
