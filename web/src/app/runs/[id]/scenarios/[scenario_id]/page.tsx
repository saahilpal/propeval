"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { fetchScenarioDetail, ScenarioDetailResponse, TurnDetail, AssertionDetail } from "@/lib/api";
import { ArrowLeft, Check, X, AlertCircle, Wrench, RefreshCw } from "lucide-react";

export default function ScenarioInspectorPage() {
  const params = useParams();
  const runId = params.id as string;
  const scenarioId = params.scenario_id as string;

  const [detail, setDetail] = useState<ScenarioDetailResponse | null>(null);
  const [showRawBuyerText, setShowRawBuyerText] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadScenario() {
      try {
        const res = await fetchScenarioDetail(runId, scenarioId, 0);
        setDetail(res);
      } catch (err) {
        console.error("Failed to load scenario detail:", err);
      } finally {
        setLoading(false);
      }
    }
    loadScenario();
  }, [runId, scenarioId]);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center p-12 text-xs font-mono text-ink-secondary">
        Loading synchronized turns for {scenarioId}...
      </div>
    );
  }

  const baseline = detail?.baseline;
  const candidate = detail?.candidate;
  const maxTurns = Math.max(baseline?.turns.length || 0, candidate?.turns.length || 0);

  return (
    <div className="flex-1 flex flex-col p-6 max-w-7xl mx-auto w-full gap-6">
      {/* Top Breadcrumb & Controls */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="flex items-center gap-1.5 text-xs font-mono text-ink-secondary hover:text-ink-primary px-2 py-1 rounded border border-border bg-surface"
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
          <label className="flex items-center gap-2 cursor-pointer bg-surface border border-border px-3 py-1.5 rounded shadow-sm">
            <input
              type="checkbox"
              checked={showRawBuyerText}
              onChange={(e) => setShowRawBuyerText(e.target.checked)}
              className="rounded text-ink-primary focus:ring-0"
            />
            <span className="text-ink-secondary">Toggle Raw FSM Intent vs 8 kHz ASR</span>
          </label>
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
                className={`text-[10px] font-mono px-2 py-0.5 rounded ${
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
              <div key={idx} className="border border-border rounded-md bg-surface p-4 text-xs shadow-sm flex flex-col gap-2.5">
                <div className="flex items-center justify-between text-[11px] font-mono text-ink-secondary border-b border-gray-100 pb-1.5">
                  <span className="font-semibold text-ink-primary">Turn {t.turn_index}</span>
                  <span>FSM: {t.fsm_state}</span>
                </div>

                {/* Buyer Utterance */}
                <div className="bg-canvas border border-border rounded p-2.5">
                  <div className="text-[10px] uppercase font-mono text-ink-secondary mb-1">
                    {showRawBuyerText ? "Raw FSM Intent" : "8 kHz Perturbed Hinglish"}
                  </div>
                  <div className="text-ink-primary font-mono text-xs">
                    {showRawBuyerText ? t.buyer_raw_text : t.buyer_perturbed_text}
                  </div>
                </div>

                {/* Agent Response */}
                <div className="p-2.5 bg-blue-50/40 border border-blue-100 rounded">
                  <div className="text-[10px] uppercase font-mono text-accent-cobalt mb-1 font-semibold">
                    Agent Utterance ({t.ttft_ms}ms TTFT)
                  </div>
                  <div className="text-ink-primary text-xs leading-relaxed font-sans">{t.agent_text}</div>
                </div>

                {/* Tool Calls */}
                {t.tool_calls.length > 0 && (
                  <div className="flex flex-wrap gap-2 pt-1">
                    {t.tool_calls.map((tc, tcIdx) => {
                      const name = tc.name || tc.function?.name || "tool";
                      const outcome = t.tool_outcomes[tcIdx];
                      const isOk = outcome?.status_code === 200 || outcome?.status_code === 201;
                      return (
                        <div
                          key={tcIdx}
                          className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono border ${
                            isOk
                              ? "bg-accent-emeraldBg border-accent-emerald/30 text-accent-emerald"
                              : "bg-accent-crimsonBg border-accent-crimson/30 text-accent-crimson"
                          }`}
                        >
                          <Wrench className="w-3 h-3" />
                          <span>{name}</span>
                          <span className="font-bold">{outcome?.status_code || 200}</span>
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
                className={`text-[10px] font-mono px-2 py-0.5 rounded ${
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
              // Check if any assertion failed on this turn
              const failedAssertions = candidate?.assertions.filter(
                (a) => !a.passed && (a.failure_stage === "TOOL_CONTRACT" || a.failure_stage === "FACT_HALLUCINATION")
              );

              return (
                <div
                  key={idx}
                  className={`border rounded-md bg-surface p-4 text-xs shadow-sm flex flex-col gap-2.5 ${
                    failedAssertions && failedAssertions.length > 0
                      ? "border-accent-crimson/60 ring-1 ring-accent-crimson/20"
                      : "border-border"
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-mono text-ink-secondary border-b border-gray-100 pb-1.5">
                    <span className="font-semibold text-ink-primary">Turn {t.turn_index}</span>
                    <span>FSM: {t.fsm_state}</span>
                  </div>

                  {/* Buyer Utterance */}
                  <div className="bg-canvas border border-border rounded p-2.5">
                    <div className="text-[10px] uppercase font-mono text-ink-secondary mb-1">
                      {showRawBuyerText ? "Raw FSM Intent" : "8 kHz Perturbed Hinglish"}
                    </div>
                    <div className="text-ink-primary font-mono text-xs">
                      {showRawBuyerText ? t.buyer_raw_text : t.buyer_perturbed_text}
                    </div>
                  </div>

                  {/* Agent Response */}
                  <div className="p-2.5 bg-blue-50/40 border border-blue-100 rounded">
                    <div className="text-[10px] uppercase font-mono text-accent-cobalt mb-1 font-semibold">
                      Agent Utterance ({t.ttft_ms}ms TTFT)
                    </div>
                    <div className="text-ink-primary text-xs leading-relaxed font-sans">{t.agent_text}</div>
                  </div>

                  {/* Inline Red Assertion Callout */}
                  {failedAssertions && failedAssertions.length > 0 && idx === candidate.turns.length - 1 && (
                    <div className="p-2.5 bg-accent-crimsonBg border border-accent-crimson/40 rounded flex items-start gap-2 text-accent-crimson">
                      <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                      <div className="text-[11px] font-mono">
                        <div className="font-bold">Assertion Failure: {failedAssertions[0].metric_name}</div>
                        <div>{failedAssertions[0].rationale?.reason || "Contract violated"}</div>
                      </div>
                    </div>
                  )}

                  {/* Tool Calls */}
                  {t.tool_calls.length > 0 && (
                    <div className="flex flex-wrap gap-2 pt-1">
                      {t.tool_calls.map((tc, tcIdx) => {
                        const name = tc.name || tc.function?.name || "tool";
                        const outcome = t.tool_outcomes[tcIdx];
                        const isOk = outcome?.status_code === 200 || outcome?.status_code === 201;
                        return (
                          <div
                            key={tcIdx}
                            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded text-[11px] font-mono border ${
                              isOk
                                ? "bg-accent-emeraldBg border-accent-emerald/30 text-accent-emerald"
                                : "bg-accent-crimsonBg border-accent-crimson/30 text-accent-crimson font-bold"
                            }`}
                          >
                            <Wrench className="w-3 h-3" />
                            <span>{name}</span>
                            <span>{outcome?.status_code || 200}</span>
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

      {/* Bottom Summary: Extracted Lead JSON Comparison */}
      <section className="bg-surface border border-border rounded-md p-6 shadow-sm flex flex-col gap-3">
        <h3 className="text-xs font-mono uppercase font-bold text-ink-secondary tracking-wider">
          Extracted Lead Slots &amp; Assertions Breakdown
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs font-mono">
          <div className="border border-border rounded p-4 bg-canvas">
            <div className="font-semibold text-ink-primary mb-2">Baseline Assertions:</div>
            <ul className="space-y-1 text-[11px]">
              {baseline?.assertions.map((a, i) => (
                <li key={i} className="flex items-center gap-2">
                  {a.passed ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <X className="w-3.5 h-3.5 text-accent-crimson" />}
                  <span>{a.metric_name}</span>
                  <span className="text-ink-secondary">({a.layer})</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="border border-border rounded p-4 bg-canvas">
            <div className="font-semibold text-ink-primary mb-2">Candidate Assertions:</div>
            <ul className="space-y-1 text-[11px]">
              {candidate?.assertions.map((a, i) => (
                <li key={i} className="flex items-center gap-2">
                  {a.passed ? <Check className="w-3.5 h-3.5 text-accent-emerald" /> : <X className="w-3.5 h-3.5 text-accent-crimson" />}
                  <span>{a.metric_name}</span>
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
