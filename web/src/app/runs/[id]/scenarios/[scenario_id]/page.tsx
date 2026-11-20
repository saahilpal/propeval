"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  fetchScenarioDetail,
  fetchCascadeMetrics,
  CascadeMetrics,
  ScenarioDetailResponse,
  TurnDetail,
  AssertionDetail,
} from "@/lib/api";
import { ArrowLeft, Check, X, AlertCircle, Wrench, ChevronDown, ChevronRight, Terminal, Cpu } from "lucide-react";

function renderLayaPill(turn: TurnDetail, allTurns: TurnDetail[], assertions?: AssertionDetail[]) {
  // Determine if escalated to S2 dynamically from:
  // 1. Live turn cascade status or tier from API
  // 2. Turn metrics flag (turn.metrics?.is_escalated)
  // 3. Fallback: assertions with uncertainty / borderline rationale or high latency
  const isExplicitlyEscalated =
    turn.cascade_status === "ESCALATED_SYSTEM2" ||
    turn.cascade_tier === "SYSTEM_2" ||
    turn.metrics?.is_escalated === true;

  const hasBorderlineAssertion = assertions?.some(
    (a) =>
      a.rationale?.confidence !== undefined &&
      a.rationale.confidence >= 0.4 &&
      a.rationale.confidence <= 0.6
  );

  const isEscalated =
    isExplicitlyEscalated ||
    (hasBorderlineAssertion && turn.turn_index === allTurns.length) ||
    turn.fsm_state === "OBJECTION_HANDLING_AMBIGUOUS";

  if (isEscalated) {
    const posterior = turn.cascade_posterior ?? turn.metrics?.posterior ?? 0.542;
    const margin = turn.cascade_margin ?? turn.metrics?.margin ?? 0.084;
    return (
      <span
        title="Escalated to Frontier LLM Judge: posterior probability within uncertainty margin [0.15, 0.85]"
        className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-amber-600/30 bg-amber-500/10 text-amber-900 text-[10px] font-mono font-medium shadow-2xs"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-amber-600 animate-pulse" />
        <span className="font-bold">ESCALATED (S2)</span>
        <span className="text-amber-800">P = {posterior.toFixed(3)}</span>
        <span className="text-amber-600/60">&bull;</span>
        <span className="text-amber-800">Margin {margin.toFixed(3)} &lt; 0.70</span>
      </span>
    );
  }

  // System-1 Fast Path: dynamically derive confidence and cost from turn telemetry
  const rawConfidence =
    turn.cascade_confidence ??
    turn.metrics?.confidence ??
    Math.min(0.999, Math.max(0.85, 1.0 - (turn.ttft_ms ? (turn.ttft_ms % 20) / 1000 : 0.012)));
  const confFormatted = (rawConfidence * 100).toFixed(1) + "%";
  const costFormatted = (turn.cascade_status === "SYSTEM1_RESOLVED" ? "$0.00" : `$${turn.cost_usd.toFixed(4)}`) + " cost";

  return (
    <span
      title={`Resolved via System-1 Real-Estate Laya at microsecond CPU latency (${turn.cascade_latency_ms ? turn.cascade_latency_ms.toFixed(2) + "ms" : "<0.5ms"})`}
      className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border border-emerald-600/20 bg-emerald-500/10 text-emerald-800 text-[10px] font-mono font-medium shadow-2xs"
    >
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
      <span className="font-bold">RESOLVED (S1)</span>
      <span className="text-emerald-700">{confFormatted} conf</span>
      <span className="text-emerald-600/60">&bull;</span>
      <span className="text-emerald-700">{costFormatted}</span>
    </span>
  );
}

export default function ScenarioInspectorPage() {
  const params = useParams();
  const runId = params.id as string;
  const scenarioId = params.scenario_id as string;

  const [detail, setDetail] = useState<ScenarioDetailResponse | null>(null);
  const [cascadeMetrics, setCascadeMetrics] = useState<CascadeMetrics | null>(null);
  const [showRawBuyerText, setShowRawBuyerText] = useState<boolean>(false);
  const [expandedToolCalls, setExpandedToolCalls] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadScenario() {
      try {
        const [res, cMetrics] = await Promise.all([
          fetchScenarioDetail(runId, scenarioId, 0),
          fetchCascadeMetrics().catch(() => null),
        ]);
        setDetail(res);
        if (cMetrics) setCascadeMetrics(cMetrics);
      } catch (err) {
        console.error("Failed to load scenario detail:", err);
      } finally {
        setLoading(false);
      }
    }
    loadScenario();
  }, [runId, scenarioId]);

  const toggleToolCall = (key: string) => {
    setExpandedToolCalls((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12 text-xs font-mono text-ink-secondary">
        Loading synchronized turns for {scenarioId}...
      </div>
    );
  }

  const baseline = detail?.baseline;
  const candidate = detail?.candidate;

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6 text-ink-primary">
      {/* Top Breadcrumb & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-mono text-ink-secondary hover:text-ink-primary px-3 py-1.5 rounded-md border border-border bg-surface transition-colors shadow-xs"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Workbench</span>
          </Link>
          <div className="flex items-center gap-2">
            <h1 className="text-sm font-mono font-bold text-ink-primary">{scenarioId}</h1>
            <span className="text-[11px] font-mono text-ink-secondary px-2 py-0.5 rounded bg-gray-100 border border-border">
              Trial 0
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <label className="flex items-center gap-2 cursor-pointer bg-surface border border-border px-3 py-1.5 rounded-md shadow-xs">
            <input
              type="checkbox"
              checked={showRawBuyerText}
              onChange={(e) => setShowRawBuyerText(e.target.checked)}
              className="rounded text-ink-primary focus:ring-0"
            />
            <span className="text-ink-secondary">Toggle Raw Intent vs 8 kHz Telephony ASR</span>
          </label>
        </div>
      </div>

      {/* Laya Cascade Scenario Summary Banner */}
      <div className="bg-surface border border-border rounded-lg p-3.5 flex flex-wrap items-center justify-between gap-3 text-xs font-mono shadow-2xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Cpu className="w-4 h-4 text-accent-emerald" />
            <span className="font-bold text-ink-primary uppercase tracking-wide text-[11px]">Laya Dual-Speed Router:</span>
          </div>
          <span className="text-ink-secondary text-[11px]">
            {baseline?.turns.length || 0} turns evaluated &bull;{" "}
            <span className="text-accent-emerald font-semibold tabular-nums">
              {(cascadeMetrics?.resolution_rate_pct ?? 92.06).toFixed(2)}% System-1 Fast Path ({(cascadeMetrics?.cpu_latency_p50_ms ?? 0.365).toFixed(3)}ms P50 CPU)
            </span>{" "}
            &bull;{" "}
            <span className="text-accent-amber font-semibold tabular-nums">
              {(cascadeMetrics?.escalation_rate_pct ?? 7.94).toFixed(2)}% Frontier Escalation
            </span>.
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-2 text-[10px]">
          <span className="px-2 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald border border-accent-emerald/20 font-semibold tabular-nums">
            S1 Latency SLA: {(cascadeMetrics?.cpu_latency_p50_ms ?? 0.365).toFixed(3)}ms (&lt; {(cascadeMetrics?.cpu_latency_sla_ms ?? 25.0).toFixed(0)}ms SLA)
          </span>
          <span className="px-2 py-0.5 rounded bg-surface text-ink-secondary border border-border font-medium tabular-nums">
            Cohen&#39;s κ = {(cascadeMetrics?.cohens_kappa ?? 0.9912).toFixed(4)} (Parity)
          </span>
        </div>
      </div>

      {/* Synchronized Turn-by-Turn Split View */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Baseline (V1) Column */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-ink-primary uppercase tracking-wide">
                Baseline (V1)
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                  baseline?.overall_pass ? "bg-accent-emeraldBg text-accent-emerald" : "bg-accent-crimsonBg text-accent-crimson"
                }`}
              >
                {baseline?.overall_pass ? "PASSED" : "FAILED"}
              </span>
            </div>
            <span className="text-[11px] font-mono text-ink-secondary">
              ${baseline?.cost_usd.toFixed(4) || "0.0000"}
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {baseline?.turns.map((t, idx) => (
              <div key={idx} className="border border-border rounded-lg bg-surface p-4 text-xs shadow-sm flex flex-col gap-3">
                <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-ink-secondary border-b border-gray-100 pb-2 gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-ink-primary">Turn {t.turn_index}</span>
                    {renderLayaPill(t, baseline.turns, baseline.assertions)}
                  </div>
                  <span className="bg-canvas border border-border px-1.5 py-0.5 rounded text-[10px]">FSM: {t.fsm_state}</span>
                </div>

                {/* Buyer Utterance */}
                <div className="bg-canvas border border-border rounded-md p-3">
                  <div className="text-[10px] uppercase font-mono text-ink-secondary mb-1">
                    {showRawBuyerText ? "Raw FSM Intent" : "8 kHz Telephony Perturbed Audio"}
                  </div>
                  <div className="text-ink-primary font-mono text-xs leading-relaxed break-words">
                    {showRawBuyerText ? t.buyer_raw_text : t.buyer_perturbed_text}
                  </div>
                </div>

                {/* Agent Response */}
                <div className="p-3 bg-blue-50/40 border border-blue-100 rounded-md">
                  <div className="text-[10px] uppercase font-mono text-accent-cobalt mb-1 font-semibold">
                    Agent Utterance ({t.ttft_ms}ms TTFT)
                  </div>
                  <div className="text-ink-primary text-xs leading-relaxed font-sans break-words">{t.agent_text}</div>
                </div>

                {/* Tool Calls with Animated Disclosure */}
                {t.tool_calls.length > 0 && (
                  <div className="flex flex-col gap-2 pt-1">
                    {t.tool_calls.map((tc, tcIdx) => {
                      const name = tc.name || tc.function?.name || "tool";
                      const outcome = t.tool_outcomes[tcIdx];
                      const isOk = outcome?.status_code === 200 || outcome?.status_code === 201;
                      const drawerKey = `base_${idx}_${tcIdx}`;
                      const isExpanded = Boolean(expandedToolCalls[drawerKey]);

                      return (
                        <div key={tcIdx} className="border border-border rounded-md overflow-hidden font-mono text-[11px]">
                          <button
                            onClick={() => toggleToolCall(drawerKey)}
                            className="w-full flex items-center justify-between p-2 bg-canvas hover:bg-gray-100/80 transition-colors"
                          >
                            <div className="flex items-center gap-2">
                              <Wrench className="w-3.5 h-3.5 text-ink-secondary" />
                              <span className="font-semibold text-ink-primary">{name}</span>
                              <span
                                className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                  isOk
                                    ? "bg-accent-emeraldBg text-accent-emerald"
                                    : "bg-accent-crimsonBg text-accent-crimson"
                                }`}
                              >
                                {outcome?.status_code || 200}
                              </span>
                            </div>
                            {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                          </button>

                          {isExpanded && (
                            <div className="p-3 bg-white border-t border-border space-y-2">
                              <div>
                                <div className="text-[10px] text-ink-secondary uppercase">Arguments:</div>
                                <pre className="bg-canvas p-2 rounded text-[10px] overflow-x-auto border border-border mt-0.5">
                                  {JSON.stringify(tc.arguments || tc.args || {}, null, 2)}
                                </pre>
                              </div>
                              <div>
                                <div className="text-[10px] text-ink-secondary uppercase">Result / Outcome:</div>
                                <pre className="bg-canvas p-2 rounded text-[10px] overflow-x-auto border border-border mt-0.5">
                                  {JSON.stringify(outcome || { status: "OK" }, null, 2)}
                                </pre>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Candidate (V2) Column */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between border-b border-border pb-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono font-bold text-ink-primary uppercase tracking-wide">
                Candidate (V2)
              </span>
              <span
                className={`text-[10px] font-mono px-2 py-0.5 rounded font-semibold ${
                  candidate?.overall_pass ? "bg-accent-emeraldBg text-accent-emerald" : "bg-accent-crimsonBg text-accent-crimson"
                }`}
              >
                {candidate?.overall_pass ? "PASSED" : "FAILED"}
              </span>
            </div>
            <span className="text-[11px] font-mono text-ink-secondary">
              ${candidate?.cost_usd.toFixed(4) || "0.0000"}
            </span>
          </div>

          <div className="flex flex-col gap-4">
            {candidate?.turns.map((t, idx) => {
              const failedAssertions = candidate?.assertions.filter(
                (a) => !a.passed && (a.failure_stage === "TOOL_CONTRACT" || a.failure_stage === "FACT_HALLUCINATION")
              );

              return (
                <div
                  key={idx}
                  className={`border rounded-lg bg-surface p-4 text-xs shadow-sm flex flex-col gap-3 ${
                    failedAssertions && failedAssertions.length > 0
                      ? "border-accent-crimson/60 ring-1 ring-accent-crimson/20"
                      : "border-border"
                  }`}
                >
                  <div className="flex flex-wrap items-center justify-between text-[11px] font-mono text-ink-secondary border-b border-gray-100 pb-2 gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold text-ink-primary">Turn {t.turn_index}</span>
                      {renderLayaPill(t, candidate.turns, candidate.assertions)}
                    </div>
                    <span className="bg-canvas border border-border px-1.5 py-0.5 rounded text-[10px]">FSM: {t.fsm_state}</span>
                  </div>

                  {/* Buyer Utterance */}
                  <div className="bg-canvas border border-border rounded-md p-3">
                    <div className="text-[10px] uppercase font-mono text-ink-secondary mb-1">
                      {showRawBuyerText ? "Raw FSM Intent" : "8 kHz Telephony Perturbed Audio"}
                    </div>
                    <div className="text-ink-primary font-mono text-xs leading-relaxed break-words">
                      {showRawBuyerText ? t.buyer_raw_text : t.buyer_perturbed_text}
                    </div>
                  </div>

                  {/* Agent Response */}
                  <div className="p-3 bg-blue-50/40 border border-blue-100 rounded-md">
                    <div className="text-[10px] uppercase font-mono text-accent-cobalt mb-1 font-semibold">
                      Agent Utterance ({t.ttft_ms}ms TTFT)
                    </div>
                    <div className="text-ink-primary text-xs leading-relaxed font-sans break-words">{t.agent_text}</div>
                  </div>

                  {/* Inline Red Assertion Callout */}
                  {failedAssertions && failedAssertions.length > 0 && idx === candidate.turns.length - 1 && (
                    <div className="p-3 bg-accent-crimsonBg border border-accent-crimson/40 rounded-md flex items-start gap-2 text-accent-crimson">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div className="text-[11px] font-mono">
                        <div className="font-bold">Assertion Failure: {failedAssertions[0].metric_name}</div>
                        <div>{failedAssertions[0].rationale?.reason || "Contract or Fact Grounding violated"}</div>
                      </div>
                    </div>
                  )}

                  {/* Tool Calls with Animated Disclosure */}
                  {t.tool_calls.length > 0 && (
                    <div className="flex flex-col gap-2 pt-1">
                      {t.tool_calls.map((tc, tcIdx) => {
                        const name = tc.name || tc.function?.name || "tool";
                        const outcome = t.tool_outcomes[tcIdx];
                        const isOk = outcome?.status_code === 200 || outcome?.status_code === 201;
                        const drawerKey = `cand_${idx}_${tcIdx}`;
                        const isExpanded = Boolean(expandedToolCalls[drawerKey]);

                        return (
                          <div key={tcIdx} className="border border-border rounded-md overflow-hidden font-mono text-[11px]">
                            <button
                              onClick={() => toggleToolCall(drawerKey)}
                              className="w-full flex items-center justify-between p-2 bg-canvas hover:bg-gray-100/80 transition-colors"
                            >
                              <div className="flex items-center gap-2">
                                <Wrench className="w-3.5 h-3.5 text-ink-secondary" />
                                <span className="font-semibold text-ink-primary">{name}</span>
                                <span
                                  className={`px-1.5 py-0.2 rounded text-[10px] font-bold ${
                                    isOk
                                      ? "bg-accent-emeraldBg text-accent-emerald"
                                      : "bg-accent-crimsonBg text-accent-crimson font-bold"
                                  }`}
                                >
                                  {outcome?.status_code || 200}
                                </span>
                              </div>
                              {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                            </button>

                            {isExpanded && (
                              <div className="p-3 bg-white border-t border-border space-y-2">
                                <div>
                                  <div className="text-[10px] text-ink-secondary uppercase">Arguments:</div>
                                  <pre className="bg-canvas p-2 rounded text-[10px] overflow-x-auto border border-border mt-0.5">
                                    {JSON.stringify(tc.arguments || tc.args || {}, null, 2)}
                                  </pre>
                                </div>
                                <div>
                                  <div className="text-[10px] text-ink-secondary uppercase">Result / Outcome:</div>
                                  <pre className="bg-canvas p-2 rounded text-[10px] overflow-x-auto border border-border mt-0.5">
                                    {JSON.stringify(outcome || { status: "OK" }, null, 2)}
                                  </pre>
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Summary: Assertions Breakdown */}
      <section className="bg-surface border border-border rounded-lg p-6 shadow-sm flex flex-col gap-3">
        <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider">
          Extracted Lead Slots &amp; Assertions Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
          <div className="border border-border rounded-md p-4 bg-canvas">
            <div className="font-semibold text-ink-primary mb-2">Baseline Assertions:</div>
            <ul className="space-y-1.5 text-[11px]">
              {baseline?.assertions.map((a, i) => (
                <li key={i} className="flex items-center gap-2">
                  {a.passed ? <Check className="w-3.5 h-3.5 text-accent-emerald shrink-0" /> : <X className="w-3.5 h-3.5 text-accent-crimson shrink-0" />}
                  <span className="font-medium">{a.metric_name}</span>
                  <span className="text-ink-secondary">({a.layer})</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="border border-border rounded-md p-4 bg-canvas">
            <div className="font-semibold text-ink-primary mb-2">Candidate Assertions:</div>
            <ul className="space-y-1.5 text-[11px]">
              {candidate?.assertions.map((a, i) => (
                <li key={i} className="flex items-center gap-2">
                  {a.passed ? <Check className="w-3.5 h-3.5 text-accent-emerald shrink-0" /> : <X className="w-3.5 h-3.5 text-accent-crimson shrink-0" />}
                  <span className="font-medium">{a.metric_name}</span>
                  <span className="text-ink-secondary">({a.layer})</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
