"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRight, Terminal } from "lucide-react";

export function Navbar() {
  const pathname = usePathname();
  const isWorkbench = pathname === "/workbench" || pathname.startsWith("/runs");

  return (
    <header className="h-14 border-b border-border bg-surface/95 backdrop-blur-sm px-4 sm:px-6 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-4 sm:gap-8">
        <Link href="/" className="flex items-center gap-2.5 group shrink-0">
          <span className="w-2.5 h-2.5 rounded-sm bg-ink-primary group-hover:scale-110 transition-transform" />
          <span className="font-mono font-bold text-sm tracking-wider uppercase text-ink-primary">
            PropEval
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200">
            v0.5.0
          </span>
        </Link>

        <nav className="hidden md:flex items-center gap-1 text-xs font-medium text-slate-600">
          <Link
            href="/"
            className={`py-1 px-2.5 rounded-md transition-colors ${
              pathname === "/"
                ? "text-ink-primary bg-slate-100 font-semibold"
                : "hover:text-ink-primary hover:bg-slate-100"
            }`}
          >
            Product
          </Link>
          <Link
            href="/workbench"
            className={`py-1 px-2.5 rounded-md transition-colors ${
              pathname === "/workbench"
                ? "text-ink-primary bg-slate-100 font-semibold"
                : "hover:text-ink-primary hover:bg-slate-100"
            }`}
          >
            Live Workbench
          </Link>
          <Link
            href="/registry"
            className={`py-1 px-2.5 rounded-md transition-colors ${
              pathname === "/registry"
                ? "text-ink-primary bg-slate-100 font-semibold"
                : "hover:text-ink-primary hover:bg-slate-100"
            }`}
          >
            Registry
          </Link>
          <a
            href="https://github.com/saahilpal/propeval/blob/main/benchmarks/BENCHMARK_REPORT.md"
            target="_blank"
            rel="noreferrer"
            className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
          >
            Benchmarks
          </a>
          <a
            href="https://github.com/saahilpal/propeval"
            target="_blank"
            rel="noreferrer"
            className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
          >
            GitHub
          </a>
          <a
            href="https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1"
            target="_blank"
            rel="noreferrer"
            className="py-1 px-2.5 rounded-md hover:text-ink-primary hover:bg-slate-100 transition-colors"
          >
            Hugging Face
          </a>
        </nav>
      </div>

      <div className="flex items-center gap-3">
        <div className="hidden lg:flex items-center gap-2 text-xs font-mono text-slate-500 bg-slate-50 px-2.5 py-1 rounded-md border border-slate-200">
          <span className="inline-block w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
          <span>Postgres 17</span>
          <span className="text-slate-300">|</span>
          <span className="text-accent-emerald font-medium">$0.00 Spend</span>
        </div>

        {/* Hide redundant Open Workbench CTA when already inside Workbench */}
        {!isWorkbench ? (
          <Link
            href="/workbench"
            className="text-xs font-medium bg-ink-primary text-white hover:bg-slate-800 px-3 py-1.5 rounded-md transition-colors shrink-0 flex items-center gap-1.5"
          >
            <span>Open Workbench</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        ) : (
          <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-slate-100 border border-slate-200 rounded text-[11px] font-mono text-slate-600">
            <Terminal className="w-3.5 h-3.5 text-slate-500" />
            <span>Interactive Session</span>
          </div>
        )}
      </div>
    </header>
  );
}
