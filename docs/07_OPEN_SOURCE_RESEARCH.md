# 07 — Open-Source Technology Research

All repositories, licenses, versions, and maintenance statuses below were verified directly as of **November 2026**. Rather than defaulting to popular AI frameworks, every project is audited on architecture, licensing risk, dependency weight, and **Adopt vs. Wrap/Integrate vs. Build Custom** fit for PropEval.

---

## 1. LLM Evaluation & Observability Ecosystem Audit

| Project | Verified Repo & Docs | License | Verified Version (Nov 2026) | Architecture & Strengths | Limitations & Commercial Risks | PropEval Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenTelemetry (Python)** | [opentelemetry-python](https://github.com/open-telemetry/opentelemetry-python), [PyPI](https://pypi.org/project/opentelemetry-sdk/) | **Apache-2.0** | `opentelemetry-sdk 1.45.2` (Oct 29, 2026) | CNCF graduated; OTLP wire standard + 2026 `gen_ai.*` semantic conventions ([OTel GenAI](https://opentelemetry.io/blog/2026/genai-observability/)). | Plumbing only (no storage or eval engine). | **ADOPT** — Never reinvent trace propagation or OTLP export. |
| **Langfuse** | [langfuse/langfuse](https://github.com/langfuse/langfuse), [PyPI](https://pypi.org/project/langfuse/) | **MIT** core; commercial **`ee/LICENSE`** (ClickHouse, Inc.) | Platform `v4.81.0`; Python SDK `5.2.0` | Built on OTel + ClickHouse + Postgres + Redis + Next.js; polished trace UI. | Self-hosting v4 requires ClickHouse ops; enterprise features (SSO, external media) sit under `ee/LICENSE`. | **INTEGRATE via OTLP** — Do not adopt as PropEval's core DB/backend. |
| **Promptfoo** | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo), [npm](https://www.npmjs.com/package/promptfoo?activeTab=readme) | **MIT** | `0.125.1` (Oct 2026; active Nov releases) | Node.js/TypeScript CLI (Node 24+), YAML eval matrices, strong red-teaming & GH Action scanning. | Node.js runtime clashes with Python async/SciPy workers (`promptfoo-python` shells out to `npx`). | **BUILD CUSTOM core; optional YAML/red-team adapter** |
| **DeepEval** | [confident-ai/deepeval](https://github.com/confident-ai/deepeval), [Docs](https://deepeval.com/) | **Apache-2.0** | `4.3.4` (Nov 12, 2026) | Pytest-style Python unit tests with G-Eval, hallucination, and task-completion judges. | Opaque built-in judge prompts hinder Rogan–Gladen/human calibration, cost control, and paired diffing. | **BUILD CUSTOM core** (optional plugin protocol only) |
| **Ragas** | [vibrantlabsai/ragas](https://github.com/vibrantlabsai/ragas), [PyPI](https://pypi.org/project/ragas/) | **Apache-2.0** | `0.4.4` (Nov 13, 2026; patched `CVE-2026-6587`) | RAG-specific faithfulness/relevancy metrics and synthetic testset generators. | Pre-1.0 (`0.4.x`) breaking API churn; expensive multi-call-per-row LLM cost; RAG-centric. | **BUILD CUSTOM core** (transparent single-call grounding check) |
| **DSPy** | [stanfordnlp/dspy](https://github.com/stanfordnlp/dspy), [PyPI](https://pypi.org/project/dspy/) | **MIT** | `3.5.0` (Nov 10, 2026) | Declarative Signatures, Modules, and automated prompt/program optimizers. | Compiled/mutated prompts work against auditable, immutable regression harnesses. | **WRAP LATER** (optional automated prompt-optimizer worker) |
| **MLflow** | [mlflow/mlflow](https://github.com/mlflow/mlflow), [PyPI](https://pypi.org/project/mlflow/) | **Apache-2.0** | `3.18.0` (Nov 2026) | Full ML lifecycle server with OTel-compatible `mlflow-tracing` and `LoggedModel` versioning. | Heavy classical-ML server footprint. | **INTEGRATE via OTLP export** (enterprise target only) |

---

## 2. Voice AI, Model Abstraction & Core Infrastructure Audit

| Project | Verified Repo | License | Verified Version (Nov 2026) | Key Architectural Takeaway | PropEval Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pipecat (Daily)** | [pipecat-ai/pipecat](https://github.com/pipecat-ai/pipecat) | **BSD 2-Clause** | `1.16.0` | Transport-agnostic async frame pipeline (`VAD/STT -> LLM -> TTS`); includes `pipecat.flows` and open-source Smart Turn v3.2. | **ADOPT for Layer-2 Audio Replay** (zero SFU lock-in) |
| **LiveKit Agents** | [livekit/agents](https://github.com/livekit/agents) | **Apache-2.0** (audit plugins: [#6192](https://github.com/livekit/agents/issues/6192)) | `1.8.13` (Nov 18, 2026) | Worker-pool runtime tightly integrated with LiveKit Go WebRTC SFU & SIP; Turn Detector v1.0. | **Optional target adapter** for LiveKit-hosted customer agents |
| **LiteLLM** | [BerriAI/litellm](https://github.com/BerriAI/litellm) | **MIT** core / **BerriAI Enterprise** (`enterprise/`) | `1.110.0` | 100+ provider proxy moving to Rust core; high churn and license-boundary ambiguity ([Issue #34241](https://github.com/BerriAI/litellm/issues/34241)). | **REJECT as hard core dep** (allow as optional BYO gateway URL) |
| **PydanticAI** | [pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) | **MIT** | `2.70.0` (Nov 17, 2026) | Typed Pydantic v2 structured outputs + OTel; lightweight `pydantic-ai-slim` package. | **Optional** if unified multi-provider structured output is needed |
| **Official SDKs** (`openai`, `google-genai`, `groq`) | [openai](https://github.com/openai/openai-python), [google-genai](https://github.com/googleapis/python-genai), [groq](https://github.com/groq/groq-python) | **Apache-2.0** | `openai 3.54.0`, `google-genai 3.2.0`, `groq 1.7.0` | Zero abstraction lag on structured outputs, native `httpx2` async clients, exact token/finish-reason metadata. | **ADOPT behind thin 120-line `LLMProvider` Protocol** |
| **SciPy & statsmodels** | [scipy](https://github.com/scipy/scipy), [statsmodels](https://github.com/statsmodels/statsmodels) | **BSD-3-Clause** | `scipy 1.18.1`, `statsmodels 0.15.0` | Exact McNemar, Wilcoxon, BCa bootstrap, Holm-Bonferroni, BH-FDR, Cohen's $\kappa$. | **ADOPT (Mandatory)** — Never hand-roll statistical tests |
| **DuckDB** | [duckdb/duckdb](https://github.com/duckdb/duckdb) | **MIT** | `2.0.0` (Oct 21, 2026) | In-process columnar OLAP over Parquet; eliminates ClickHouse ops for offline failure clustering. | **ADOPT for offline analytics / Parquet slicing** |
| **Temporal** | [temporalio/temporal](https://github.com/temporalio/temporal) | **MIT** | Server `v1.32.2`; Python SDK `1.36.1` | Best-in-class durable execution for long-running DAGs, at the cost of operating Temporal Server. | **DEFER to Scale Trigger** (>500 transitions/sec or multi-day HITL) |
| **Redis / Valkey** | [redis/redis](https://github.com/redis/redis/releases) | **RSALv2 / SSPLv1 / AGPLv3** (Valkey: **BSD-3-Clause**) | Redis `8.10.1` | Fast atomic Lua RPM/TPM token buckets & SSE Pub/Sub; AGPLv3/SSPLv1 triggers enterprise procurement review if modified/distributed. | **ADOPT Valkey (BSD-3-Clause)** as drop-in Redis-compatible layer |
| **Microsoft Presidio** | [microsoft/presidio](https://github.com/microsoft/presidio) | **MIT** | Active 2026 | Extensible in-VPC PII analyzer/anonymizer supporting custom Indian PAN/Aadhaar Verhoeff recognizers. | **ADOPT** for DPDP Act 2023 redaction |

---

## 3. Core Build-vs-Adopt Principle for PropEval

1. **Adopt mature, boring, permissively licensed primitives** where correctness is hard and commoditized: OpenTelemetry (`1.45.2`), SciPy (`1.18.1`), statsmodels (`0.15.0`), Hypothesis (`6.170.15`), Presidio, PostgreSQL (`17/18`), official LLM SDKs, and Pipecat (`1.16.0` for Layer 2).
2. **Build custom where PropEval's product value and auditability live** (~250 lines of clean Python): the Hybrid FSM+LLM Hinglish Simulator, the Indian currency/RERA deterministic verifier, the versioned calibrated rubric judge, the `FOR UPDATE SKIP LOCKED` lease/fence queue, and the atomic USD budget circuit breaker.
