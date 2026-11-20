# 08 — Technology Stack Selection

Every technology choice below is tied to verified November 2026 versions, official repositories, commercial licenses, rejected alternatives, and explicit migration paths. We clearly distinguish **verified facts/official benchmarks** from **theoretical engineering estimates**.

---

## 1. Master Technology Selection Matrix

| Layer | Selected Technology | Official Docs & Repo | License | Verified Version (Nov 2026) | Rejected Alternatives & Why |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend API & Workers** | **Python 3.12+ / FastAPI** | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) · [fastapi/fastapi](https://github.com/fastapi/fastapi) | MIT | `0.165.0` | **Node.js/Express:** Poor native ecosystem for SciPy/statsmodels/Presidio/Pipecat. **Django:** Sync-first ORM friction with streaming async LLM/SSE workloads. **Go:** Faster CPU, but lacks SciPy/Presidio/AI SDK parity for an AI eval engine. |
| **Frontend UI** | **Next.js / React / TypeScript** | [nextjs.org](https://nextjs.org/docs) · [vercel/next.js](https://github.com/vercel/next.js/) | MIT | Next.js `16.4.6` / React `19.3` | **Streamlit/Gradio:** Fast demo, unusable for crisp side-by-side multi-turn diffing, SSE streaming, or multi-tenant SaaS UI. **Vue/Svelte:** Smaller hiring/ecosystem overlap with Huvo's React stack. *(Note: pin `>=16.4.1` for patched RSC CVE-2026-126187.)* |
| **Primary Database** | **PostgreSQL + `asyncpg` + SQLAlchemy + Alembic** | [postgresql.org](https://www.postgresql.org/docs/release/) · [asyncpg](https://pypi.org/project/asyncpg/) | PostgreSQL / Apache-2.0 / MIT | PG `17.12`/`18.7`, `asyncpg 0.32.0`, `SQLAlchemy 2.1.9`, `Alembic 1.20.1` | **SQLite (WAL 3.54.1):** Single-writer lock blocks concurrent multi-pod SaaS workers (kept only for optional local CLI mode). **MongoDB:** Weak relational aggregation & lacks `FOR UPDATE SKIP LOCKED` + RLS. **ClickHouse:** Premature dual-DB ops for MVP. |
| **Job Orchestration** | **PostgreSQL `FOR UPDATE SKIP LOCKED` (Lease + Fence)** | [PG SELECT Docs](https://www.postgresql.org/docs/current/sql-select.html) | PostgreSQL | Built-in | **Temporal (`1.36.1`):** Best durable engine, but adds cluster ops prematurely (<500 transitions/sec). **Celery (`5.7.0`):** Awkward `asyncio` story. **Dramatiq (`2.2.1`):** LGPL-3.0 + separate broker. |
| **Rate Limiting & SSE Pub/Sub** | **Valkey (Redis-compatible)** | [valkey.io](https://valkey.io/) (drop-in for [Redis 8.10.1](https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/redisce/)) | **BSD-3-Clause** | Valkey `8.x` | **Redis 8.10.1:** Tri-licensed RSALv2/SSPLv1/AGPLv3 can trigger enterprise procurement review; Valkey provides identical Lua atomic token-bucket & Pub/Sub semantics under BSD-3-Clause. |
| **AI Model Abstraction** | **Official SDKs (`openai`, `google-genai`, `groq`) behind custom Protocol** | [openai](https://github.com/openai/openai-python) · [google-genai](https://github.com/googleapis/python-genai) · [groq](https://github.com/groq/groq-python) | Apache-2.0 | `openai 3.54.0`, `google-genai 3.2.0`, `groq 1.7.0` | **LiteLLM (`1.110.0`):** High release churn, large dep tree, MIT vs BerriAI Enterprise ambiguity. **LangChain:** Unnecessary abstraction overhead obscuring raw token/TTFT telemetry. *(Optional: `pydantic-ai-slim 2.70.0` MIT for structured outputs.)* |
| **Evaluation Engine** | **Custom Auditable Python Runner + 3-Tier Graders** | Internal (~250 LOC core) | Proprietary / MIT | v1.0 | **DeepEval (`4.3.4`):** Opaque judge prompts hurt human calibration. **Ragas (`0.4.4`):** Pre-1.0 churn + multi-call cost. **Promptfoo (`0.125.1`):** Node.js runtime mismatch. |
| **Statistical Analysis** | **SciPy + statsmodels** | [docs.scipy.org](https://docs.scipy.org/doc/scipy/) · [statsmodels](https://github.com/statsmodels/statsmodels) | BSD-3-Clause | `scipy 1.18.1`, `statsmodels 0.15.0` | **Custom math / NumPy-only:** High bug risk in BCa bootstrap, exact McNemar, and Holm-Bonferroni edge cases. **R via rpy2:** Extra runtime & container bloat. |
| **Dataset & Offline Analytics** | **Git-Versioned YAML + PG + DuckDB (Parquet)** | [duckdb.org](https://duckdb.org/) · [duckdb/duckdb](https://github.com/duckdb/duckdb) | MIT | `duckdb 2.0.0` | **HuggingFace Datasets:** Overkill for 20–500 structured FSM real-estate YAML scenarios. **ClickHouse:** Unnecessary operational cost below 50M rows. |
| **Voice Integration (Layer 2)** | **Pipecat (Daily)** | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) | BSD-2-Clause | `1.16.0` | **LiveKit Agents (`1.8.13`):** Tighter coupling to LiveKit WebRTC SFU (keep as optional target adapter). **Raw Twilio Media Streams:** High boilerplate for frame tapping. |
| **PII & Security** | **Microsoft Presidio + Cloud KMS** | [microsoft/presidio](https://github.com/microsoft/presidio) | MIT | Active 2026 | **Regex-only scrubber:** Misses Indian buyer names/addresses in Hinglish prose. **External PII API:** Violates DPDP in-VPC redaction goal. |
| **Observability** | **OpenTelemetry Python SDK + `structlog`** | [opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python) | Apache-2.0 | `opentelemetry-sdk 1.45.2` | **Vendor-locked SDKs (Langfuse/Datadog-only):** Lock-in; OTel exports natively to Langfuse v4, MLflow 3.18, Grafana Tempo, and Jaeger. |
| **Testing** | **pytest + Hypothesis** | [docs.pytest.org](https://docs.pytest.org/) · [hypothesis](https://github.com/hypothesisworks/hypothesis) | MIT / MPL-2.0 | `pytest 9.x`, `Hypothesis 6.170.15` | **unittest:** Verbose, lacks fixtures and property-based shrinking for Indian currency/FSM invariants. |
| **Deployment** | **Docker Compose (Local/MVP) -> Cloud Containers (`ap-south-1`) + GitHub Actions** | [docs.docker.com](https://docs.docker.com/) | Apache-2.0 | Standard | **Kubernetes (EKS/GKE) on Day 1:** Unnecessary control-plane cost and YAML ops for a 2–4 container MVP. |

---

## 2. Official Benchmarks vs. Theoretical Estimates (Explicit Separation)

* **Verified External Facts / Official Benchmarks:**
  * Pipecat Smart Turn v3.2 executes in **12 ms on modern CPU** (~60–65 ms cloud CPU) across 23 languages ([Daily Blog, Jan 7, 2026](https://www.daily.co/blog/smart-turn-v3-2-handling-noisy-environments-and-short-responses/)).
  * LiveKit Turn Detector v1.0 achieves **9.9% false-cutoff at 300 ms** and **4.5% at 600 ms** on `eot-bench` ([LiveKit, Jun 17, 2026](https://livekit.com/blog/solving-end-of-turn-detection)).
  * Twilio ConversationRelay benchmarks end-to-end voice latency at **p50 491 ms / p95 713 ms** ([Twilio Blog, Nov 17, 2025](https://www.twilio.com/en-us/blog/developers/best-practices/guide-core-latency-ai-voice-agents)).
  * SQLite `3.53.x` fixed a WAL-reset corruption bug; local CLI mode must pin `>=3.54.1` ([SQLite Release Log, Oct 16, 2026](https://sqlite.org/releaselog/3_54_1.html)).
* **Theoretical Engineering Estimates (Must Be Benchmarked in Implementation):**
  * PostgreSQL `FOR UPDATE SKIP LOCKED` queue comfortably sustaining **500–2,000 job state transitions/sec** before MVCC/autovacuum pressure requires Temporal.
  * Tier 1 smoke run ($N=20$, 40 conversations, 8 turns) completing in **<90 seconds** at 10-way async concurrency (dominated by external LLM provider TTFT/tokens-per-sec, not PropEval CPU).
  * Layer 1 deterministic grader executing in **<50 ms p95** per conversation.

---

## 3. Integration & Migration Paths

* **Queue Migration (`SKIP LOCKED` $\to$ Temporal):** Because `engine/worker.py` delegates job lifecycle strictly through `storage/queue.py`, migrating to `temporalio 1.36.1` requires wrapping `run_hybrid_simulation` and `evaluate_conversation` as Temporal Activities with zero changes to `evaluation/`, `stats/`, or `api/` contracts.
* **Analytics Migration (PG $\to$ DuckDB/ClickHouse):** `eval_runs`, `conversation_turns`, and `assertion_results` use typed relational columns so a nightly Parquet export feeds DuckDB `2.0.0` immediately—and can stream into ClickHouse MergeTree if cross-run analytics exceed 50M rows.
* **Provider Migration:** Adding Anthropic, Sarvam AI, or a local vLLM endpoint requires implementing one 50-line `LLMProvider` adapter without touching simulation, grading, or billing ledger logic.
