# 15 — Observability & Deployment

## 1. OpenTelemetry Instrumentation (2026 `gen_ai.*` Semantic Conventions)

PropEval adopts the **OpenTelemetry Python SDK (`1.45.2`)** aligned with the 2026 [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/blog/2026/genai-observability/) and [GenAI Agent Spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md):

* **Trace Hierarchy:**
  * Root Span: `eval.run` (`propeval.run_id`, `propeval.suite_tier`, `propeval.trials_k`)
  * Child Span (per job): `invoke_agent <target_prompt_version>` (`propeval.scenario_id`, `propeval.prompt_role`, `propeval.fence_token`)
  * Leaf Spans (per LLM call): `{gen_ai.operation.name} {gen_ai.request.model}` carrying `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.finish_reasons`, and `propeval.role` (`simulator` | `target` | `judge` | `auditor`).
* **Privacy-by-Default Telemetry:** `gen_ai.input.messages` and `gen_ai.output.messages` are **disabled by default** in production exports so Indian buyer PII never leaks into external APM backends.
* **Vendor Neutrality:** Standard OTLP export connects seamlessly to Grafana Tempo, Jaeger, [Langfuse v4](https://github.com/langfuse/langfuse), or [MLflow 3.18](https://mlflow.org/docs/latest/genai/tracing/).

---

## 2. Structured Logging & Low-Cardinality Metrics

* **Structured JSON Logs (`structlog`):** Every log line includes `timestamp`, `severity_text`, `trace_id`, `span_id`, `tenant_id`, `run_id`, `job_id`, `fence_token`, and `event` (`lease.expired`, `lease.fenced_out`, `circuit_breaker.opened`, `budget.halted`, `sim.quarantined`). A mandatory scrubber strips `Authorization`, `x-api-key`, and unredacted phone/PAN/Aadhaar patterns.
* **Core OTel Metrics (strictly low-cardinality labels — NEVER put `tenant_id` or `run_id` in metric labels):**
  * `gen_ai.client.operation.duration` (histogram, seconds; sliced by `gen_ai.request.model`, `propeval.role`)
  * `gen_ai.client.token.usage` (histogram, tokens; sliced by `gen_ai.token.type`, `gen_ai.request.model`)
  * `propeval.queue.claim_lag_seconds` (histogram — primary autoscaling signal for worker pods)
  * `propeval.run.cost_usd` (counter/histogram)
  * `propeval.target_webhook.duration` (histogram; sliced by `http.response.status_code`)

---

## 3. Deployment Architecture & CI/CD Integration

### Local Development & MVP (`docker-compose.yml` — Zero Valkey Required in MVP)
Single-command parity booting four containers:
1. `api` (FastAPI `0.165.0` + Uvicorn + durable `run_events` SSE via `PG LISTEN`)
2. `worker` (Async Eval Worker + Lease Reaper, scalable via `--scale worker=4`)
3. `web` (Next.js `16.4.6` / React `19.3`)
4. `postgres` (PostgreSQL `17.12` with Alembic `1.20.1` migrations + RLS init)

### Production Cloud Topology (`ap-south-1` Mumbai — Phase 2 Multi-Pod)
* **Compute:** Managed container runtime (AWS ECS Fargate / Cloud Run) running `api` (2 replicas behind TLS 1.3 ALB) and `worker` (2–10 replicas autoscaled on `propeval.queue.claim_lag_seconds > 5 s`).
* **Data:** Managed PostgreSQL `17.12` Multi-AZ primary + read replica; Managed Valkey `8.x` (BSD-3-Clause) for cross-pod dual RPM/TPM token buckets; Cloud KMS CMK; dedicated SSRF-hardened egress subnet (Envoy/Smokescreen + IMDSv2).
* **Analytics:** Nightly Parquet export to encrypted S3 (`ap-south-1`) queried via **DuckDB `2.0.0`** for cross-run failure clustering and **EWMA / $p$-chart SPC** drift alerts.

### GitHub Actions CI/CD Gate (Exact Canonical CLI Flags)
* **On Every Prompt PR (`Tier 1 Smoke`):**
  ```bash
  propeval run --baseline prompt_v1.yaml --candidate prompt_v2.yaml \
    --suite suites/hinglish_smoke_20.yaml --fixture fixtures/lodha_wakad_2026_11.yaml \
    --trials 1 --max-budget-usd 1.50 --gate
  ```
* **Nightly / Pre-Release (`Tier 2 Release Gate`):**
  ```bash
  propeval run --baseline prompt_v1.yaml --candidate prompt_v2.yaml \
    --suite suites/hinglish_release_100.yaml --fixture fixtures/lodha_wakad_2026_11.yaml \
    --trials 3 --max-budget-usd 12.00 --gate
  ```
