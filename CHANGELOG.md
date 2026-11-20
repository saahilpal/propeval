# Changelog

All notable changes to PropEval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - Gate 5: Adversarial Red-Team & Edge-Case Hardening
- **Permanent Regression Suite (`backend/tests/red_team/`):**
  - Added 27 dedicated attack & fuzzing regression tests covering all 6 threat vectors.
  - Test count expanded from 51 to 79 automated tests across the workspace (79/79 passing in ~6.5s).
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
  - Fuzzed mobile numbers across spaced, dashed, and regional prefix variants.
- **Vector 5: Concurrency, Budget & Crash Chaos:**
  - Implemented HTTP `Idempotency-Key` serialisation on `POST /api/v1/runs` via PostgreSQL advisory locks and `http_idempotency_keys` store, eliminating race conditions during bursts (10 concurrent requests yield exactly 1 run with shared response).
  - Added HTTP 422 Idempotency Conflict rejection when key is reused with different request payload.
  - Verified crash reclamation under tight $0.05 budget where `claim_next_eval_job` reclaims orphaned reservations.
  - Hardened SSE streaming (`GET /api/v1/runs/{id}/stream`) to handle stale/negative `Last-Event-ID` and terminate cleanly on completed runs.
- **Vector 6: Statistical, Hinglish & UI Edge-Case Fuzzing:**
  - Hardened McNemar exact test with zero discordant pairs ($b=0, c=0$), returning $p=1.0$ and valid Method 10 CI without division by zero.
  - Hardened Wilcoxon signed-rank test on all-tied differences ($s_2 - s_1 = 0$), returning $p=1.0$ and zero correlation.
  - Extended Indian unit normalizers to support Devanagari numerals (`१२ लाख`, `१.५ करोड़`, `५० हज़ार`) and Hindi script terms (`बीएचके`, `कमरा`, `वर्ग फुट`) with full equivalence checking.

### Added - Gate 2: Control Plane API, Durable SSE Stream, Worker & 5-Mutant Meta-Eval
- **FastAPI Control Plane (`backend/app/main.py`, `backend/app/api/`):**
  - Live on `http://localhost:8001` with RFC 9457 Problem Details error formatting.
  - `POST /api/v1/prompts` immutable registration with SHA-256 deduplication.
  - `POST /api/v1/fixtures` versioned property truth fixture upload.
  - `POST /api/v1/suites` and `POST /api/v1/replay/import` for telephony transcripts with DPDP PII scrubbing.
  - `POST /api/v1/runs`, `GET /api/v1/runs/{id}/diff` (non-compensatory matrix & failure stages), `GET /api/v1/runs/{id}/scenarios/{id}` (synchronized turn inspection).
  - `GET /api/v1/runs/{id}/stream` durable Server-Sent Events with `Last-Event-ID` replay.
  - `DELETE /api/v1/tenants/{id}` cascading purge.
- **Evaluation Worker & Execution Engine (`backend/app/engine/worker.py`):**
  - `execute_eval_job` runs FSM simulation, Indian ASR perturbations, mock tool execution, and Layer 1-3 evaluations.
  - Automated budget reservation settlement and paired statistics computation.
- **CLI (`backend/cli/main.py`):**
  - `propeval run --baseline ... --candidate ... --suite ... --fixture ... --gate` with monospace tabular output and exit code enforcement.
- **Security & DPDP Compliance:**
  - `RemoteWebhookAgentAdapter` with SSRF protection, loopback/private IP blocking, and 45s hard timeout.
  - `redact_pii_dpdp` with Verhoeff Aadhaar validation, PAN redaction, Indian phone scrubbing while preserving RERA numbers.
- **5-Mutant Meta-Eval (`backend/tests/test_mutation_meta_eval.py`):**
  - Proves PropEval catches 5 out of 5 regressions (dropped DNC, stale RERA date, broken currency parse, invented WhatsApp confirmation after HTTP 503, malformed booking tool schema) locally at $0 spend.
- 51/51 automated tests passing.

### Added - Gate 1: Core Database, Replay Engine, Evaluation Layers & Paired Stats
- **Database & Storage (Postgres 17):**
  - Full relational DDL in `backend/sql/01_init.sql` with 15 core tables.
  - Split partial indexes (`idx_eval_jobs_queued`, `idx_eval_jobs_expired_lease`, `idx_budget_res_active`, `idx_run_events_stream`).
  - `FORCE RLS` on tenant data with `NULLIF(current_setting('app.current_tenant_id', true), '')`.
  - `claim_next_eval_job()` `SECURITY DEFINER` function with per-tenant fairness cap.
  - Alembic migration setup with reversible migrations.
  - Asyncpg database pools, budget reservation helpers, and LLM call ledger.
- **AI Simulator & Engine:**
  - `LLMProvider` protocol with `$0` Deterministic Replay Provider.
  - `BuyerAgendaFSM` hybrid state machine with Indian real-estate buyer personas (budget, possession, RERA, site visit).
  - Indian telephony perturbations: 8 kHz ASR phoneme confusion matrix and barge-in cutoffs.
  - `MockRealEstateEnv` with replayable tool calls and HTTP 503 fault injector.
  - Token-Jaccard stall guard to abort looping dialogues.
  - Versioned YAML fixtures (`lodha_wakad_2026_11.yaml`, `dlf_gurugram_2026_11.yaml`) and evaluation suites.
- **Evaluation & Statistical Rigor:**
  - Indian real-estate normalizers (Crore/Lakh/K, 2.5 BHK / 3 BHK, sq ft / sq yd) with Hypothesis property testing.
  - Layer 1 Deterministic checks: DNC exit, invented actions, tool schema, metamorphic pairs.
  - Layer 2 Property Fact Verifier: negation-aware price, possession date, RERA check.
  - Layer 3 Cross-Family Rubric Judge with XML nonce framing and position swap debiasing.
  - Paired stats: Exact McNemar with Newcombe Method 10 CI, Wilcoxon Signed-Rank with rank-biserial correlation, Two-Stage Cluster BCa Bootstrap, Holm-Bonferroni correction, and `SMOKE_TEST_UNDERPOWERED` flagging.
- Initialized clean repository structure from architecture package (`docs/`, `docs/adr/`).
- Verified local and upstream engineering skill catalog.
