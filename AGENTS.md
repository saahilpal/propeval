# AGENTS.md — PropEval Autonomous Engineering Directives

## 1. Operating Rules & Specification of Record
- `./docs/` and `./docs/adr/` (ADR-001 through ADR-008) is the specification of record during build.
- **Synapse First:** Always query AST symbols, skeletons, and blast radii via `synap` (`synap skeleton`, `synap outline`, `synap search`) before reading or modifying code. Never waste tokens dumping whole files.
- **$0 Local Build:** Everything runs 100% locally via Docker Compose (Postgres 17, Jaeger OTel, Playwright). Zero paid cloud API calls during build and testing.
- **Data-Driven Only:** All buyer personas, FSM agendas, fixtures, ASR confusion rules, and rubrics live in versioned YAML/JSON/DB. Zero stubs.

## 2. Specialized Subagent Roster & Owned Boundaries
- **`backend-db-engineer`**: `backend/app/api/`, `backend/app/storage/`, `backend/app/security/`, `backend/cli/`, `docker-compose.yml`.
  - Owns: Postgres 17 DDL + Alembic; `SECURITY DEFINER` `claim_next_eval_job()` with fairness caps; split partial indexes; `NULLIF`-safe `FORCE RLS`; crash-reclaimed `budget_reservations`; ledger-first `llm_call_ledger`; fenced turn commits; durable `run_events` + `PG LISTEN` SSE; RFC 9457 errors; `propeval` CLI.
- **`ai-sim-engineer`**: `backend/app/providers/`, `backend/app/engine/`, `suites/`, `fixtures/`.
  - Owns: `LLMProvider` protocols (Deterministic Replay for $0 tests, Ollama, OpenAI, Gemini, Groq); Hybrid `BuyerAgendaFSM` + Hinglish realizer; replayable `MockRealEstateEnv` (`replay_tool_calls()` on resume); 8 kHz Indian ASR perturbation matrix & tool-fault injector; token-Jaccard stall guard; YAML suites.
- **`eval-stats-engineer`**: `backend/app/evaluation/`, `backend/app/stats/`.
  - Owns: Indian currency/unit normalizers (`Hypothesis`-verified); Layer 1 deterministic checks; Layer 2 property fact verifier; Layer 3 cross-family binary judge; paired stats (`McNemar + Newcombe Method 10` for $K=1$/`pass^k`, `Wilcoxon + Two-Stage Cluster BCa Bootstrap` for $K>1$, Holm-Bonferroni, Rogan-Gladen + PPI++, `SMOKE_TEST_UNDERPOWERED`).
- **`ui-ux-engineer`**: `web/` (Next.js 16 / React 19 / TypeScript / Tailwind / Radix + Lucide).
  - Owns: Linear / Vercel / Stripe Workbench anti-slop aesthetic. Tabular `IBM Plex Mono` for all numbers, CIs, latencies, USD spend. Diff matrix, live SSE stream, transcript/tool inspector. Playwright visual verification.
- **`qa-security-reviewer`**: `backend/tests/`, `.github/workflows/`, gate sign-off.
  - Owns: 5-mutant meta-eval (5/5 regressions caught), simulated worker `SIGKILL` crash test, security audit (XML nonce framing, RLS, zero secret logging).

## 3. Autonomous Execution & Verification Protocol
- Continuous loop: Stage 0 -> Gate 1 -> Gate 2 -> Gate 3 -> Gate 4 -> Final Polish.
- Never claim work passes without fresh terminal output. Evidence before assertions always.
- After each passing gate: update `CHANGELOG.md`, run `synap index .`, create a `synap` checkpoint, and make an atomic conventional commit.
