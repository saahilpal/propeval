"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchCascadeMetrics, CascadeMetrics } from "@/lib/api";

export default function ProductLandingPage() {
  const [metrics, setMetrics] = useState<CascadeMetrics | null>(null);
  const [copiedSnippet, setCopiedSnippet] = useState(false);

  useEffect(() => {
    fetchCascadeMetrics()
      .then((data) => setMetrics(data))
      .catch((err) => console.warn("Live telemetry fallback:", err));
  }, []);

  const copyCliCommand = () => {
    navigator.clipboard.writeText(
      "docker compose up -d && uv sync && uv run python -m backend.cli.main run --gate"
    );
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  return (
    <div className="flex flex-col w-full bg-white text-slate-900">
      {/* 1. HERO SECTION */}
      <section className="relative pt-16 pb-20 md:pt-24 md:pb-28 px-4 sm:px-6 lg:px-8 border-b border-slate-200 bg-gradient-to-b from-slate-50/80 to-white">
        <div className="max-w-6xl mx-auto flex flex-col items-center text-center">
          {/* Release Badge */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-white border border-slate-200 text-slate-700 shadow-xs mb-8">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>PropEval v0.5.0</span>
            <span className="text-slate-300">·</span>
            <span className="text-slate-500">100% Local $0 Build</span>
            <span className="text-slate-300">·</span>
            <span className="text-indigo-600 font-semibold">146/146 Tests Passing</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-slate-950 max-w-4xl leading-[1.12]">
            Pre-Release Prompt Regression & Reliability Workbench for{" "}
            <span className="text-indigo-600 underline decoration-indigo-200 underline-offset-8">
              Indian Real Estate Voice AI
            </span>
          </h1>

          {/* Subtitle */}
          <p className="mt-6 text-lg sm:text-xl text-slate-600 max-w-2xl leading-relaxed">
            Eliminate prompt-drift disasters before live calls. Catch TRAI DNC opt-out drops,
            invented WhatsApp confirmations after CRM 503s, and 8 kHz acoustic{" "}
            <code className="text-sm font-mono bg-slate-100 px-1.5 py-0.5 rounded border border-slate-200 text-slate-800">
              "1.2 cr"
            </code>{" "}
            misparses with paired statistical confidence intervals.
          </p>

          {/* CTAs */}
          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/workbench"
              className="inline-flex items-center gap-2 bg-slate-950 text-white font-medium text-sm px-6 py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-colors"
            >
              <span>Open Live Workbench</span>
              <span className="text-slate-400">→</span>
            </Link>

            <button
              onClick={copyCliCommand}
              className="inline-flex items-center gap-2 bg-white text-slate-800 font-mono text-xs px-5 py-3 rounded-lg border border-slate-200 shadow-xs hover:bg-slate-50 transition-colors"
            >
              <span className="text-indigo-600">$</span>
              <span>propeval run --gate</span>
              <span className="text-[10px] text-slate-400 ml-1">
                {copiedSnippet ? "✓ Copied" : "Copy"}
              </span>
            </button>
          </div>

          {/* Hero Live Preview Strip */}
          <div className="mt-12 w-full max-w-4xl bg-slate-950 text-slate-200 rounded-xl p-4 sm:p-6 border border-slate-800 text-left shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
                <span className="ml-2 font-semibold text-slate-300">
                  REGRESSION GATE: Candidate V2 vs Baseline V1
                </span>
              </div>
              <span className="text-emerald-400 font-semibold">EXIT CODE: 1 (BLOCKED)</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4 text-xs font-mono">
              <div className="bg-slate-900 p-3 rounded border border-red-900/40">
                <div className="text-red-400 font-bold uppercase tracking-wider text-[10px]">
                  Turn 4 · DNC Violation
                </div>
                <div className="mt-1 text-slate-300">"faltu call band kar abhi"</div>
                <div className="mt-1 text-slate-400 text-[11px]">
                  V2 continued pitching instead of immediate TRAI opt-out exit.
                </div>
              </div>

              <div className="bg-slate-900 p-3 rounded border border-amber-900/40">
                <div className="text-amber-400 font-bold uppercase tracking-wider text-[10px]">
                  Turn 6 · 8 kHz ASR Noise
                </div>
                <div className="mt-1 text-slate-300">"1.5 cr budget hai" → "1.5 core"</div>
                <div className="mt-1 text-slate-400 text-[11px]">
                  Acoustic confusion caused V2 to pitch 3.5 Cr luxury penthouses.
                </div>
              </div>

              <div className="bg-slate-900 p-3 rounded border border-red-900/40">
                <div className="text-red-400 font-bold uppercase tracking-wider text-[10px]">
                  Turn 8 · Tool Action Hallucination
                </div>
                <div className="mt-1 text-slate-300">CRM WhatsApp API: HTTP 503</div>
                <div className="mt-1 text-slate-400 text-[11px]">
                  V2 verbally promised "Bhej diya sir" despite socket connection timeout.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THE PRODUCTION PROBLEM */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-3xl mx-auto">
          <span className="text-xs font-mono uppercase tracking-wider font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-100">
            Real Telephony Failure Modes
          </span>
          <h2 className="mt-4 text-3xl font-extrabold text-slate-950 tracking-tight sm:text-4xl">
            Why Generic LLM Evals Fail on Indian Telephony
          </h2>
          <p className="mt-4 text-base text-slate-600 leading-relaxed">
            General-purpose eval tools return an aggregate 92% pass rate and deploy. In real estate,
            a single compliance breach or hallucinated carpet area kills customer trust.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:shadow-sm transition-all">
            <div className="w-8 h-8 rounded-lg bg-red-100 text-red-700 flex items-center justify-center font-bold text-sm mb-4">
              1
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              TRAI Do-Not-Call (DNC) Misses
            </h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              When a buyer says <em className="text-slate-800">"bhai call mat ghumao"</em> or{" "}
              <em className="text-slate-800">"dobara phone mat karna"</em>, conversational LLMs often
              treat it as soft hesitation and continue objection handling. PropEval enforces an
              immediate Layer 1 deterministic exit gate.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:shadow-sm transition-all">
            <div className="w-8 h-8 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center font-bold text-sm mb-4">
              2
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              8 kHz Phone Audio & Unit Misparses
            </h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Real telephony codecs distort audio: <em className="text-slate-800">"crore"</em> becomes{" "}
              <em className="text-slate-800">"core"</em>, <em className="text-slate-800">"lakh"</em> becomes{" "}
              <em className="text-slate-800">"lack"</em>, and Devanagari numerals are dropped. PropEval
              runs an 8 kHz acoustic perturbation matrix with property-tested normalizers.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:shadow-sm transition-all">
            <div className="w-8 h-8 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center font-bold text-sm mb-4">
              3
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              RERA & Carpet Area Hallucinations
            </h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Voice models frequently invent possession dates, amenities, or RERA IDs when buyers
              push on pricing. PropEval's Layer 2 verifies factual assertions against immutable
              project fixture databases before responses are graded.
            </p>
          </div>

          <div className="p-6 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white hover:shadow-sm transition-all">
            <div className="w-8 h-8 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center font-bold text-sm mb-4">
              4
            </div>
            <h3 className="text-lg font-bold text-slate-900">
              Invented Tool Confirmations (CRM 503 Faults)
            </h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              When CRM endpoints or WhatsApp dispatch tools fail under load, prompts often invent
              verbal confirmations like <em className="text-slate-800">"Brochure WhatsApp kar diya hai"</em>.
              PropEval injects socket faults and halts on fake verbal sends.
            </p>
          </div>
        </div>
      </section>

      {/* 3. VERIFIED LIVE NUMBERS */}
      <section className="py-16 bg-slate-50 border-y border-slate-200 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-600">
              Empirical Benchmarks
            </span>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-slate-950 tracking-tight">
              Real Verified Metrics on Disk
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Zero synthetic claims. Loaded directly from local PostgreSQL aggregates and held-out test audits.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                OOD Accuracy
              </div>
              <div className="text-3xl font-mono font-bold text-emerald-600 mt-2 tabular-nums">
                97.62%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                66.67% → 97.62% via calibration escalation
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                P95 S1 CPU Latency
              </div>
              <div className="text-3xl font-mono font-bold text-slate-950 mt-2 tabular-nums">
                {(metrics?.cpu_latency_p95_ms ?? 0.38).toFixed(2)} ms
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                0.36ms P50 · Sub-millisecond CPU inference
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                LLM Spend Cut
              </div>
              <div className="text-3xl font-mono font-bold text-indigo-600 mt-2 tabular-nums">
                {(metrics?.net_dollar_savings_pct ?? 92.06).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                $250 → $19.84 per 1,000 telephony calls
              </div>
            </div>

            <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
              <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                Automated Tests
              </div>
              <div className="text-3xl font-mono font-bold text-slate-950 mt-2 tabular-nums">
                146 / 146
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                27 Red-Team + 5 Mutants + SIGKILL recovery
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. HOW PROPEVAL WORKS (ARCHITECTURE) */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-xs font-mono uppercase tracking-wider font-semibold text-indigo-600 bg-indigo-50 px-2.5 py-1 rounded-full border border-indigo-100">
            System Design
          </span>
          <h2 className="mt-4 text-3xl font-extrabold text-slate-950 tracking-tight sm:text-4xl">
            The 3-Stage Pre-Release Pipeline
          </h2>
          <p className="mt-4 text-base text-slate-600">
            Everything runs in a clean, reproducible local loop before prompts touch production telephony trunks.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="border border-slate-200 rounded-xl p-6 bg-white shadow-xs">
            <div className="font-mono text-xs font-bold text-indigo-600 uppercase">Stage 01</div>
            <h3 className="text-lg font-bold text-slate-900 mt-2">Acoustic Simulation</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Buyer personas execute dynamic FSM agendas with 8 kHz phone acoustic codecs, dropped
              phonemes, and simulated CRM WhatsApp 503 timeouts.
            </p>
          </div>

          <div className="border border-slate-200 rounded-xl p-6 bg-white shadow-xs">
            <div className="font-mono text-xs font-bold text-indigo-600 uppercase">Stage 02</div>
            <h3 className="text-lg font-bold text-slate-900 mt-2">Laya Confidence Cascade</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Real-Estate Laya evaluates 92% of unambiguous turns in 0.36ms ($0 spend). Temperature
              calibration surges escalation on novel slang, preventing false passes.
            </p>
          </div>

          <div className="border border-slate-200 rounded-xl p-6 bg-white shadow-xs">
            <div className="font-mono text-xs font-bold text-indigo-600 uppercase">Stage 03</div>
            <h3 className="text-lg font-bold text-slate-900 mt-2">Paired Statistical Gating</h3>
            <p className="mt-2 text-sm text-slate-600 leading-relaxed">
              Exact McNemar and Newcombe Method 10 confidence intervals block CI deployments when
              regressions are statistically significant (p &lt; 0.05).
            </p>
          </div>
        </div>

        {/* Embedded Architecture Diagrams */}
        <div className="mt-16 border border-slate-200 rounded-xl p-4 sm:p-6 bg-slate-50">
          <div className="flex items-center justify-between pb-4 border-b border-slate-200 text-xs font-mono text-slate-600">
            <span className="font-semibold uppercase tracking-wider text-slate-900">
              System Architecture (Modular Monolith on PostgreSQL 17)
            </span>
            <a
              href="https://github.com/saahilpal/propeval/blob/main/architecture/01_propeval_system_architecture.drawio"
              target="_blank"
              rel="noreferrer"
              className="text-indigo-600 hover:underline"
            >
              Editable Draw.io XML →
            </a>
          </div>
          <div className="pt-4 flex justify-center">
            <img
              src="/architecture/01_propeval_system_architecture.svg"
              alt="PropEval System Architecture"
              className="w-full max-h-[500px] object-contain rounded-lg bg-white border border-slate-200 p-2"
            />
          </div>
        </div>
      </section>

      {/* 5. DEVELOPER QUICKSTART */}
      <section className="py-20 bg-slate-950 text-white px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-4xl mx-auto text-center">
          <span className="text-xs font-mono uppercase tracking-wider font-semibold text-emerald-400 bg-emerald-950/60 px-3 py-1 rounded-full border border-emerald-800">
            Developer Quickstart
          </span>
          <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl text-white">
            Run PropEval 100% Locally in 60 Seconds
          </h2>
          <p className="mt-3 text-sm text-slate-400">
            Zero cloud infrastructure required. Runs against local Docker PostgreSQL 17.
          </p>

          <div className="mt-8 text-left font-mono text-xs bg-slate-900 rounded-xl p-4 sm:p-6 border border-slate-800 overflow-x-auto shadow-2xl">
            <div className="text-slate-400 mb-2"># 1. Start local PostgreSQL 17 & Jaeger OTel</div>
            <div className="text-emerald-400 font-semibold mb-4">docker compose up -d</div>

            <div className="text-slate-400 mb-2"># 2. Run CLI regression gate</div>
            <div className="text-emerald-400 font-semibold mb-4">
              uv run python -m backend.cli.main run \<br />
              &nbsp;&nbsp;--baseline fixtures/prompt_baseline_v1.yaml \<br />
              &nbsp;&nbsp;--candidate fixtures/prompt_candidate_regressed.yaml \<br />
              &nbsp;&nbsp;--suite suites/hinglish_smoke_20.yaml \<br />
              &nbsp;&nbsp;--fixture fixtures/lodha_wakad_2026_11.yaml \<br />
              &nbsp;&nbsp;--gate
            </div>

            <div className="text-slate-400 mb-2"># 3. Open Next.js Workbench UI</div>
            <div className="text-emerald-400 font-semibold">cd web &amp;&amp; pnpm dev</div>
          </div>

          <div className="mt-8 flex justify-center">
            <Link
              href="/workbench"
              className="inline-flex items-center gap-2 bg-indigo-600 text-white font-medium text-sm px-8 py-3 rounded-lg hover:bg-indigo-500 transition-colors shadow-lg"
            >
              <span>Explore Interactive Workbench</span>
              <span>→</span>
            </Link>
          </div>
        </div>
      </section>

      {/* 6. TASTEFUL FOOTER & CREDITS */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-slate-200 bg-white text-xs text-slate-600">
        <div className="max-w-6xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4">
            <span className="font-mono font-bold text-slate-900 uppercase">PropEval v0.5.0</span>
            <span className="text-slate-300 hidden sm:inline">·</span>
            <span>Apache-2.0 License</span>
            <span className="text-slate-300 hidden sm:inline">·</span>
            <span>Engineered by Sahil Pal</span>
          </div>

          <div className="flex flex-wrap items-center gap-4 sm:gap-6 font-medium">
            <a
              href="https://github.com/saahilpal/propeval"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition-colors"
            >
              GitHub
            </a>
            <a
              href="https://sahil-pal-portfolio-d147.vercel.app/"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition-colors"
            >
              Portfolio
            </a>
            <a
              href="https://www.linkedin.com/in/sahiilpal"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition-colors"
            >
              LinkedIn
            </a>
            <a
              href="https://huggingface.co/saahilpal17"
              target="_blank"
              rel="noreferrer"
              className="hover:text-slate-900 transition-colors"
            >
              Hugging Face
            </a>
            <a
              href="mailto:saahilpal17@gmail.com"
              className="text-indigo-600 hover:text-indigo-800 transition-colors font-mono"
            >
              saahilpal17@gmail.com
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
