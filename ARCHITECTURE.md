# PropEval Architecture Specification

PropEval is an evaluation and prompt regression workbench designed for Hinglish voice AI agents in Indian real estate telephony.

## 1. System Architecture Overview
![PropEval Modular Monolith System Architecture](architecture/01_propeval_system_architecture.svg)
*Figure 1: PropEval Modular Monolith Architecture (Editable Draw.io: [architecture/01_propeval_system_architecture.drawio](architecture/01_propeval_system_architecture.drawio))*

## 2. Laya Cascade & 3-Layer Evaluation Pipeline
![PropEval Laya Cascade and Evaluation Pipeline](architecture/02_laya_cascade_and_eval_pipeline.svg)
*Figure 2: Real-Estate Laya System-1 Cascade & 3-Layer Evaluation Pyramid (Editable Draw.io: [architecture/02_laya_cascade_and_eval_pipeline.drawio](architecture/02_laya_cascade_and_eval_pipeline.drawio))*

## 3. Component Flow Specification
```mermaid
flowchart TD
    subgraph UI["Frontend UI / UX (Next.js 16 / React 19)"]
        Workbench["Experiment Diff Workbench (/)"]
        Transcript["Side-by-Side Turn Inspector (/runs/id/scenarios/id)"]
        Registry["Prompt & RERA Registry (/registry)"]
    end

    subgraph API["FastAPI Control Plane (Port 8001)"]
        PromptsAPI["/api/v1/prompts"]
        FixturesAPI["/api/v1/fixtures"]
        SuitesAPI["/api/v1/suites & /replay/import"]
        RunsAPI["/api/v1/runs & /runs/id/diff"]
        SSEStream["/api/v1/runs/id/stream (Last-Event-ID)"]
    end

    subgraph Simulation["Evaluation Worker & Engine"]
        FSM["BuyerAgendaFSM (State Machine)"]
        ASR["8 kHz ASR Perturbation Engine"]
        MockEnv["MockRealEstateEnv (CRM & Tool Faults)"]
        Adapter["Target Agent Adapter (Local $0 / Webhook)"]
    end

    subgraph Evaluation["3-Layer Evaluation Core"]
        L1["Layer 1: Deterministic Oracles (DNC, Invented Actions, Tool Schema)"]
        L2["Layer 2: Property Fact Grounding (4-token Negation, RERA, Price)"]
        L3["Layer 3: Cross-Family Rubric Judge (Randomized XML Nonces)"]
        Stats["Paired Statistics (Exact McNemar, Newcombe CI, Wilcoxon, BCa)"]
    end

    subgraph DB["PostgreSQL 17 (Port 5433)"]
        RLS["FORCE Row-Level Security (NULLIF Tenant ID)"]
        Queue["claim_next_eval_job() (SKIP LOCKED + Fairness)"]
        Budget["Two-Phase budget_reservations"]
        Events["run_events (Durable Stream)"]
    end

    UI --> API
    API --> DB
    Simulation --> DB
    Simulation --> Evaluation
    API -.-> SSEStream
```

## Architectural Highlights
1. **$0 Local Build:** Fully runs offline via Docker Compose with PostgreSQL 17, local Jaeger OTel, and a deterministic replay provider.
2. **Non-Compensatory Hard Gates:** If an agent violates TRAI DNC, hallucinates RERA facts, or invents tool confirmations after HTTP 503 errors, the candidate prompt is blocked regardless of overall fluency score.
3. **Paired Statistical Rigor:** Uses Exact McNemar tests with Newcombe Method 10 confidence intervals and two-stage BCa bootstrapping instead of misleading unpaired averages on small scenario sets ($N < 50$).
4. **Multi-Tenant Isolation:** `FORCE ROW LEVEL SECURITY` across all 15 tenant tables with `NULLIF` variable safety.
5. **Linear-Grade Workbench Aesthetic:** Neutral canvas, 1px borders, and monospace `IBM Plex Mono` tabular numerals for every numeric measurement.

## System Disclosures & Prototype Boundaries

1. **Acoustic Simulation Reality:** PropEval evaluates dialogue turns via synthetic 8 kHz phonetic perturbation matrices (confusion rules simulating Indian ASR telephony transcribers) and LLM buyer personas, not raw SIP/RTP VoIP packet streams. Audio jitter, packet drop, acoustic echo, and codec clipping are simulated at the textual transcription boundary rather than in hardware digital signal processors (DSP).
2. **Statistical Power & Sample Size Thresholds:** The default $N=20$ smoke test suite (`hinglish_smoke_20.yaml`) is designed strictly as a fast directional pre-commit gate. It carries $>80\%$ Type II error ($\beta$) for small-to-moderate effect sizes ($\Delta < 20\%$). Final production release candidate decisions require the benchmarked $N \ge 120$ suite (`hinglish_release_30.yaml` with trials $K \ge 4$ or full benchmark suite) to achieve statistical power $(1 - \beta) \ge 0.80$ at $\alpha = 0.05$.
3. **Dataset Template Distribution:** Exact-match SHA-256 deduplication across splits is verified ($\text{Train} \cap \text{Val} = \emptyset$, $\text{Train} \cap \text{Test} = \emptyset$). Synthetic template generation introduces an estimated 18.65% near-duplicate fuzzy template overlap in training slots, mitigated in production by dual-confidence System-2 escalation.
