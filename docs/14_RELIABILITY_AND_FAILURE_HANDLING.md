# 14 — Reliability & Failure Handling

Evaluating multi-turn voice agents orchestrates hundreds of external LLM APIs and customer webhooks in parallel. PropEval is engineered so that **no crash, rate limit, or runaway loop can corrupt results, leak budget reservations, or leave runs stuck**.

---

## 1. Failure Mode & Recovery Matrix

| Failure Mode | Detection Mechanism | Automated Recovery Strategy | Data / Cost Guarantee |
| :--- | :--- | :--- | :--- |
| **Worker pod `SIGKILL` / OOM mid-call** | `eval_jobs.lease_expires_at < now()` (60 s lease, 20 s heartbeat, 300 s hard job wall cap) | `claim_next_eval_job()` reclaims job, increments `fence_token`, releases orphaned `budget_reservations`, loads persisted `conversation_turns`, replays prior `tool_calls` into `MockRealEstateEnv`, and resumes at `MAX(turn_index) + 1`. | **0% duplicate billing on already-persisted completed turns** (at most 1 in-flight turn if crash occurs between provider billing and DB commit). |
| **Zombie worker wakes after GC/network pause** | Fenced writes (`WHERE id = $1 AND fence_token = $2`) return `0` rows | Zombie worker aborts both turn writes and job completion, logging `lease.fenced_out`. | **0% split-brain corruption**. |
| **Provider HTTP `429` / `502` / `503` / `504`** | HTTP status + `Retry-After` header ([RFC 6585](https://www.rfc-editor.org/info/rfc6585/)) | Honor `Retry-After` if present; else **Exponential Backoff with Full Jitter** (`random(0, min(cap, base * 2^attempt))`; [AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)). | Prevents thundering herd across worker pods. |
| **Sustained provider or customer webhook outage** | Sliding window >50% errors over 20 calls or 10 consecutive failures | **Circuit Breaker** ([Fowler](https://martinfowler.com/bliki/CircuitBreaker.html)) trips `OPEN` for 30 s cool-down, then probes in `HALF_OPEN`. Jobs defer via `run_after`. | Isolates blast radius per `(provider, model)` and per webhook host. |
| **Slowloris customer webhook** | Hard 5 s connect, 30 s read, and **45 s total wall-clock timeout** per turn | Aborts socket cleanly so heartbeat cannot keep a hung job alive indefinitely. | Protects worker concurrency pool. |
| **Runaway multi-turn simulator loop** | (1) `turn_index >= max_turns`; (2) 3-turn token Jaccard >0.85 stall guard; (3) `budget_reservations` check fails | Loop detector terminates case; budget failure trips `eval_runs.status = 'BUDGET_EXCEEDED'`, cancels queued jobs, writes `run.budget_halted` to `run_events`. | Hard spend ceiling guaranteed across simulator, target, auditor, and judge calls. |
| **Non-retryable error (`400`, `401`) or `attempt >= 5`** | HTTP `4xx` (excl. `408`/`429`) or retry exhaustion | Transition job to `DEAD_LETTERED` with `last_error_code` + `last_error_detail`; replay via `POST /api/v1/runs/{run_id}/dlq/replay`. | Zero infinite retry loops. |
| **Buyer simulator violates FSM / persona** | Deterministic FSM transition check + `SimulatorFidelityAuditor` | Transition job to `QUARANTINED_SIM_FAULT`; paired counterpart excluded from paired stats (`effective_paired_scenarios` reported). | Prevents simulator noise from falsely failing Prompt V2. |

---

## 2. Per-Call `budget_reservations` (Zero Crash Leaks & Low Contention)

Instead of mutating a single `reserved_usd` counter on `eval_runs` (which leaks permanently on worker `SIGKILL` and creates a hot row lock), PropEval tracks active reservations in `budget_reservations`:
1. **Ledger-First Check:** Always check `llm_call_ledger` for a completed response *before* reserving budget so resumed turns cost `$0`.
2. **Scoped Reservation (covers Simulator, Target, Auditor, and Judge):** Inside a short transaction guarded by an advisory lock on `hashtext(run_id::text)`, check:
   ```sql
   SELECT (r.spent_usd + COALESCE(SUM(b.reserved_usd), 0) + $est) <= r.max_budget_usd
   FROM eval_runs r
   LEFT JOIN budget_reservations b ON b.run_id = r.id AND b.status = 'ACTIVE'
   WHERE r.id = $run_id AND r.status IN ('QUEUED', 'RUNNING')
   GROUP BY r.id;
   ```
   If true, insert `budget_reservations (run_id, job_id, fence_token, reserved_usd, status='ACTIVE')`.
3. **Settlement or Crash Reclamation:** On response, mark the reservation `SETTLED` and add `actual_cost_usd` to `eval_runs.spent_usd`. If the worker crashes, `claim_next_eval_job()` automatically marks all `ACTIVE` reservations from the dead `fence_token` as `RELEASED`—guaranteeing **zero permanent budget leaks**.

---

## 3. Dual RPM + TPM Rate Limiting & Partial Run Resumption

* **Rate Limiting:** For multi-pod production, a Valkey (`8.x`, BSD-3-Clause) atomic Lua script enforces dual RPM + TPM buckets keyed by `(provider, model_id, api_key_hash)` with post-call unused-token refund. (Single-pod MVP can run the identical interface in-process via `asyncio`.)
* **Partial Run Resumption:** Calling `POST /api/v1/runs/{run_id}/resume` (with an updated `max_budget_usd`) requeues only incomplete jobs. Completed turns replay from `conversation_turns` and `llm_call_ledger` at **$0 additional LLM cost**, while `MockRealEstateEnv.replay_tool_calls()` reconstructs exact mock CRM/inventory state before Turn `t+1`.
