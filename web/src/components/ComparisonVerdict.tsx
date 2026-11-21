"use client";

import React from "react";
import { Award, AlertTriangle, CheckCircle2, RotateCw } from "lucide-react";

interface ComparisonVerdictProps {
  scoreA: number;
  statusA: string;
  scoreB: number;
  statusB: string;
  winner: string;
  summaryBullets: string[];
  latencyMs: number;
  onReRun: () => void;
  isSimulating: boolean;
}

export function ComparisonVerdict({
  scoreA,
  statusA,
  scoreB,
  statusB,
  winner,
  summaryBullets,
  latencyMs,
  onReRun,
  isSimulating,
}: ComparisonVerdictProps) {
  const isSafeA = statusA.toLowerCase().includes("safe");
  const isSafeB = statusB.toLowerCase().includes("safe");

  return (
    <div className="bg-surface border border-border rounded-lg p-4 sm:p-5 shadow-xs space-y-3.5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-md bg-accent-emeraldBg border border-emerald-200 text-accent-emerald">
            <Award className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono uppercase tracking-wider text-slate-500 font-semibold">
                Simulation Verdict
              </span>
              <span className="text-[11px] font-mono text-slate-400">
                · {latencyMs} ms
              </span>
            </div>
            <h3 className="text-base sm:text-lg font-bold text-ink-primary">
              Winner:{" "}
              <span
                className={
                  winner === "Prompt A"
                    ? "text-accent-emerald"
                    : winner === "Prompt B"
                    ? "text-accent-emerald"
                    : "text-amber-600"
                }
              >
                {winner}
              </span>
            </h3>
          </div>
        </div>

        {/* Re-Run Button */}
        <button
          type="button"
          onClick={onReRun}
          disabled={isSimulating}
          className="self-start sm:self-auto px-4 py-2 bg-ink-primary hover:bg-slate-800 text-white text-xs font-semibold rounded-md shadow-xs flex items-center gap-2 transition-all disabled:opacity-50"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
          <span>{isSimulating ? "Running..." : "Re-Run"}</span>
          <span className="text-[10px] font-mono bg-white/20 px-1.5 py-0.2 rounded text-slate-200">
            ⌘↵
          </span>
        </button>
      </div>

      {/* Ratings Comparison Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {/* Score A */}
        <div
          className={`p-3 rounded-md border flex items-center justify-between ${
            isSafeA
              ? "bg-accent-emeraldBg/40 border-emerald-200"
              : "bg-accent-crimsonBg/40 border-red-200"
          }`}
        >
          <div>
            <div className="text-[11px] font-mono text-slate-500 font-medium">
              Prompt A (Current)
            </div>
            <div className="text-xs font-semibold text-ink-primary">
              {statusA}
            </div>
          </div>
          <div className="text-right">
            <span
              className={`text-xl sm:text-2xl font-bold font-mono tabular-nums ${
                isSafeA ? "text-accent-emerald" : "text-accent-crimson"
              }`}
            >
              {scoreA.toFixed(1)}
            </span>
            <span className="text-xs font-mono text-slate-400"> / 10</span>
          </div>
        </div>

        {/* Score B */}
        <div
          className={`p-3 rounded-md border flex items-center justify-between ${
            isSafeB
              ? "bg-accent-emeraldBg/40 border-emerald-200"
              : "bg-accent-crimsonBg/40 border-red-200"
          }`}
        >
          <div>
            <div className="text-[11px] font-mono text-slate-500 font-medium">
              Prompt B (New Candidate)
            </div>
            <div className="text-xs font-semibold text-ink-primary">
              {statusB}
            </div>
          </div>
          <div className="text-right">
            <span
              className={`text-xl sm:text-2xl font-bold font-mono tabular-nums ${
                isSafeB ? "text-accent-emerald" : "text-accent-crimson"
              }`}
            >
              {scoreB.toFixed(1)}
            </span>
            <span className="text-xs font-mono text-slate-400"> / 10</span>
          </div>
        </div>
      </div>

      {/* Plain-English Failure / Status Bullets */}
      <div className="bg-slate-50 border border-border/80 rounded-md p-3 space-y-1.5">
        <div className="text-[11px] font-mono uppercase tracking-wider text-slate-500 font-semibold mb-1">
          Root Cause & Rule Evaluation Summary:
        </div>
        {summaryBullets.map((bullet, idx) => {
          const isFail = bullet.toLowerCase().includes("fail") || bullet.toLowerCase().includes("violation");
          return (
            <div key={idx} className="flex items-start gap-2 text-xs text-ink-secondary leading-snug">
              {isFail ? (
                <AlertTriangle className="w-3.5 h-3.5 text-accent-crimson shrink-0 mt-0.5" />
              ) : (
                <CheckCircle2 className="w-3.5 h-3.5 text-accent-emerald shrink-0 mt-0.5" />
              )}
              <span>{bullet}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
