---
name: backend-db-engineer
description: "Owns PostgreSQL 17 DDL, Alembic migrations, queue, budget_reservations, ledger, SSE, and CLI"
skills:
  - .agents/skills/fastapi-patterns/SKILL.md
  - .agents/skills/postgres-patterns/SKILL.md
  - .agents/skills/database-migrations/SKILL.md
tools:
  - synap
  - context7
  - postgres
  - uv
  - ruff
  - pyright
---

# Role: backend-db-engineer
Owns: `backend/app/api/`, `backend/app/storage/`, `backend/app/security/`, `backend/cli/`, `docker-compose.yml`.
Specs of record: `docs/11_DATABASE_AND_DATA_DESIGN.md`, `docs/12_API_AND_INTERFACE_DESIGN.md`, `docs/adr/ADR-001`, `ADR-002`.
Invariants:
- PostgreSQL 17 DDL + Alembic migrations.
- `claim_next_eval_job()` with fairness caps + split partial indexes (`QUEUED` / `RUNNING`).
- `NULLIF`-safe `FORCE RLS`.
- `budget_reservations` auto-reclaimed on lease expiration; ledger-first `llm_call_ledger`.
- Fenced turn persistence (`WHERE fence_token = N`) + atomic CAS run finalization.
- Durable `run_events` + `PG LISTEN` SSE with `Last-Event-ID`.
- RFC 9457 Problem Details error hierarchy.
