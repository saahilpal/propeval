# Changelog

All notable changes to PropEval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
