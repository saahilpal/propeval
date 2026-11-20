# 16 — Implementation Roadmap

This roadmap sequences implementation realistically across a **4-week Focused MVP** (delivering an end-to-end, live-demoable Hinglish prompt regression workbench with zero premature infrastructure) followed by **Phase 2 Production Hardening** and **Phase 3 Layer-2 Audio Replay**. *(Note: This document is a planning specification only; no application code has been implemented.)*

---

## Phase 1 — Focused MVP (Weeks 1–4, Solo Engineer)

### Week 1: Core Schema, Transactional Queue & Deterministic Oracles
* **Deliverables:** PostgreSQL `17.12` schema + Alembic `1.20.1` migrations (`tenants`, `tenant_credentials`, `http_idempotency_keys`, `prompt_versions`, `project_fixtures`, `scenario_suites`, `eval_runs`, `budget_reservations`, `eval_jobs`, `run_events`, `conversation_turns`, `assertion_results`, `llm_call_ledger`, `calibration_anchors`, `judge_calibrations`); `claim_next_eval_job()` `SECURITY DEFINER` function + split partial indexes; ledger-first `call_with_ledger_and_budget()` helper; Indian real-estate currency/unit normalizer (`lakh`/`crore`/`peti`/`khoka`/Hinglish) verified with `Hypothesis 6.170.15` property tests.
* **Exit Gate:** `pytest` + `Hypothesis` unit suite passes in <30 s with 0 API calls; simulated worker `SIGKILL` test verifies lease reclamation, `budget_reservations` release, and 0% duplicate billing on persisted turns.

### Week 2: Hybrid FSM+LLM Simulator & 3-Tier Evaluation Core
* **Deliverables:** `BuyerAgendaFSM` + Hinglish surface realizer + `MockRealEstateEnv` (with `replay_tool_calls()` on resume); domain 8 kHz Indian ASR perturbation matrix & mock `503`/timeout tool faults; 20 Tier-1 smoke scenarios + 30 additional Tier-2 scenarios across Mumbai/Gurugram project fixtures; Layer 1 deterministic checks (schema, DNC exit, invented-action check, metamorphic pairs); Layer 2 property fact verifier with negation window; Layer 3 cross-family binary rubric judge (position-swapped, XML nonce framing).
* **Exit Gate:** 30 hand-labeled transcripts calibrate judge ($\kappa \ge 0.70$, Fail Recall $\ge 0.80$); **Mutation Meta-Eval** catches 5/5 deliberately injected prompt/tool bugs.

### Week 3: Statistical Engine, REST + Durable SSE API & CLI Gate
* **Deliverables:** `stats/` module (`SciPy 1.18.1` + `statsmodels 0.15.0`) implementing Exact McNemar + Newcombe Method 10 (for $K=1$ / binary `pass^k`), Wilcoxon signed-rank + two-stage cluster BCa bootstrap (for $K>1$ & continuous metrics), Holm-Bonferroni, BH-FDR, quarantined-pair exclusion, and `SMOKE_TEST_UNDERPOWERED` tagging; FastAPI `0.165.0` Control Plane (`/api/v1/*`) with durable PostgreSQL `run_events` + `LISTEN/NOTIFY` SSE streaming (`Last-Event-ID` resumable); `propeval` CLI exit-code gate wired into GitHub Actions; OpenTelemetry `1.45.2` (`gen_ai.*`) tracing.
* **Exit Gate:** End-to-end CLI smoke gate ($N=20$) completes in <90 s and exits `1` on deliberate V2 regressions.

### Week 4: Next.js Diff UI, Docker Compose & Live Demo
* **Deliverables:** Next.js `16.4.6` / React `19.3` Non-Compensatory Diff Viewer, live SSE progress bar, and turn-by-turn transcript/tool-call inspector; single-command `docker-compose.yml` (`api`, `worker`, `web`, `postgres:17.12`); public staging demo + 90-second walkthrough.
* **Exit Gate:** 3-minute live demo executes 20 paired Hinglish scenarios, flags 3 deliberate V2 regressions (DNC miss, `"ek point do crore"` ASR misparse, invented WhatsApp confirmation after `503`), and blocks PR merge in GitHub Actions.

---

## Phase 2 — Production Hardening & Multi-Tenant SaaS (Weeks 5–8)
* **Deliverables:** Enable `FORCE ROW LEVEL SECURITY` across all tenant-scoped tables; add Valkey `8.x` (BSD-3-Clause) Lua dual RPM/TPM rate limiter for multi-pod workers; integrate Cloud KMS AES-256-GCM envelope encryption for `tenant_credentials` and `DELETE /api/v1/tenants/{tenant_id}` erasure; deploy in-VPC Microsoft Presidio (Indian mobile/PAN/Verhoeff Aadhaar) on `POST /api/v1/replay/import`; stand up DNS-pinned SSRF egress proxy for `RemoteWebhookAgentAdapter`; expand Tier-2 release suite to $N=100$ with mSPRT harm early-abort and nightly EWMA/$p$-chart SPC + DuckDB `2.0.0` Parquet export.

## Phase 3 — Layer-2 Audio Replay & Scale Triggers (Post-v1.0)
* **Deliverables:** Add `PipecatAudioAgentAdapter` (`pipecat-ai 1.16.0`, BSD-2-Clause) replaying recorded 8 kHz G.711 Indian buyer audio via `soxr_hq` resampling, Smart Turn v3.2 EoT evaluation, and SEER/PIER acoustic metrics.
* **Scale Trigger:** Migrate `storage/queue.py` to **Temporal (`1.36.1`)** only if sustained queue transitions exceed 500/sec or multi-day human-in-the-loop grading workflows are required.
