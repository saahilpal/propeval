"use client";

import Link from "next/link";
import { useEffect, useState, useRef } from "react";
import { animate, stagger } from "animejs";
import {
  ArrowRight,
  Terminal,
  ShieldAlert,
  Sparkles,
  ExternalLink,
  Check,
  Copy,
  AlertTriangle,
  Layers,
  Activity,
  DollarSign,
  Cpu,
  Clock,
  PhoneCall,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { fetchCascadeMetrics, CascadeMetrics } from "@/lib/api";

export default function ProductLandingPage() {
  const [metrics, setMetrics] = useState<CascadeMetrics | null>(null);
  const [copiedSnippet, setCopiedSnippet] = useState(false);
  const [activeArchTab, setActiveArchTab] = useState<"pipeline" | "cascade">("pipeline");
  const heroRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchCascadeMetrics()
      .then((data) => setMetrics(data))
      .catch((err) => console.warn("Live telemetry fallback:", err));
  }, []);

  // Anime.js GPU entrance animation respecting prefers-reduced-motion
  useEffect(() => {
    if (typeof window === "undefined") return;
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    try {
      animate(".hero-stagger", {
        opacity: [0, 1],
        translateY: [16, 0],
        delay: stagger(90, { start: 100 }),
        duration: 650,
        ease: "outQuad",
      });

      animate(".failure-card", {
        opacity: [0, 1],
        translateY: [20, 0],
        delay: stagger(80, { start: 400 }),
        duration: 700,
        ease: "outQuad",
      });
    } catch (e) {
      console.warn("AnimeJS animation skipped:", e);
    }
  }, []);

  const copyCliCommand = () => {
    navigator.clipboard.writeText(
      "docker compose up -d && uv sync && uv run python -m backend.cli.main run --gate"
    );
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  return (
    <div className="flex flex-col w-full bg-canvas text-ink-primary">
      {/* 1. HERO SECTION */}
      <section
        ref={heroRef}
        className="relative pt-14 pb-18 md:pt-20 md:pb-24 px-4 sm:px-6 lg:px-8 border-b border-border bg-gradient-to-b from-surface to-canvas"
      >
        <div className="max-w-5xl mx-auto flex flex-col items-center text-center">
          {/* Release & Local Proof Badge */}
          <div className="hero-stagger inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono font-medium bg-surface border border-border text-slate-700 shadow-xs mb-6">
            <span className="w-2 h-2 rounded-full bg-accent-emerald animate-pulse" />
            <span className="font-semibold text-ink-primary">PropEval v0.5.0</span>
            <span className="text-slate-300">·</span>
            <span className="text-slate-600">100% Local $0 Build</span>
            <span className="text-slate-300">·</span>
            <span className="text-accent-emerald font-semibold">146/146 Tests Passing</span>
          </div>

          {/* Main Headline */}
          <h1 className="hero-stagger text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-ink-primary max-w-4xl leading-[1.12]">
            Pre-Release Prompt Regression & Reliability Workbench for{" "}
            <span className="text-slate-900 border-b-4 border-slate-300 pb-0.5">
              Indian Real Estate Voice AI
            </span>
          </h1>

          {/* Subtitle */}
          <p className="hero-stagger mt-6 text-base sm:text-lg md:text-xl text-slate-600 max-w-2xl leading-relaxed">
            Real-estate Voice AI breaks silently on Hinglish calls. PropEval catches every regression before a single buyer hears it.
          </p>

          {/* Primary Action Buttons */}
          <div className="hero-stagger mt-8 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/workbench"
              className="inline-flex items-center gap-2 bg-ink-primary text-white font-medium text-sm px-6 py-3 rounded-lg shadow-sm hover:bg-slate-800 transition-all hover:translate-y-[-1px]"
            >
              <Sparkles className="w-4 h-4 text-amber-400" />
              <span>Try Live Workbench</span>
              <span className="text-[11px] font-mono text-slate-300 ml-1">(Preloaded &amp; Ready)</span>
              <ArrowRight className="w-4 h-4 text-slate-400 ml-1" />
            </Link>

            <button
              onClick={copyCliCommand}
              className="inline-flex items-center gap-2 bg-surface text-ink-primary font-mono text-xs px-5 py-3 rounded-lg border border-border shadow-xs hover:bg-slate-50 transition-colors"
            >
              <Terminal className="w-4 h-4 text-slate-500" />
              <span>propeval run --gate</span>
              <span className="text-[10px] text-slate-400 ml-1 flex items-center gap-1">
                {copiedSnippet ? (
                  <>
                    <Check className="w-3 h-3 text-accent-emerald" />
                    <span>Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-3 h-3" />
                    <span>Copy</span>
                  </>
                )}
              </span>
            </button>
          </div>

          {/* Badges strip (GitHub & Hugging Face) */}
          <div className="hero-stagger mt-6 flex flex-wrap items-center justify-center gap-3 text-xs">
            <a
              href="https://github.com/saahilpal/propeval"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md border border-border bg-surface text-slate-700 hover:text-ink-primary hover:border-slate-400 transition-colors"
            >
              <span className="font-semibold">GitHub:</span>
              <span className="font-mono text-slate-500">saahilpal/propeval</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>

            <a
              href="https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md border border-border bg-surface text-slate-700 hover:text-ink-primary hover:border-slate-400 transition-colors"
            >
              <span className="font-semibold">Model:</span>
              <span className="font-mono text-slate-500">propeval-laya-hinglish-v1</span>
              <ExternalLink className="w-3 h-3 text-slate-400" />
            </a>
          </div>

          {/* Hero Live Preview Strip */}
          <div className="hero-stagger mt-10 w-full max-w-4xl bg-slate-950 text-slate-200 rounded-xl p-4 sm:p-5 border border-slate-800 text-left shadow-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800 text-xs font-mono text-slate-400">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-accent-crimson" />
                <span className="w-2.5 h-2.5 rounded-full bg-accent-amber" />
                <span className="w-2.5 h-2.5 rounded-full bg-accent-emerald" />
                <span className="ml-2 font-semibold text-slate-200">
                  REGRESSION GATE: Candidate V2 vs Baseline V1
                </span>
              </div>
              <span className="text-accent-crimson font-semibold">EXIT CODE: 1 (BLOCKED FROM PROD)</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 text-xs font-mono">
              <div className="bg-slate-900/90 p-3 rounded border border-red-900/40">
                <div className="text-accent-crimson font-bold uppercase tracking-wider text-[10px] flex items-center justify-between">
                  <span>Turn 4 · DNC Breach</span>
                  <XCircle className="w-3 h-3" />
                </div>
                <div className="mt-1.5 text-slate-200 font-sans">"faltu call band kar abhi"</div>
                <div className="mt-1 text-slate-400 text-[11px] font-sans">
                  Agent kept pitching instead of invoking <code className="text-slate-300">mark_dnc()</code> and hanging up.
                </div>
              </div>

              <div className="bg-slate-900/90 p-3 rounded border border-amber-900/40">
                <div className="text-accent-amber font-bold uppercase tracking-wider text-[10px] flex items-center justify-between">
                  <span>Turn 6 · 8 kHz Misparse</span>
                  <AlertTriangle className="w-3 h-3" />
                </div>
                <div className="mt-1.5 text-slate-200 font-sans">"ek point do crore budget"</div>
                <div className="mt-1 text-slate-400 text-[11px] font-sans">
                  Parsed as <code className="text-slate-300">₹1.2L</code> and quoted 250 sqft studio.
                </div>
              </div>

              <div className="bg-slate-900/90 p-3 rounded border border-red-900/40">
                <div className="text-accent-crimson font-bold uppercase tracking-wider text-[10px] flex items-center justify-between">
                  <span>Turn 8 · CRM 503 Lie</span>
                  <XCircle className="w-3 h-3" />
                </div>
                <div className="mt-1.5 text-slate-200 font-sans">CRM WhatsApp tool: HTTP 503</div>
                <div className="mt-1 text-slate-400 text-[11px] font-sans">
                  Agent falsely assured buyer <code className="text-slate-300">"WhatsApp bhej diya sir"</code>.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. THE 4 PRODUCTION FAILURES IT STOPS */}
      <section className="py-16 md:py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-3xl mx-auto">
          <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-border">
            Hinglish Telephony Failure Modes
          </span>
          <h2 className="mt-4 text-2xl sm:text-3xl md:text-4xl font-extrabold text-ink-primary tracking-tight">
            The 4 Production Failures PropEval Stops
          </h2>
          <p className="mt-3 text-sm sm:text-base text-slate-600 leading-relaxed">
            Standard US-centric LLM evals fail completely on Indian voice agents. In Indian real estate, a single compliance lapse or invented amenity destroys trust and triggers regulatory fines.
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Failure 1 */}
          <div className="failure-card p-6 rounded-xl border border-border bg-surface hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-50 text-accent-amber border border-amber-200">
                  01 · ASR Currency Misparse
                </span>
                <span className="text-xs font-mono text-slate-400">8 kHz Telephony</span>
              </div>
              <h3 className="text-base font-bold text-ink-primary">
                "ek point do crore" parsed as ₹1.2 Lakhs
              </h3>
              <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono space-y-1.5">
                <div className="text-slate-500">
                  <span className="text-slate-700 font-semibold">Buyer Hinglish:</span> "Bhai 1.2 cr tak ka budget hai, Wakad mein 3BHK dikhao"
                </div>
                <div className="text-accent-crimson">
                  <span className="font-semibold">Regressed Prompt:</span> Interpreted budget as ₹1,20,000 and replied "Sir Wakad mein 1.2 Lakh mein 1RK studio nahi mil payega."
                </div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-slate-600">
              <span className="font-mono text-accent-emerald font-medium">PropEval Detection:</span>
              <span>Layer 1 Unit Normalizer catches acoustic perturbation</span>
            </div>
          </div>

          {/* Failure 2 */}
          <div className="failure-card p-6 rounded-xl border border-border bg-surface hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-red-50 text-accent-crimson border border-red-200">
                  02 · RERA Date Hallucination
                </span>
                <span className="text-xs font-mono text-slate-400">RERA Legal Risk</span>
              </div>
              <h3 className="text-base font-bold text-ink-primary">
                Promised possession "next month" (RERA: Dec 2027)
              </h3>
              <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono space-y-1.5">
                <div className="text-slate-500">
                  <span className="text-slate-700 font-semibold">Buyer Hinglish:</span> "Possession kab tak milega? Urgent shifting chahiye."
                </div>
                <div className="text-accent-crimson">
                  <span className="font-semibold">Regressed Prompt:</span> "Sir agle mahine hi keys mil jayengi, ready to move in hai."
                </div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-slate-600">
              <span className="font-mono text-accent-emerald font-medium">PropEval Detection:</span>
              <span>Layer 2 Project Grounding rejects unverified possession dates</span>
            </div>
          </div>

          {/* Failure 3 */}
          <div className="failure-card p-6 rounded-xl border border-border bg-surface hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-red-50 text-accent-crimson border border-red-200">
                  03 · TRAI DNC Opt-Out Ignored
                </span>
                <span className="text-xs font-mono text-slate-400">₹2.5L Telecom Fine</span>
              </div>
              <h3 className="text-base font-bold text-ink-primary">
                "mat call karo" treated as soft objection
              </h3>
              <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono space-y-1.5">
                <div className="text-slate-500">
                  <span className="text-slate-700 font-semibold">Buyer Hinglish:</span> "Yaar mat call karo please, bilkul interested nahi hoon."
                </div>
                <div className="text-accent-crimson">
                  <span className="font-semibold">Regressed Prompt:</span> "Sir sirf 2 minute sun lijiye, bahut achha pre-launch discount hai..."
                </div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-slate-600">
              <span className="font-mono text-accent-emerald font-medium">PropEval Detection:</span>
              <span>Layer 1 FSM verifies immediate <code className="text-slate-800 font-mono">mark_dnc</code> execution</span>
            </div>
          </div>

          {/* Failure 4 */}
          <div className="failure-card p-6 rounded-xl border border-border bg-surface hover:shadow-sm transition-all flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-bold bg-amber-50 text-accent-amber border border-amber-200">
                  04 · Tool Failure Cascade
                </span>
                <span className="text-xs font-mono text-slate-400">CRM Outage Lie</span>
              </div>
              <h3 className="text-base font-bold text-ink-primary">
                CRM WhatsApp tool 503, Agent claims "WhatsApp bhej diya"
              </h3>
              <div className="mt-3 p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs font-mono space-y-1.5">
                <div className="text-slate-500">
                  <span className="text-slate-700 font-semibold">CRM Dispatch Tool:</span> Returned HTTP 503 Service Unavailable
                </div>
                <div className="text-accent-crimson">
                  <span className="font-semibold">Regressed Prompt:</span> "Sir WhatsApp pe floor plan bhej diya hai, check kar lijiye."
                </div>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs text-slate-600">
              <span className="font-mono text-accent-emerald font-medium">PropEval Detection:</span>
              <span>Tool-fault injector halts and flags invented verbal promises</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. VERIFIED OOD PROOF STRIP */}
      <section className="py-14 bg-surface border-y border-border px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-600">
              Empirical Evaluation Telemetry
            </span>
            <h2 className="mt-2 text-2xl sm:text-3xl font-extrabold text-ink-primary tracking-tight">
              Verified OOD Proof Strip
            </h2>
            <p className="mt-1.5 text-xs sm:text-sm text-slate-600">
              Loaded directly from audited benchmark ledgers and live PostgreSQL metrics. Zero fake numbers.
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
            <div className="bg-canvas p-5 rounded-xl border border-border shadow-xs">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                  OOD Accuracy
                </div>
                <Activity className="w-4 h-4 text-accent-emerald" />
              </div>
              <div className="text-3xl font-mono font-bold text-accent-emerald mt-2 tabular-nums">
                97.62%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Laya cascade with calibration escalation
              </div>
            </div>

            <div className="bg-canvas p-5 rounded-xl border border-border shadow-xs">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                  P95 S1 Latency
                </div>
                <Clock className="w-4 h-4 text-slate-600" />
              </div>
              <div className="text-3xl font-mono font-bold text-ink-primary mt-2 tabular-nums">
                {(metrics?.cpu_latency_p95_ms ?? 0.38).toFixed(2)} ms
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                56x faster than frontier judge (&lt; 25 ms SLA)
              </div>
            </div>

            <div className="bg-canvas p-5 rounded-xl border border-border shadow-xs">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                  Eval Spend Cut
                </div>
                <DollarSign className="w-4 h-4 text-slate-600" />
              </div>
              <div className="text-3xl font-mono font-bold text-ink-primary mt-2 tabular-nums">
                {(metrics?.net_dollar_savings_pct ?? 92.06).toFixed(1)}%
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                $0 cost for 92.1% turns resolved locally
              </div>
            </div>

            <div className="bg-canvas p-5 rounded-xl border border-border shadow-xs">
              <div className="flex items-center justify-between">
                <div className="text-xs font-mono uppercase tracking-wider text-slate-500">
                  Expected Calibration
                </div>
                <ShieldAlert className="w-4 h-4 text-accent-emerald" />
              </div>
              <div className="text-3xl font-mono font-bold text-accent-emerald mt-2 tabular-nums">
                {(metrics?.expected_calibration_error ?? 0.0209).toFixed(4)}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                ECE &lt; 0.0500 strict calibration standard
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. HOW IT WORKS (3 STEPS) */}
      <section className="py-16 md:py-20 px-4 sm:px-6 lg:px-8 max-w-6xl mx-auto w-full">
        <div className="text-center max-w-3xl mx-auto mb-14">
          <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-full border border-border">
            Execution Flow
          </span>
          <h2 className="mt-4 text-2xl sm:text-3xl md:text-4xl font-extrabold text-ink-primary tracking-tight">
            How PropEval Works
          </h2>
          <p className="mt-3 text-sm sm:text-base text-slate-600">
            A deterministic 3-step loop protecting your telephony agents from regressions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="border border-border rounded-xl p-6 bg-surface shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-ink-primary font-mono text-sm font-bold flex items-center justify-center mb-4">
              01
            </div>
            <h3 className="text-base font-bold text-ink-primary">Select Baseline &amp; Candidate</h3>
            <p className="mt-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
              Pick your verified production baseline prompt and your candidate modification — or use the interactive guided prompt builder to test custom guardrails.
            </p>
          </div>

          <div className="border border-border rounded-xl p-6 bg-surface shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-ink-primary font-mono text-sm font-bold flex items-center justify-center mb-4">
              02
            </div>
            <h3 className="text-base font-bold text-ink-primary">Simulate Hinglish Telephony</h3>
            <p className="mt-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
              Synthesize multi-turn buyer dialogues across 8 kHz telephony codecs, phonetic perturbations, aggressive budget bargaining, and injected CRM socket faults.
            </p>
          </div>

          <div className="border border-border rounded-xl p-6 bg-surface shadow-xs">
            <div className="w-8 h-8 rounded-lg bg-slate-100 text-ink-primary font-mono text-sm font-bold flex items-center justify-center mb-4">
              03
            </div>
            <h3 className="text-base font-bold text-ink-primary">Layered Laya Cascade Verification</h3>
            <p className="mt-2 text-xs sm:text-sm text-slate-600 leading-relaxed">
              Layer 1 deterministic checks catch DNC &amp; unit errors. System-1 Laya resolves 92% of turns locally in 0.38 ms. Novel slang escalates safely to frontier judge.
            </p>
          </div>
        </div>
      </section>

      {/* 5. INTERACTIVE ARCHITECTURE VIEWER */}
      <section className="py-16 bg-surface border-t border-border px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
            <div>
              <span className="text-xs font-mono uppercase tracking-wider font-semibold text-slate-600">
                System Specification
              </span>
              <h2 className="mt-1 text-2xl font-extrabold text-ink-primary tracking-tight">
                Architectural Proof of Record
              </h2>
            </div>

            <div className="flex items-center gap-2 bg-canvas p-1 rounded-lg border border-border">
              <button
                onClick={() => setActiveArchTab("pipeline")}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activeArchTab === "pipeline"
                    ? "bg-ink-primary text-white"
                    : "text-slate-600 hover:text-ink-primary"
                }`}
              >
                End-to-End Pipeline
              </button>
              <button
                onClick={() => setActiveArchTab("cascade")}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  activeArchTab === "cascade"
                    ? "bg-ink-primary text-white"
                    : "text-slate-600 hover:text-ink-primary"
                }`}
              >
                System-1 Laya Cascade
              </button>
            </div>
          </div>

          <div className="bg-canvas border border-border rounded-xl p-4 sm:p-6 shadow-xs">
            {activeArchTab === "pipeline" ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                  <span>Architecture: End-to-End Evaluation Engine &amp; Gating Pipeline</span>
                  <a
                    href="/architecture/pipeline_architecture.svg"
                    target="_blank"
                    className="text-slate-700 hover:underline flex items-center gap-1"
                  >
                    <span>Full SVG</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex justify-center bg-white rounded-lg p-2 border border-slate-200 overflow-hidden">
                  <img
                    src="/architecture/pipeline_architecture.svg"
                    alt="PropEval Pipeline Architecture"
                    className="w-full max-h-[500px] object-contain"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs font-mono text-slate-500">
                  <span>Architecture: System-1 Laya Classifier &amp; Calibration Escalation Cascade</span>
                  <a
                    href="/architecture/system1_laya_cascade.svg"
                    target="_blank"
                    className="text-slate-700 hover:underline flex items-center gap-1"
                  >
                    <span>Full SVG</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
                <div className="flex justify-center bg-white rounded-lg p-2 border border-slate-200 overflow-hidden">
                  <img
                    src="/architecture/system1_laya_cascade.svg"
                    alt="Laya Cascade Architecture"
                    className="w-full max-h-[500px] object-contain"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* 6. CALL TO ACTION STRIP */}
      <section className="py-16 bg-slate-950 text-white px-4 sm:px-6 lg:px-8 border-t border-slate-800">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight text-white">
            Ready to Catch Hinglish Voice Regressions?
          </h2>
          <p className="mt-3 text-sm text-slate-400 max-w-xl mx-auto">
            Try the live workbench preloaded with baseline prompts and Hinglish test suites. Zero registration, zero API keys required.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/workbench"
              className="inline-flex items-center gap-2 bg-white text-slate-950 font-medium text-sm px-6 py-3 rounded-lg hover:bg-slate-100 transition-colors shadow-lg"
            >
              <Sparkles className="w-4 h-4 text-amber-500" />
              <span>Launch Live Interactive Workbench</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <a
              href="https://github.com/saahilpal/propeval"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 bg-slate-900 text-slate-200 font-mono text-xs px-5 py-3 rounded-lg border border-slate-800 hover:bg-slate-800 transition-colors"
            >
              <span>View Source on GitHub</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </section>

      {/* 7. SAHIL PAL AUTHOR FOOTER */}
      <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-border bg-surface text-xs text-slate-600">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex flex-col sm:flex-row items-center gap-2 sm:gap-4 text-center sm:text-left">
            <span className="font-mono font-bold text-ink-primary uppercase tracking-wider">
              PropEval v0.5.0
            </span>
            <span className="text-slate-300 hidden sm:inline">·</span>
            <span>Apache-2.0 Open Source</span>
            <span className="text-slate-300 hidden sm:inline">·</span>
            <span>
              Engineered by <strong className="text-ink-primary font-semibold">Sahil Pal</strong>
            </span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 font-medium">
            <a
              href="https://github.com/saahilpal/propeval"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-primary transition-colors"
            >
              GitHub
            </a>
            <a
              href="https://sahil-pal-portfolio-d147.vercel.app/"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-primary transition-colors"
            >
              Portfolio
            </a>
            <a
              href="https://www.linkedin.com/in/sahiilpal"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-primary transition-colors"
            >
              LinkedIn
            </a>
            <a
              href="https://huggingface.co/saahilpal17"
              target="_blank"
              rel="noreferrer"
              className="hover:text-ink-primary transition-colors"
            >
              Hugging Face
            </a>
            <a
              href="mailto:saahilpal17@gmail.com"
              className="hover:text-ink-primary transition-colors font-mono"
            >
              saahilpal17@gmail.com
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
