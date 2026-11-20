# Changelog

All notable changes to PropEval will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
