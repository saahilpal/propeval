# 02 — High-Level Design (HLD)

## 1. System Overview & Architectural Style

PropEval is designed as a **Modular Monolith with a PostgreSQL Transactional Job Queue (`FOR UPDATE SKIP LOCKED` + Lease/Fence Tokens) and Durable Server-Sent Events (SSE) Streaming**, accompanied by a thin CLI client for CI/CD regression gating.

* **Why this style (summary of [`ADR-001`](./adr/ADR-001-modular-monolith-vs-microservices-vs-cli.md)):** PropEval's workload is I/O-bound, high-latency (2–45 s per multi-turn LLM interaction), bursty (CI merges + nightly batches), and cost-sensitive. A modular monolith backed by PostgreSQL `17.12` provides ACID transactional guarantees between run creation, per-call budget reservations, job enqueueing, durable SSE `run_events`, and transcript persistence—eliminating distributed two-phase commits and Kafka/Temporal operational overhead while maintaining strict internal module boundaries.

---

## 2. System Context Diagram (C4 Level 1)

```mermaid
flowchart LR
    PE[Prompt / FDE Engineer] -->|Edits prompts, inspects V1 vs V2 diffs| UI[PropEval Web UI & CLI]
    CI[GitHub Actions CI/CD] -->|Triggers PR smoke gate & nightly release runs| API[PropEval Control Plane]
    UI --> API

    API -->|Executes candidate, simulator & judge turns| LLM[External LLM Providers<br/>OpenAI / Gemini / Groq]
    API -->|Optional: tests live customer agent| CUST[Customer Target Agent Webhook<br/>via SSRF Egress Proxy]
    API -->|Exports OTLP gen_ai.* traces & metrics| OTel[Observability Backend<br/>OTLP / Grafana / Langfuse]
    PROD[Anonymized Production Call Logs<br/>Twilio / Exotel Transcripts] -->|Imported via Presidio PII Redactor| API
```

---

## 3. Container Diagram (C4 Level 2)

```mermaid
flowchart TB
    subgraph ClientLayer["Client Interfaces"]
        WEB["Next.js 16.4.6 / React 19.3 Web UI<br/>(Diff Viewer, Trace Explorer, Calibration)"]
        CLI["PropEval Python CLI<br/>(CI/CD Exit-Code Gate)"]
    end

    subgraph AppCluster["PropEval Modular Monolith (Python 3.12+ / FastAPI 0.165.0)"]
        API["Control Plane API<br/>REST + Durable SSE (run_events + PG LISTEN) + OTel"]
        WORKER["Async Eval Worker Pool<br/>(FSM Simulator + Target Runner + 3-Tier Grader + Stats)"]
        REAPER["Lease Reaper & SPC Scheduler<br/>(Expired Lease Recovery + Nightly Canary EWMA)"]
    end

    subgraph DataLayer["Data & Security Infrastructure"]
        PG[("PostgreSQL 17.12<br/>OLTP + SKIP LOCKED Queue + run_events + RLS + Ledger")]
        VALKEY[("Valkey 8.x (Phase 2 Multi-Pod)<br/>Dual RPM/TPM Lua Token Buckets")]
        KMS["Cloud KMS<br/>Envelope Encryption for BYOK Keys"]
        EGRESS["SSRF-Safe Egress Proxy<br/>(DNS/IP Pinned HTTPS Only)"]
    end

    subgraph Analytics["Optional Offline OLAP"]
        DUCK["DuckDB 2.0.0 over Parquet<br/>(Cross-Run Failure Clustering)"]
    end

    WEB -->|HTTPS REST + SSE| API
    CLI -->|HTTPS REST| API
    API -->|asyncpg + LISTEN| PG
    WORKER -->|SECURITY DEFINER Claim + RLS Writes| PG
    WORKER -.->|Multi-Pod Rate Limit| VALKEY
    WORKER -->|Decrypt BYOK DEK| KMS
    WORKER -->|Target Webhooks| EGRESS
    REAPER -->|Reclaim Stale Leases| PG
    PG -.->|Nightly Parquet Export| DUCK
```

---

## 4. Component Diagram (C4 Level 3 — Inside the Modular Monolith)

```mermaid
flowchart LR
    subgraph ControlPlane["api/ (Control Plane)"]
        R_PROMPT["Prompt & Fixture Registry"]
        R_RUN["Experiment & Run Orchestrator"]
        R_REPLAY["Production Replay Importer"]
        R_SSE["Durable SSE Streamer (run_events + Last-Event-ID)"]
    end

    subgraph SecurityPipe["security/"]
        PII["Presidio PII Redactor<br/>(IN Phone, PAN, Verhoeff Aadhaar)"]
        INJ["XML Nonce Prompt-Injection Guard"]
        CRYPTO["KMS Envelope Decryptor"]
    end

    subgraph ExecutionCore["engine/ (Worker Execution)"]
        Q["PG SKIP LOCKED Queue<br/>(SECURITY DEFINER + Fence Token)"]
        BUDGET["Per-Call budget_reservations Breaker"]
        SIM["Hybrid FSM + LLM Buyer Simulator"]
        PERTURB["8 kHz ASR Perturbation & Tool Fault Injector"]
        ADAPTER["TargetAgentAdapter<br/>(Local LLM+MockTools OR Remote Webhook)"]
        LEDGER["Idempotent llm_call_ledger (Checked First)"]
    end

    subgraph EvalCore["evaluation/"]
        DET["Layer 1: Deterministic Oracles<br/>(Currency, Schema, DNC, Metamorphic)"]
        FACT["Layer 2: Versioned Property Fact Verifier"]
        JUDGE["Layer 3: Cross-Family Calibrated Rubric Judge<br/>+ Simulator-Fidelity Auditor"]
        STATS["Statistical Engine (SciPy / statsmodels)<br/>McNemar (K=1/pass^k), Wilcoxon, Cluster Bootstrap, Holm"]
    end

    R_REPLAY --> PII --> R_RUN
    R_RUN --> Q
    Q --> LEDGER --> BUDGET --> SIM
    SIM --> PERTURB --> ADAPTER
    ADAPTER --> DET --> FACT --> JUDGE --> STATS
    STATS --> R_SSE
```

---

## 5. End-to-End Experiment Lifecycle Sequence Diagram

```mermaid
sequenceDiagram
    actor Eng as Engineer / CI
    participant API as FastAPI Control Plane
    participant PG as PostgreSQL 17.12 (Queue + Ledger + run_events)
    participant W as Async Eval Worker
    participant LLM as Independent LLM Providers (Sim / Target / Judge)

    Eng->>API: POST /api/v1/runs (v1_id, v2_id, suite_id, trials_k=3, max_budget_usd=4.50)
    API->>PG: BEGIN; INSERT eval_runs + 2*N*K eval_jobs (QUEUED); COMMIT
    API-->>Eng: 202 Accepted (run_id, stream_url)
    Eng->>API: GET /api/v1/runs/{run_id}/stream (SSE + Last-Event-ID)

    loop For each claimed job (paired V1 & V2 scenarios)
        W->>PG: SELECT * FROM claim_next_eval_job(worker_id, 60) -> fence_token++, releases stale reservations
        W->>PG: SET LOCAL app.current_tenant_id = job.tenant_id
        loop Turns 1..max_turns (while FSM != TERMINAL)
            W->>W: FSM decides next buyer agenda directive
            W->>PG: Check llm_call_ledger FIRST -> if miss, reserve budget_reservations
            W->>LLM: Simulator LLM renders Hinglish -> apply 8 kHz ASR perturbation
            W->>LLM: Target Agent responds + executes replayable MockRealEstateEnv tools
            W->>PG: Fenced persist_turn(fence_token) + settle budget_reservations
        end
        W->>LLM: Simulator Auditor & Cross-Family Judge (also via ledger + budget_reservations)
        W->>PG: Fenced Commit + INSERT run_events('job.completed') + NOTIFY
        API-->>Eng: SSE event: job.completed
    end

    W->>PG: Atomic CAS (RUNNING -> COMPUTING_STATS) -> compute paired stats
    W->>PG: UPDATE eval_runs + INSERT run_events('run.completed') + NOTIFY
    API-->>Eng: SSE event: run.completed (diff_summary)
```

---

## 6. Data Flow Diagram

```mermaid
flowchart TD
    YAML["Versioned Scenario Suites (YAML/Git)<br/>+ Project Fixtures (RERA, Pricing)"] --> REG["Immutable Registry Tables (PG)"]
    RAW["Raw Production Transcripts"] --> REDACT["Presidio PII Scrubber<br/>(<IN_PHONE_1>, <IN_PAN_1>)"] --> REG
    REG --> EXEC["Simulation & Target Execution"]
    EXEC -->|"Turns, Tool Calls, Latency, Tokens"| TRANS["Normalized PG Tables<br/>(conversation_turns, assertion_results)"]
    TRANS --> STATS["Paired Statistical Diff Engine"]
    STATS --> UI["Next.js Diff UI & CI Exit Code"]
    EXEC -->|"OTLP gen_ai.* (PII-free)"| OTEL["OpenTelemetry Collector"]
    TRANS -.->|"Nightly Export"| PARQUET["Parquet + DuckDB 2.0.0<br/>(Failure Clustering & EWMA SPC)"]
```

---

## 7. Prompt Version, Dataset & Evaluation Lifecycles

1. **Prompt Version Lifecycle (`prompt_versions.status`):** `DRAFT` $\to$ `REGISTERED` $\to$ `CANDIDATE_EVALUATING` $\to$ `GATED_PASS | GATED_REGRESSED` $\to$ `PRODUCTION_BASELINE` $\to$ `ARCHIVED`.
2. **Dataset Version Lifecycle (`scenario_suites.suite_tier`):** Immutable Git-versioned YAML suites stratified into `smoke_pr` ($N=20$), `release_gate` ($N=50\text{–}100$), `metamorphic`, and `canary_spc`, plus `calibration_anchors` for judge calibration.
3. **Evaluation Run Lifecycle (`eval_runs.status`):** `QUEUED` $\to$ `RUNNING` $\to$ `COMPUTING_STATS` $\to$ `PASSED | REGRESSED | INCONCLUSIVE_UNDERPOWERED | BUDGET_EXCEEDED | EARLY_ABORTED_HARM | FAILED`.

---

## 8. Deployment Diagram & Scaling Strategy

```mermaid
flowchart LR
    subgraph Cloud["Cloud Region: ap-south-1 (Mumbai — Enterprise Privacy Guarantee)"]
        LB["HTTPS Load Balancer / TLS 1.3"]
        WEB_POD["Next.js Web Container (1-2 replicas)"]
        API_POD["FastAPI Control Plane (2 replicas)"]
        W_POD["Async Eval Worker Pods (2-10 autoscaled on queue lag)"]
        PROXY["SSRF Egress Proxy (Dedicated Subnet, IMDSv2)"]
        PG_M[("Managed PostgreSQL 17.12 Primary<br/>(Multi-AZ + Read Replica)")]
        VALKEY[("Managed Valkey 8.x<br/>(Multi-Pod RPM/TPM Rate Limiter)")]
        KMS_C["Cloud KMS (CMK per Env)"]
    end

    LB --> WEB_POD
    LB --> API_POD
    API_POD --> PG_M
    W_POD --> PG_M
    W_POD --> VALKEY
    W_POD --> KMS_C
    W_POD --> PROXY
```
