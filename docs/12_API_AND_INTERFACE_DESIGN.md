# 12 — API & Interface Design

PropEval exposes a versioned REST + SSE Control Plane (`/api/v1/*`) and a thin Python CLI (`propeval`) calling the exact same endpoints. All mutating `POST` endpoints support the [IETF `Idempotency-Key` header draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/) backed by `http_idempotency_keys`, and all errors conform to **RFC 9457 Problem Details**.

---

## 1. Complete Endpoint Catalog

| Method & Path | Purpose | Auth & Headers | Status Codes |
| :--- | :--- | :--- | :--- |
| `POST /api/v1/prompts` | Register immutable prompt version (deduped by SHA-256) | `Bearer <API_KEY>`, `Idempotency-Key` | `201`, `200`, `422` |
| `POST /api/v1/fixtures` | Upload versioned real-estate project truth fixture | `Bearer <API_KEY>`, `Idempotency-Key` | `201`, `422` |
| `POST /api/v1/suites` | Register stratified YAML/JSON scenario suite | `Bearer <API_KEY>`, `Idempotency-Key` | `201`, `422` |
| `POST /api/v1/replay/import` | Import production transcripts (in-VPC Presidio PII redactor) | `Bearer <API_KEY>`, `Idempotency-Key` | `201`, `422` |
| `POST /api/v1/runs` | Launch paired V1 vs V2 evaluation run with budget cap | `Bearer <API_KEY>`, `Idempotency-Key` | `202`, `400`, `422` |
| `GET /api/v1/runs/{run_id}/stream` | Durable SSE stream backed by `run_events` (`Last-Event-ID` resumable) | `Bearer <API_KEY>`, `Last-Event-ID` | `200` (`text/event-stream`) |
| `GET /api/v1/runs/{run_id}/diff` | Retrieve paired statistical diff, hard-gate verdicts & cost | `Bearer <API_KEY>` | `200`, `404` |
| `GET /api/v1/runs/{run_id}/jobs/{job_id}` | Inspect turn-by-turn transcript, tool trace & failed assertions | `Bearer <API_KEY>` | `200`, `404` |
| `POST /api/v1/runs/{run_id}/resume` | Resume `BUDGET_EXCEEDED` / partial run with updated cap | `Bearer <API_KEY>`, `Idempotency-Key` | `202`, `409` |
| `POST /api/v1/runs/{run_id}/dlq/replay` | Requeue `DEAD_LETTERED` jobs after fixing webhook/credentials | `Bearer <API_KEY>`, `Idempotency-Key` | `202`, `404` |
| `POST /api/v1/calibration/evaluate` | Compute & persist Cohen's $\kappa$, Fail-P/R & TPR/TNR in `judge_calibrations` | `Bearer <API_KEY>` | `200`, `422` |
| `DELETE /api/v1/tenants/{tenant_id}` | Cascading tenant hard-delete + KMS DEK erasure (DPDP Section 12) | `Bearer <ADMIN_KEY>` | `202`, `403` |

---

## 2. Key Request & Response Contract Examples

### `POST /api/v1/runs` (3-Way Cross-Family Isolation Enforced)
Notice all three roles use **independent model families** (`google` Simulator, `openai` Target, `groq`/Llama Judge):
```json
{
  "baseline_prompt_id": "2f9c0a1e-8c1a-4b2e-9a11-111111111111",
  "candidate_prompt_id": "7b4e1d2f-3a4b-4c5d-8e22-222222222222",
  "suite_id": "9a1b2c3d-4e5f-4a6b-9c33-333333333333",
  "fixture_id": "5d6e7f8a-9b0c-4d1e-8f44-444444444444",
  "trials_k": 3,
  "random_seed": 20261119,
  "max_budget_usd": 4.50,
  "simulator_model_id": "gemini-2.5-flash",
  "judge_model_id": "llama-3.3-70b-versatile"
}
```
**Response (`202 Accepted`):**
```json
{
  "run_id": "c0ffee00-1234-4567-89ab-cdef01234567",
  "status": "QUEUED",
  "suite_tier": "release_gate",
  "total_jobs": 300,
  "max_budget_usd": 4.50,
  "stream_url": "/api/v1/runs/c0ffee00-1234-4567-89ab-cdef01234567/stream"
}
```

### `GET /api/v1/runs/{run_id}/diff` (Mathematically Consistent $K=3$ Paired Output)
When `trials_k > 1`, continuous per-scenario pass rates use **Paired Wilcoxon + Two-Stage Cluster BCa Bootstrap**, while binary `pass_pow_3` (did all 3 trials pass for scenario $i$?) uses **Exact McNemar + Newcombe Paired Wilson CI**. Quarantined scenarios drop *both* paired arms (`effective_paired_scenarios: 48`, denominator `144` trials):
```json
{
  "run_id": "c0ffee00-1234-4567-89ab-cdef01234567",
  "status": "REGRESSED",
  "suite_tier": "release_gate",
  "n_scenarios": 50,
  "trials_k": 3,
  "quarantined_simulator_faults": 2,
  "effective_paired_scenarios": 48,
  "effective_trials_per_arm": 144,
  "hard_gates": {
    "dnc_compliance": {"v1_pass_trials": 144, "v2_pass_trials": 140, "status": "FAIL_REGRESSION"},
    "no_invented_actions": {"v1_pass_trials": 144, "v2_pass_trials": 142, "status": "FAIL_REGRESSION"},
    "rera_fact_grounding": {"v1_pass_trials": 144, "v2_pass_trials": 144, "status": "PASS"},
    "metamorphic_currency_invariance": {"v1_pass_pairs": 10, "v2_pass_pairs": 9, "status": "FAIL_REGRESSION"}
  },
  "statistical_metrics": {
    "task_completion_primary": {
      "v1_mean_rate": 0.840, "v2_mean_rate": 0.778, "mean_diff": -0.062,
      "wilcoxon_p": 0.084, "cluster_bca_95_ci": [-0.131, 0.009],
      "pass_pow_3": {
        "v1": 0.708, "v2": 0.604, "mcnemar_exact_p": 0.125, "newcombe_95_ci": [-0.214, 0.018]
      },
      "statistically_significant": false
    },
    "slot_extraction_f1": {
      "v1_mean": 0.910, "v2_mean": 0.860, "wilcoxon_p": 0.012,
      "holm_adjusted_p": 0.036, "rank_biserial_r": -0.41, "cluster_bca_95_ci": [-0.088, -0.014]
    },
    "hinglish_tone_rubric": {
      "calibration_status": "CALIBRATED", "cohens_kappa": 0.78,
      "v1_rogan_gladen_rate": 0.880, "v2_rogan_gladen_rate": 0.910
    }
  },
  "cost_and_latency": {
    "v1_p95_ttft_ms": 480, "v2_p95_ttft_ms": 545, "total_run_cost_usd": 2.84
  }
}
```

### `GET /api/v1/runs/{run_id}/stream` (Durable SSE Wire Format via `run_events`)
Supports all five canonical event types (`job.completed`, `job.quarantined`, `run.budget_halted`, `run.early_aborted`, `run.completed`). On reconnect with `Last-Event-ID: 41`, FastAPI queries `SELECT * FROM run_events WHERE run_id = $1 AND event_id > 41 ORDER BY event_id ASC` before subscribing to `PG LISTEN`:
```text
id: 41
event: job.completed
data: {"job_id":"...","scenario_id":"hinglish_budget_switch_04","prompt_role":"candidate","hard_gate_pass":false,"failed_checks":["dnc_compliance"]}

id: 42
event: run.budget_halted
data: {"run_id":"c0ffee00-...","spent_usd":4.49,"max_budget_usd":4.50}

id: 43
event: run.completed
data: {"run_id":"c0ffee00-...","status":"REGRESSED","exit_code":1}
```

---

## 3. Standardized Error Contract (RFC 9457)

```json
{
  "type": "https://propeval.dev/errors/cross-family-violation",
  "title": "Simulator, target, and judge must use independent model families",
  "status": 422,
  "detail": "Target uses 'openai', simulator uses 'google'; judge cannot reuse 'openai' or 'google'. Select an independent family (e.g., 'groq' / 'anthropic').",
  "instance": "/api/v1/runs",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736"
}
```

---

## 4. CLI CI/CD Contract (`propeval`)

```bash
propeval run \
  --baseline prompt_v1.yaml \
  --candidate prompt_v2.yaml \
  --suite suites/hinglish_smoke_20.yaml \
  --fixture fixtures/lodha_wakad_2026_11.yaml \
  --trials 1 \
  --max-budget-usd 1.50 \
  --gate   # Exits 0 on PASSED or INCONCLUSIVE_UNDERPOWERED (with warning); exits 1 on REGRESSED / BUDGET_EXCEEDED
```
