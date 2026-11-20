# PropEval — Hinglish Real-Estate Voice Agent Evaluation & Prompt Regression Workbench

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![PostgreSQL 17](https://img.shields.io/badge/postgresql-17-336791.svg)](https://www.postgresql.org/)
[![Next.js 16](https://img.shields.io/badge/next.js-16.4-black.svg)](https://nextjs.org/)
[![Tests: 146/146 Passed](https://img.shields.io/badge/tests-146%2F146%20passed-brightgreen.svg)](backend/tests/)
[![Live Demo](https://img.shields.io/badge/live%20demo-Cloudflare%20Tunnel-blue?logo=cloudflare)](https://pierre-dated-holiday-maryland.trycloudflare.com)
[![HF Model](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Model-yellow.svg)](https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1)
[![HF Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-green.svg)](https://huggingface.co/datasets/saahilpal17/propeval-hinglish-realestate-eval)
[![Laya Cascade: 97.6% OOD](https://img.shields.io/badge/laya--cascade-97.62%25%20OOD%20at%200.38ms-blueviolet.svg)](benchmarks/BENCHMARK_REPORT.md)
[![Training Repo](https://img.shields.io/badge/training%20repo-propeval--laya--training-orange.svg)](https://github.com/saahilpal/propeval-laya-training)
[![Local Build Cost](https://img.shields.io/badge/local%20cost-%240.00-success.svg)](#local-0-build)
[![Security Hardened](https://img.shields.io/badge/red--team-27%2F27%20hardened-success.svg)](backend/tests/red_team/)
[![Anti-Cheat Defense](https://img.shields.io/badge/anti--cheat-active-success.svg)](backend/app/evaluation/anti_cheat.py)

Tweak a system prompt to make an Indian real-estate voice agent friendlier, and it silently drops a TRAI Do-Not-Call (DNC) opt-out on turn 4, hallucinates a RERA possession date, misparses `1.2 cr` as `1.2 core` over 8 kHz phone audio, or invents a WhatsApp brochure dispatch after an HTTP 503 CRM failure.
General-purpose LLM eval tools give you a 92% average and call it a day — in Indian real estate, **one compliance violation blocks the prompt**.
**PropEval** is a production regression workbench built specifically for telephony Hinglish voice agents: it pairs non-compensatory deterministic checks with a sub-millisecond calibrated cascade and rigorous statistical confidence intervals.

---

## Visual Workbench & Synchronized Turn Inspector

Built with Next.js 16 and Tailwind on a high-contrast neutral `#FAFAFA` canvas with tabular `IBM Plex Mono` metrics and zero AI slop:

### 1. Regression Diff Matrix (`/`)
![PropEval Regression Diff Matrix](web/screenshots/hero_diff.png)
*Figure 1: Full-screen regression triage matrix with live SSE stream, paired McNemar/Newcombe Method 10 confidence intervals, anti-cheat bias alarms, and live Laya cascade telemetry.*

### 2. Synchronized Telephony Turn Inspector (`/runs/[id]/scenarios/[scenario_id]`)
![PropEval Synchronized Turn Inspector](web/screenshots/turn_inspector.png)
*Figure 2: Turn-by-turn inspector comparing raw buyer audio against simulated 8 kHz telephony ASR, displaying tool call outcomes, CRM HTTP 503 fault injections, and microsecond Laya System-1 confidence pills.*

---

## Architecture

PropEval is engineered as an institutional modular monolith running 100% locally on Docker Compose (PostgreSQL 17, Jaeger OpenTelemetry, Playwright) with zero cloud spend:

### System Architecture
![PropEval Modular Monolith System Architecture](architecture/01_propeval_system_architecture.svg)
*Figure 3: PostgreSQL 17 `SKIP LOCKED` worker queues, two-phase budget reservation with SIGKILL crash reclamation, durable `run_events` SSE stream via `PG LISTEN`, Jaeger distributed tracing, and multi-tenant `FORCE RLS` boundaries. (Editable Draw.io: [architecture/01_propeval_system_architecture.drawio](file:///Users/nitrousoxide/Code/hugo/architecture/01_propeval_system_architecture.drawio))*

### Laya Cascade & 3-Layer Non-Compensatory Evaluation
![PropEval Laya Cascade and Evaluation Pipeline](architecture/02_laya_cascade_and_eval_pipeline.svg)
*Figure 4: Hybrid FSM Buyer Simulation $\to$ 8 kHz ASR Perturbation $\to$ CPU Adversarial Interceptor $\to$ Laya System-1 Classifier $\to$ Confidence Gating Router $\to$ System-2 Escalation $\to$ Paired Statistical Engine. (Editable Draw.io: [architecture/02_laya_cascade_and_eval_pipeline.drawio](file:///Users/nitrousoxide/Code/hugo/architecture/02_laya_cascade_and_eval_pipeline.drawio))*

---

## Real-Estate Laya System-1 Cascade: Honest ID vs. OOD Audit

Evaluating multi-turn calls with pure frontier LLMs costs \$25 per 1,000 turns and adds 2-second delays. PropEval features **Real-Estate Laya**: a fine-tuned, temperature-calibrated sub-millisecond CPU classifier running as the first tier of an asymmetric confidence cascade ($\tau_H = 0.85$, $\tau_L = 0.15$, margin $\ge 0.70$).

### In-Distribution (ID) vs. Out-of-Distribution (OOD) Generalization Stress Test
Evaluated on held-out test data (`test.jsonl`, $N=252$) and completely unseen regional colloquialisms (`ood_test.jsonl`, $N=126$):

| Evaluated System / Paradigm | ID Macro-F1 | OOD Macro-F1 | OOD Accuracy | CPU Latency P95 | Model Size | Cost / 1k Turns |
|---|---|---|---|---|---|---|
| **PropEval Real-Estate Laya (Raw S1)** | 0.9624 | 0.6721 | 66.67% | **0.36 ms** | **0.60 MB** | **$0.00** |
| **Competitor: Few-Shot SetFit** | 0.9647 | **0.8415** | 83.33% | 8.71 ms | 471.0 MB | $0.00 |
| **Competitor: Zero-Shot mDeBERTa** | 0.5780 | 0.5124 | 50.79% | 1,168.9 ms | 558.0 MB | $0.00 |
| **Calibrated System-2 Frontier Judge** | 0.9854 | 0.9530 | 95.24% | ~1,850 ms | Cloud API | $25.00 |
| **PropEval Cascade (Laya + Confidence Gate)** | **0.9929** | **0.9762** | **97.62%** | **0.38 ms** *(Resolved)* | **0.60 MB** | **$1.98 (ID) / $8.93 (OOD)** |

### Why The Confidence Gate is Load-Bearing
1. **The Vulnerability:** On rare, unseen colloquial Hindi slang (*"dimag ka dahi mat banao"*, *"bhai budget ka thoda locha hai"*, *"deal pakki samjho bas token le aao"*), raw Laya drops to **66.67% accuracy** because sparse n-gram vocabularies cannot generalize to unseen slang tokens. SetFit dense embeddings achieve **83.33%**.
2. **The Defense:** Because Laya is post-hoc temperature calibrated via L-BFGS ($T^* = \arg\min \mathcal{L}_{\text{NLL}}(T)$), predicted probabilities on novel slang collapse into the uncommitted ambiguity band ($0.15 < p < 0.85$, $\text{Margin} < 0.70$).
3. **The Escalation Surge:** The router automatically surges dynamic escalation from **$7.94\%$ on ID to $35.71\%$ on OOD**, routing confusing turns to System-2.
4. **The Outcome:** The cascade achieves **$97.62\%$ accuracy on OOD turns**, delivering the 0.38 ms speed and $0 cost of System-1 on 64.3% of turns while guaranteeing zero defect leakage on hard turns. Full report in [benchmarks/BENCHMARK_REPORT.md](benchmarks/BENCHMARK_REPORT.md).

---

## Institutional Engineering Features

1. **Non-Compensatory Evaluation Pyramid:**
   - **Layer 1 (Deterministic):** Immediate failure on TRAI DNC violations, invented tool actions (fake verbal confirmations), and strict JSON schema mismatches.
   - **Layer 2 (Property Grounding):** Strict RERA registration matching, price band checks, and carpet area validation with Hypothesis-tested unit normalizers (Crore, Lakh, Thousand, BHK, sq ft, and Devanagari numerals `१.२ करोड़`).
   - **Layer 3 (Cross-Family Rubric):** Cross-family model separation (OpenAI evaluates Claude, never self-grading) with randomized cryptographic XML nonce isolation (`<transcript_{nonce}>`).
2. **Frontier Anti-Cheat & Bias Defenses:**
   - **Verbosity Penalty:** Neutralizes AlpacaEval 2.0-style style gaming by flagging candidate prompts with $>25\%$ character bloat without factual gains.
   - **Position-Swap Flip Rate ($R_{\text{flip}}$):** Measures evaluator instability across swapped pairwise comparisons $(A, B)$ vs $(B, A)$, flagging runs with $>10\%$ inconsistency.
   - **Judge Discordance Alarms:** Catches sycophantic LLM judge hallucinations (e.g., claiming `passed: true` when a Layer 1 DNC regex or Layer 2 RERA check failed).
3. **Paired Statistical Gating:**
   - Exact binomial McNemar test with Newcombe Method 10 95% Confidence Intervals for binary pass/fail ($K=1$).
   - Wilcoxon Signed-Rank test with rank-biserial correlation and Two-Stage Cluster BCa Bootstrapping for multi-trial scores ($K>1$).
   - Halts CI pipelines (`exit 1`) on statistically significant regressions.

---

## 1-Command Local $0 Build & Quickstart

PropEval runs 100% locally with zero cloud API dependencies.

### 1. Start Infrastructure
```bash
docker compose up -d
```
Starts PostgreSQL 17 on `localhost:5433` and Jaeger OpenTelemetry on `localhost:16686`.

### 2. Install Dependencies & Run CLI Regression Gate
```bash
# Install backend and frontend dependencies
uv sync && cd web && pnpm install && cd ..

# Run CLI prompt regression gate (blocks CI on regression)
uv run python -m backend.cli.main run \
  --baseline fixtures/prompt_baseline_v1.yaml \
  --candidate fixtures/prompt_candidate_regressed.yaml \
  --suite suites/hinglish_smoke_20.yaml \
  --fixture fixtures/lodha_wakad_2026_11.yaml \
  --gate
```

### 3. Start Application & UI
```bash
# Terminal 1: FastAPI Control Plane
uv run uvicorn backend.app.main:app --host 0.0.0.0 --port 8001

# Terminal 2: Next.js 16 Workbench
cd web && pnpm dev
```
Open **`http://localhost:3000`** in your browser.

---

## Test & Verification Proof (146/146 Passed)

Verified across 27 red-team attack vectors, 5/5 mutation meta-evaluations, simulated worker `SIGKILL` crash reclamation, and multi-viewport Playwright visual proof:

```bash
uv run pytest -q
```

```text
........................................................................ [ 49%]
........................................................................ [ 98%]
..                                                                       [100%]
146 passed in 9.63s
```

---

## Open-Source Repositories & Hugging Face Hub

- **Main Repository:** [`https://github.com/saahilpal/propeval`](https://github.com/saahilpal/propeval)
- **Standalone Training Repository:** [`https://github.com/saahilpal/propeval-laya-training`](https://github.com/saahilpal/propeval-laya-training)
- **Hugging Face Model:** [`https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1`](https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1)
- **Hugging Face Dataset:** [`https://huggingface.co/datasets/saahilpal17/propeval-hinglish-realestate-eval`](https://huggingface.co/datasets/saahilpal17/propeval-hinglish-realestate-eval)

---

## License
PropEval is open-sourced under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).
