"use client";

import React from "react";
import Link from "next/link";
import { Zap, GitBranch } from "lucide-react";

export function Navbar() {
  return (
    <header className="h-13 border-b border-border bg-surface px-4 sm:px-8 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <span className="w-2.5 h-2.5 rounded-sm bg-ink-primary group-hover:scale-110 transition-transform" />
          <span className="font-mono font-bold text-sm tracking-wider uppercase text-ink-primary">
            PropEval
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-border">
            v1.0.0
          </span>
        </Link>
        <span className="text-slate-300 hidden sm:inline">/</span>
        <span className="text-xs font-medium text-ink-secondary hidden sm:inline">
          Indian Customer Prompt Simulator
        </span>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-[11px] font-mono text-ink-secondary bg-slate-50 border border-border px-2.5 py-1 rounded-md">
          <Zap className="w-3 h-3 text-accent-emerald" />
          <span>Laya 0.4ms Local CPU + Layer 1/2 Gating</span>
        </div>
        <a
          href="https://github.com/saahilpal/propeval"
          target="_blank"
          rel="noreferrer"
          className="text-slate-500 hover:text-ink-primary p-1.5 rounded-md hover:bg-slate-100 transition-colors"
          title="GitHub Repository"
        >
          <GitBranch className="w-4 h-4" />
        </a>
      </div>
    </header>
  );
}
