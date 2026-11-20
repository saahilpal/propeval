# 05 — Non-Functional Requirements

Every NFR specifies a measurable target, measurement mechanism, and architectural enforcement point.

## 1. Performance & Latency
* **NFR-01 (Control-Plane API Latency):** `POST /api/v1/runs`, `GET /api/v1/runs/{id}/diff`, and registry reads must achieve **p95 < 150 ms** and **p99 < 400 ms** under 50 concurrent API users (enforced via indexed relational columns, never scanning JSONB blobs for summary aggregations).
* **NFR-02 (End-to-End CI Smoke Run Wall Time):** A Tier 1 PR smoke gate ($N=20$ paired scenarios = 40 conversations, $K=1$, max 8 turns) must complete in **< 90 seconds p95** with 10 concurrent async workers (bounded primarily by external LLM provider latency).
* **NFR-03 (SSE Update Delivery Latency):** Job completion events must reach connected browser clients within **< 500 ms** of PostgreSQL fenced commit via Redis/Valkey Pub/Sub fan-out.
* **NFR-04 (Deterministic Grader Overhead):** Layer 1 deterministic checks (currency normalization, regex, JSON schema, DNC, numeric fact entailment) must execute in **< 50 ms p95 per conversation** on CPU.

## 2. Scalability & Concurrency
* **NFR-05 (Worker Concurrency & Zero Duplicate Execution):** The PostgreSQL `FOR UPDATE SKIP LOCKED` queue must safely support **1 to 10 worker pods** (up to 200 concurrent async coroutines) with **0% double-claimed active jobs** and **0% split-brain commits** (enforced by monotonic `fence_token` CAS updates).
* **NFR-06 (Architecture Ceiling & Scale Trigger):** Option A must sustain up to **500 job state transitions/sec** and **10M historical `conversation_turns` rows** without autovacuum degradation (enforced via partial indexes on active statuses). Crossing 500 transitions/sec or 50M assertion rows triggers migration to Option B (Temporal + ClickHouse).

## 3. Reliability, Fault Tolerance & Cost Control
* **NFR-07 (Worker Crash Recovery):** If a worker pod is `SIGKILL`ed mid-conversation, its lease (`60 s`, renewed every `20 s`) must expire and be reclaimed by another worker within **<= 90 seconds**, resuming from the last persisted turn via `llm_call_ledger` idempotency keys with **0% duplicate LLM billing** on completed turns.
* **NFR-08 (Hard Cost Guarantee):** No evaluation run may exceed `max_budget_usd` by more than a single in-flight LLM call's worst-case `max_tokens` cost (enforced via atomic PostgreSQL `reserved_usd` reservation before every external provider request).
* **NFR-09 (Provider Resilience):** Transient `429`/`5xx` provider errors must be retried with **exponential backoff + full jitter** honoring `Retry-After`, protected by per-provider RPM/TPM token buckets and Closed/Open/Half-Open circuit breakers.

## 4. Statistical & Evaluation Integrity
* **NFR-10 (No False Significance Claims):** The system must mathematically refuse to emit a "statistically significant win" badge when sample size $N < 50$ or when multiple-testing adjusted $p$-value (Holm-Bonferroni) exceeds $\alpha = 0.05$.
* **NFR-11 (Judge Calibration Floor):** Any LLM rubric judge deployed as a warning/gating signal must record a human golden-set **Cohen's $\kappa \ge 0.70$** and **Fail-class Recall $\ge 0.80$**; judges below threshold are flagged `UNCALIBRATED_ADVISORY_ONLY`.
* **NFR-12 (Reproducibility):** Every run must record immutable hashes of `prompt_v1`, `prompt_v2`, `suite_yaml`, `project_fixture`, `grader_prompt_version`, `simulator_model_id`, and `random_seed` so any regression can be reproduced and audited months later.

## 5. Security, Privacy & Indian Regulatory Compliance
* **NFR-13 (DPDP Act 2023 Compliance):** All imported production transcripts must be redacted in-VPC (Mumbai `ap-south-1` / Hyderabad `ap-south-2`) before persistence or outbound LLM calls, achieving **>= 99% recall on Indian 10-digit mobile numbers, PAN, and Verhoeff-valid Aadhaar numbers**. Tenant hard-delete requests (DPDP Section 12) must complete cascading erasure + DEK destruction within **24 hours**.
* **NFR-14 (Secret & Tenant Isolation):** Customer BYOK API keys must be encrypted with per-tenant AES-256-GCM DEKs wrapped by KMS CMKs (`EncryptionContext: tenant_id`) and never appear in logs, OTel spans, or error responses. All tenant-scoped PostgreSQL tables must enforce `FORCE ROW LEVEL SECURITY`.
* **NFR-15 (SSRF Zero-Bypass):** Outbound customer target-agent webhooks must restrict to `https://`, disable `3xx` redirects, pin DNS-resolved public IPs (blocking RFC 1918, loopback, CGNAT, and `169.254.169.254`), and route through a dedicated egress proxy.

## 6. Observability & Maintainability
* **NFR-16 (OpenTelemetry Conformance):** 100% of LLM calls, target webhooks, and eval jobs must emit OpenTelemetry (`1.45.2`) traces conforming to 2026 `gen_ai.*` semantic conventions with `gen_ai.input.messages` disabled by default to prevent PII leakage.
* **NFR-17 (Local Parity & CI Quality):** The entire stack must boot locally with one command (`docker compose up`), run deterministic unit/property tests (`pytest` + `Hypothesis`) in **< 30 seconds** without external API keys, and enforce >= 80% test coverage on core evaluation and statistical modules.
