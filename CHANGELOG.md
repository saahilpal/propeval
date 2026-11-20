# Changelog

All notable changes to PropEval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.2.0] - 2026-11-20

### Added - Frontier Anti-Cheat & Evaluator Bias Defenses
- **Anti-Cheat Engine (`backend/app/evaluation/anti_cheat.py`):**
  - **Verbosity & Length-Bloat Penalty:** Implemented `detect_verbosity_inflation` based on AlpacaEval 2.0 (Dubois et al., 2024). Flags prompts with $> 25\%$ character bloat without factual gains.
  - **Judge Position-Flip Rate ($R_{\text{flip}}$):** Implemented `compute_position_flip_rate` measuring pairwise order instability $(A, B)$ vs $(B, A)$ (Wang et al., 2023) and flagging benchmarks with $> 10\%$ flip rate.
  - **Judge-vs-Deterministic Disagreement Alarms:** Implemented `detect_judge_disagreement` to catch sycophantic LLM judge hallucinations (e.g., claiming `passed: true` when a Layer 1 DNC regex or Layer 2 RERA check failed).
- **Microsecond CPU Evasion Scanner (`backend/app/security/injection_detector.py`):**
  - Fast, deterministic regex + token-entropy classifier running in $< 1\text{ms}$ on CPU to detect delimiter breakouts (`</transcript_nonce>`), LLM control tokens (`<|im_start|>`, `[INST]`), and prompt leaks.
- **Backend & API Edge-Case Hardening:**
  - Empty scenario suite upload now returns clean HTTP `422` RFC 9457 Problem Details (`backend/app/api/suites.py`).
  - Malformed UTF-8 surrogates and control null bytes sanitized on telephony transcript import.
  - Idempotent prompt registration returning `200 OK` on matching SHA-256 (`backend/app/api/prompts.py`).
  - `trials_k` boundary validation enforced at `1..10` via Pydantic (`backend/app/api/runs.py`).
  - Revoked/stale API key rejection returning HTTP `401 Unauthorized` (`backend/app/api/deps.py`).
  - Graceful worker shutdown helper (`release_worker_jobs`) releasing running jobs back to `QUEUED` on `SIGTERM`.
- **Claude / Linear / Stripe UI/UX Overhaul (`web/`):**
  - Neutral `#FAFAFA` layered surfaces, 1px `#E5E7EB` hairlines, and tabular `IBM Plex Mono` metrics.
  - Added Frontier Anti-Cheat & Bias Defense Telemetry card to Workbench.
  - Smooth sliding filter pills (`All Scenarios`, `Regressions Only`, `Hard Gate Fails`, `Anti-Cheat Flags`).
  - Interactive tool call arguments & outcomes disclosure drawer in Synchronized Turn Inspector.
  - Empty state and inline error toast with retry on FastAPI disconnect.
  - Playwright visual proof loop expanded to 9 screenshots across `1440x900`, `1024x768`, and `768x1024` with zero console/hydration errors.
- Test suite expanded to **89 automated tests** (89/89 passed in 8.8s).

## [v0.1.0] - 2026-11-20

### Added - Gate 5: Adversarial Red-Team & Edge-Case Hardening
- **Permanent Regression Suite (`backend/tests/red_team/`):**
  - Added 27 dedicated attack & fuzzing regression tests covering all 6 threat vectors.
- **Vector 1: OWASP LLM01 Indirect Prompt Injection & XML Nonce Escaping:**
  - Hardened `_format_transcript_with_nonce` with `sanitize_untrusted_transcript` to escape delimiter breakouts (`</transcript_...>`) and strip LLM control tokens (`<|im_start|>`, `<|system|>`, `[INST]`, `<<SYS>>`).
  - Added sanitization and DPDP PII scrubbing directly to `/api/v1/suites/replay/import`.
- **Vector 2: Multi-Tenant FORCE RLS & Auth Escape:**
  - Fixed connection dependency `get_db_connection` to set session-level `app.current_tenant_id` and cleanly reset in a `finally` block, ensuring FORCE RLS applies across all queries in pooled connections.
  - Enforced UUID format validation on `X-Tenant-ID` header (returns HTTP 400 with RFC 9457 error on malformed/SQLi input).
  - Protected `DELETE /api/v1/tenants/{id}` with mandatory `X-Admin-Key` authorization (returns HTTP 403 on unauthenticated/unauthorized calls).
- **Vector 3: SSRF, Redirect & Slowloris Abuse:**
  - Enhanced `is_safe_webhook_url` and `RemoteWebhookAgentAdapter` with explicit blocking of RFC 6598 CGNAT (`100.64.0.0/10`), link-local metadata (`169.254.0.0/16`), and private/multicast spaces.
  - Enforced zero-redirect policy (raising `SSRFSecurityError` on any HTTP 3xx redirect).
  - Enforced 1 MB streaming response size cap to prevent memory exhaustion / zip bombs.
  - Configured structured timeouts (5s connect, 30s read, 45s total wall clock).
- **Vector 4: DPDP PII Redaction Fuzzing:**
  - Extended `redact_pii_dpdp` with full support for Devanagari numerals (`०-९`) in Indian mobile, PAN, and Verhoeff-validated Aadhaar numbers.
  - Added support for allowlisting legitimate project names (e.g. "Godrej Woods") and RERA registration codes to prevent false positive redactions.
- **Vector 5: Concurrency, Budget & Crash Chaos:**
  - Implemented HTTP `Idempotency-Key` serialisation on `POST /api/v1/runs` via PostgreSQL advisory locks and `http_idempotency_keys` store, eliminating race conditions during bursts.
  - Added HTTP 422 Idempotency Conflict rejection when key is reused with different request payload.
  - Verified crash reclamation under tight $0.05 budget where `claim_next_eval_job` reclaims orphaned reservations.
- **Vector 6: Statistical, Hinglish & UI Edge-Case Fuzzing:**
  - Hardened McNemar exact test with zero discordant pairs ($b=0, c=0$), returning $p=1.0$ and valid Method 10 CI without division by zero.
  - Hardened Wilcoxon signed-rank test on all-tied differences ($s_2 - s_1 = 0$), returning $p=1.0$ and zero correlation.
  - Extended Indian unit normalizers to support Devanagari numerals (`१२ लाख`, `१.५ करोड़`, `५० हज़ार`) and Hindi script terms (`बीएचके`, `कमरा`, `वर्ग फुट`).

### Added - Gate 3: Anti-Slop Workbench UI & Playwright Visual Verification
- **Next.js 16.4.6 / React 19 Frontend (`web/`):**
  - Linear / Vercel / Stripe Workbench anti-slop aesthetic: neutral canvas `#FAFAFA`, 1px solid borders `#E5E7EB`, tabular `IBM Plex Mono` for all numbers, CIs, and latencies.
  - Direct proxy rewrites from Next.js (`http://localhost:3000/api/v1/*`) to live FastAPI backend (`http://127.0.0.1:8001/api/v1/*`).
- **3 Purpose-Built Screens:**
  - **Regression Diff Workbench (`/`):** Sticky prompt regression verdict banner, non-compensatory 4-gate scorecard, paired McNemar & Wilcoxon stats with visual Newcombe CI bar, and scenario triage table.
  - **Synchronized Turn Inspector (`/runs/[id]/scenarios/[scenario_id]`):** Side-by-side turn-by-turn comparison, raw semantic intent vs 8 kHz Indian telephony ASR audio toggle, and tool execution badges.
  - **Registry (`/registry`):** Prompt versions, versioned property truth fixtures, and evaluation suites with SHA-256 integrity hashes.

### Added - Gate 2: Control Plane API, Durable SSE Stream, Worker & 5-Mutant Meta-Eval
- **FastAPI Control Plane (`backend/app/main.py`, `backend/app/api/`):**
  - Live on `http://localhost:8001` with RFC 9457 Problem Details error formatting.
  - Durable Server-Sent Events (`/api/v1/runs/{id}/stream`) with `Last-Event-ID` resume.
- **5-Mutant Meta-Eval (`backend/tests/test_mutation_meta_eval.py`):**
  - Proves PropEval catches 5 out of 5 regressions locally at $0 spend.

### Added - Gate 1: Core Database, Replay Engine, Evaluation Layers & Paired Stats
- **Database & Storage (Postgres 17):**
  - Full relational DDL in `backend/sql/01_init.sql` with 15 core tables.
  - Split partial indexes (`idx_eval_jobs_queued`, `idx_eval_jobs_expired_lease`).
  - `FORCE RLS` on tenant data with `NULLIF(current_setting('app.current_tenant_id', true), '')`.
  - `claim_next_eval_job()` `SECURITY DEFINER` function with per-tenant fairness cap.
- **AI Simulator & Engine:**
  - `LLMProvider` protocol with `$0` Deterministic Replay Provider.
  - `BuyerAgendaFSM` hybrid state machine with Indian real-estate buyer personas.
  - Indian telephony perturbations: 8 kHz ASR phoneme confusion matrix and barge-in cutoffs.
  - `MockRealEstateEnv` with replayable tool calls and HTTP 503 fault injector.
- **Evaluation & Statistical Rigor:**
  - Indian real-estate normalizers with Hypothesis property testing.
  - Layer 1 Deterministic checks + Layer 2 Fact Verifier + Layer 3 Cross-Family Rubric Judge.
  - Paired stats: Exact McNemar with Newcombe Method 10 CI, Wilcoxon Signed-Rank, Two-Stage Cluster BCa Bootstrap, Holm-Bonferroni correction.
