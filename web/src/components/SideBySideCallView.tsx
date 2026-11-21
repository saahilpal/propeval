"use client";

import React from "react";
import { MessageSquare, AlertCircle, CheckCircle, Bot, User } from "lucide-react";

export interface TurnComparisonData {
  persona_id: string;
  persona_name: string;
  customer_message: string;
  prompt_a_reply: string;
  prompt_a_passed: boolean;
  prompt_a_failure_callout: string | null;
  prompt_a_judge_tier: string;
  prompt_b_reply: string;
  prompt_b_passed: boolean;
  prompt_b_failure_callout: string | null;
  prompt_b_judge_tier: string;
}

interface SideBySideCallViewProps {
  comparisons: TurnComparisonData[];
  activePersonaId: string;
  setActivePersonaId: (id: string) => void;
}

export function SideBySideCallView({
  comparisons,
  activePersonaId,
  setActivePersonaId,
}: SideBySideCallViewProps) {
  if (comparisons.length === 0) return null;

  const currentComparison =
    comparisons.find((c) => c.persona_id === activePersonaId) || comparisons[0];

  return (
    <div className="space-y-3">
      {/* Customer Switcher Pills */}
      <div>
        <div className="text-xs font-semibold text-ink-primary mb-1.5 flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-ink-secondary" />
          <span>Switch Customer Conversation:</span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
          {comparisons.map((c) => {
            const isActive = c.persona_id === currentComparison.persona_id;
            const hasFailure = !c.prompt_a_passed || !c.prompt_b_passed;

            return (
              <button
                key={c.persona_id}
                type="button"
                onClick={() => setActivePersonaId(c.persona_id)}
                className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-all flex items-center gap-2 whitespace-nowrap shrink-0 ${
                  isActive
                    ? "bg-ink-primary text-white border-ink-primary shadow-xs"
                    : "bg-surface hover:bg-slate-100 text-ink-secondary border-border"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full shrink-0 ${
                    hasFailure ? "bg-accent-crimson" : "bg-accent-emerald"
                  }`}
                />
                <span>{c.persona_name}</span>
                {hasFailure ? (
                  <span className={`text-[10px] font-mono px-1 py-0.2 rounded ${isActive ? "bg-red-900/60 text-red-200" : "bg-red-100 text-red-700"}`}>
                    Fail
                  </span>
                ) : (
                  <span className={`text-[10px] font-mono px-1 py-0.2 rounded ${isActive ? "bg-emerald-900/60 text-emerald-200" : "bg-emerald-100 text-emerald-700"}`}>
                    Pass
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Shared Customer Message Banner */}
      <div className="bg-slate-100/90 border border-slate-200 rounded-lg p-3 flex items-start gap-2.5">
        <div className="p-1.5 rounded-full bg-white border border-slate-200 text-slate-600 shrink-0 mt-0.5">
          <User className="w-4 h-4" />
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-xs font-semibold text-ink-primary">
              {currentComparison.persona_name}
            </span>
            <span className="text-[10px] font-mono text-slate-500 bg-white px-1.5 py-0.2 rounded border border-slate-200">
              Inbound Buyer Voice Turn
            </span>
          </div>
          <p className="text-xs text-ink-primary font-medium italic">
            &ldquo;{currentComparison.customer_message}&rdquo;
          </p>
        </div>
      </div>

      {/* Side-by-Side Agent Replies */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left Column: Prompt A Reply */}
        <div className="bg-surface border border-border rounded-lg p-4 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-border/80">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-accent-emerald" />
                <span className="text-xs font-semibold text-ink-primary">
                  Prompt A Response
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                  Current
                </span>
              </div>
              <span
                className={`text-[11px] font-mono px-2 py-0.5 rounded font-medium flex items-center gap-1 ${
                  currentComparison.prompt_a_passed
                    ? "bg-accent-emeraldBg text-accent-emerald border border-emerald-200"
                    : "bg-accent-crimsonBg text-accent-crimson border border-red-200"
                }`}
              >
                {currentComparison.prompt_a_passed ? (
                  <>
                    <CheckCircle className="w-3 h-3" />
                    <span>PASS</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3 h-3" />
                    <span>FAIL</span>
                  </>
                )}
              </span>
            </div>

            {/* Bubble with red border if failed */}
            <div
              className={`p-3 rounded-md text-xs leading-relaxed ${
                currentComparison.prompt_a_passed
                  ? "bg-slate-50 text-ink-primary border border-slate-200"
                  : "bg-accent-crimsonBg/30 text-ink-primary border border-red-200 border-l-4 border-l-accent-crimson"
              }`}
            >
              {currentComparison.prompt_a_reply}
            </div>

            {/* Inline Failure Callout if failed */}
            {!currentComparison.prompt_a_passed && currentComparison.prompt_a_failure_callout && (
              <div className="mt-2.5 p-2 rounded bg-red-50 border border-red-200 text-xs text-accent-crimson flex items-start gap-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span className="font-medium">
                  {currentComparison.prompt_a_failure_callout}
                </span>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Evaluated by:</span>
            <span className="text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              {currentComparison.prompt_a_judge_tier}
            </span>
          </div>
        </div>

        {/* Right Column: Prompt B Reply */}
        <div className="bg-surface border border-border rounded-lg p-4 flex flex-col justify-between shadow-xs">
          <div>
            <div className="flex items-center justify-between pb-2 mb-2.5 border-b border-border/80">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-amber-600" />
                <span className="text-xs font-semibold text-ink-primary">
                  Prompt B Response
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-amber-50 text-amber-700 border border-amber-200">
                  New Candidate
                </span>
              </div>
              <span
                className={`text-[11px] font-mono px-2 py-0.5 rounded font-medium flex items-center gap-1 ${
                  currentComparison.prompt_b_passed
                    ? "bg-accent-emeraldBg text-accent-emerald border border-emerald-200"
                    : "bg-accent-crimsonBg text-accent-crimson border border-red-200"
                }`}
              >
                {currentComparison.prompt_b_passed ? (
                  <>
                    <CheckCircle className="w-3 h-3" />
                    <span>PASS</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="w-3 h-3" />
                    <span>FAIL</span>
                  </>
                )}
              </span>
            </div>

            {/* Bubble with red border if failed */}
            <div
              className={`p-3 rounded-md text-xs leading-relaxed ${
                currentComparison.prompt_b_passed
                  ? "bg-slate-50 text-ink-primary border border-slate-200"
                  : "bg-accent-crimsonBg/30 text-ink-primary border border-red-200 border-l-4 border-l-accent-crimson"
              }`}
            >
              {currentComparison.prompt_b_reply}
            </div>

            {/* Inline Failure Callout if failed */}
            {!currentComparison.prompt_b_passed && currentComparison.prompt_b_failure_callout && (
              <div className="mt-2.5 p-2 rounded bg-red-50 border border-red-200 text-xs text-accent-crimson flex items-start gap-2">
                <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                <span className="font-medium">
                  {currentComparison.prompt_b_failure_callout}
                </span>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-mono text-slate-400">
            <span>Evaluated by:</span>
            <span className="text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200">
              {currentComparison.prompt_b_judge_tier}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
