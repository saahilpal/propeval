"use client";

import React from "react";
import { FileCode, RotateCcw } from "lucide-react";

interface PromptEditorPairProps {
  promptA: string;
  setPromptA: (val: string) => void;
  promptB: string;
  setPromptB: (val: string) => void;
  onResetDefaults?: () => void;
}

export function PromptEditorPair({
  promptA,
  setPromptA,
  promptB,
  setPromptB,
  onResetDefaults,
}: PromptEditorPairProps) {
  const lineCountA = promptA.split("\n").length;
  const lineCountB = promptB.split("\n").length;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-ink-secondary" />
          <h2 className="text-sm font-semibold text-ink-primary">
            Side-by-Side Prompt Pair
          </h2>
          <span className="text-xs text-ink-muted hidden sm:inline">
            — Paste or edit Hinglish prompts directly
          </span>
        </div>
        {onResetDefaults && (
          <button
            type="button"
            onClick={onResetDefaults}
            className="text-[11px] font-medium text-slate-500 hover:text-ink-primary flex items-center gap-1 hover:underline"
          >
            <RotateCcw className="w-3 h-3" />
            <span>Reset Demo Prompts</span>
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Prompt A */}
        <div className="bg-surface border border-border rounded-lg p-3.5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/80">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-accent-emerald" />
              <span className="text-xs font-semibold text-ink-primary">
                Prompt A (Current)
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-accent-emeraldBg text-accent-emerald font-medium border border-emerald-200">
                Safe Reference
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {lineCountA} lines · {promptA.length} chars
            </span>
          </div>
          <textarea
            value={promptA}
            onChange={(e) => setPromptA(e.target.value)}
            placeholder="Paste Prompt A system prompt here..."
            className="w-full h-64 sm:h-72 p-2.5 font-mono text-[12px] leading-relaxed text-ink-primary bg-slate-50/70 border border-slate-200 rounded-md focus:outline-hidden focus:ring-1 focus:ring-ink-primary focus:bg-white resize-y"
            spellCheck={false}
          />
        </div>

        {/* Prompt B */}
        <div className="bg-surface border border-border rounded-lg p-3.5 flex flex-col shadow-xs">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-border/80">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-xs font-semibold text-ink-primary">
                Prompt B (New Candidate)
              </span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 font-medium border border-amber-200">
                Edit & Test
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400">
              {lineCountB} lines · {promptB.length} chars
            </span>
          </div>
          <textarea
            value={promptB}
            onChange={(e) => setPromptB(e.target.value)}
            placeholder="Paste Prompt B system prompt here..."
            className="w-full h-64 sm:h-72 p-2.5 font-mono text-[12px] leading-relaxed text-ink-primary bg-slate-50/70 border border-slate-200 rounded-md focus:outline-hidden focus:ring-1 focus:ring-ink-primary focus:bg-white resize-y"
            spellCheck={false}
          />
        </div>
      </div>
    </div>
  );
}
