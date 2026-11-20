# 00 — Executive Summary: PropEval Technical Foundation

**Document Version:** 1.1 (Post-Adversarial Principal Audit Revision — Research & Architecture Only)  
**Date:** November 19, 2026  
**Target Domain:** Hinglish & Multilingual Indian Real Estate Voice AI Agents (specifically aligned to [Huvo AI](https://huvo.ai/) / Ligatrix Technologies Private Limited)

---

## 1. The Engineering Problem in One Paragraph

Indian real estate Voice AI platforms like [Huvo AI](https://huvo.ai/) run 24/7 outbound and inbound qualification, site-visit booking, and WhatsApp follow-up calls across English, Hindi, Hinglish, Kannada, and Tamil. Huvo's own October–November 2026 hiring reveals the primary operational bottleneck: Prompt Engineers spend **60–70% of their time** tuning prompts and manually auditing call recordings/transcripts to curb hallucinations ([Wellfound Prompt Engineer JD](https://wellfound.com/jobs/4543729-prompt-engineer)), while the Founding Backend Engineer role explicitly calls for **evaluation tooling, idempotency, retries, and cost-performance observability** ([Wellfound Backend JD](https://wellfound.com/jobs/4544645-backend-engineer-python)). Every prompt edit risks silently breaking Indian currency extraction (`"1.2 cr"` vs `"120 lakh"`), RERA possession/carpet-area accuracy, TRAI DNC exit compliance, or tool-call contracts.

**PropEval** is a domain-specific **Hinglish Real-Estate Voice Agent Evaluation & Prompt Regression Workbench** that proves with quantitative rigor whether Prompt V2 improves upon Prompt V1 without introducing silent regressions in extraction, factual grounding, tool execution, safety, or latency.

---

## 2. Five Earlier Assumptions Challenged & Overturned

| Earlier / Naive Assumption | What Independent Research Proved | Revised Architectural Decision |
| :--- | :--- | :--- |
| **1. Pure LLM persona simulators are sufficient** | Human audits of `τ²-Bench` found **40–47% user-simulator error rates** ([Barres et al., 2025](https://arxiv.org/abs/2506.07982)); RLHF models exhibit **assistant/benevolence bias** ([Jeong et al., Sep 2026](https://arxiv.org/abs/2609.00608)) and are **worst calibrated to Indian English** ($ECE = 18.9$ vs $13.0$; [Seshadri et al., Jan 2026](https://arxiv.org/abs/2601.17087)). | **Hybrid FSM/Agenda + LLM Surface Realization Simulator** (`ADR-003`) with programmatic slot-reveal triggers + **Simulator-Fidelity Auditor** with paired-arm quarantine. |
| **2. A 20-scenario suite proves Prompt V2 beats V1** | Exact power analysis proves at $N=20$, exact McNemar's test requires a **+36.6 pp to +53.4 pp** jump for 80% power. | **Two-Tier Statistical Gating** (`ADR-005`): Tier 1 ($N=20$) is a **PR Smoke & Hard-Gate Check** (`SMOKE_TEST_UNDERPOWERED`); Tier 2 ($N=50\text{–}100$, $K=3\text{–}5$) runs Wilcoxon + Cluster BCa Bootstrap + binary `pass^k` McNemar + Holm-Bonferroni. |
| **3. A single 0–100 score makes diffs easy to read** | Composite averages mask catastrophic RERA/pricing hallucinations behind tone gains ([Real World Voice EQ Bench, 2026](https://arxiv.org/abs/2607.14846)). | **Non-Compensatory Multidimensional Profile** (`ADR-004`): Zero-tolerance hard gates separated from 3-way cross-family calibrated binary rubric judges (clamped Rogan–Gladen / PPI++). |
| **4. Adopt DeepEval / Langfuse / LiteLLM as core** | Langfuse (`v4.81.0`) forces ClickHouse + `ee/LICENSE`; Promptfoo (`0.125.1`) is Node.js; Ragas (`0.4.4`) has pre-1.0 churn; LiteLLM (`1.110.0`) has license ambiguity. | **Adopt Mature Primitives, Build Transparent Core (~1,800–2,500 LOC)** (`ADR-006`): Adopt OTel (`1.45.2`), SciPy (`1.18.1`), statsmodels (`0.15.0`), Hypothesis (`6.170.15`), official SDKs, and Presidio; own the multi-turn FSM simulator & paired stats engine. |
| **5. Text simulation validates voice quality** | Text strips acoustic barge-in (<300 ms), prosody, 8 kHz G.711 8-bit quantization collapse ([arXiv:2606.09335](https://arxiv.org/html/2606.09335v1)), and Indic TTS mispronunciations. | **Explicit 3-Layer Evaluation Boundary** (`ADR-007`): Layer 1 Text + ASR-Perturbation Sim (MVP); Layer 2 Recorded 8 kHz Audio Replay via Pipecat (`1.16.0`, BSD-2-Clause); Layer 3 Live SIP/Twilio/Exotel Telephony. |

---

## 3. Selected Architecture & Adversarial Audit Improvements (v1.0 $\to$ v1.1)

PropEval selects **Option A: Modular Monolith + PostgreSQL `17.12` Transactional Job Queue (`FOR UPDATE SKIP LOCKED` + Lease/Fence Tokens) + Durable SSE (`run_events` + `PG LISTEN/NOTIFY`) + Thin CLI**. An independent skeptical Principal Engineer audit (`Reviews 1–5`) caught and drove fixes for seven critical defects now resolved in v1.1:
1. Added `SECURITY DEFINER` `claim_next_eval_job()` with per-tenant fairness caps and `NULLIF`-safe `FORCE RLS` so shared multi-tenant workers never deadlock.
2. Split queue indexing into two exact partial indexes (`WHERE status = 'QUEUED'` and `WHERE status = 'RUNNING'`).
3. Replaced single-row `eval_runs.reserved_usd` with crash-reclaimed `budget_reservations`, enforced ledger-first ordering, and routed auditor/judge calls through both ledger and budget caps.
4. Replaced ephemeral Pub/Sub with durable PostgreSQL `run_events` + `LISTEN/NOTIFY` so `Last-Event-ID` SSE resumption actually works (eliminating Valkey from MVP).
5. Fixed `MockRealEstateEnv.replay_tool_calls()` on partial turn resumption and replaced embedding-based stall detection with zero-dependency token Jaccard (`>0.85`).
6. Resolved the $K>1$ statistical contradiction (using Wilcoxon + Two-Stage Cluster Bootstrap on continuous per-scenario rates, reserving Exact McNemar/Newcombe strictly for $K=1$ or binary `pass^k`, with paired-arm quarantine exclusion).
7. Unified all table names, enums, endpoints (`dlq/replay`, `DELETE /tenants/{id}`), 3-way cross-family isolation, DPDP legal precision, and a realistic 4-week MVP + Phase 2 hardening roadmap.

---

## 4. Reading Map of This Documentation Package

All 19 core design documents (`docs/00`–`18`) and 8 Architecture Decision Records (`docs/adr/ADR-001`–`ADR-008`) are internally consistent and cross-referenced for direct implementation handoff.
