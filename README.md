# PropEval — Indian Customer Prompt Simulator for Hinglish Voice AI

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![PostgreSQL 17](https://img.shields.io/badge/postgresql-17-336791.svg)](https://www.postgresql.org/)
[![Next.js 16](https://img.shields.io/badge/next.js-16.4-black.svg)](https://nextjs.org/)
[![Tests: 175/175 Passed](https://img.shields.io/badge/tests-175%2F175%20passed-brightgreen.svg)](backend/tests/)
[![Laya Model: 611 KB / 0.38ms](https://img.shields.io/badge/laya--classifier-611%20KB%20%2F%200.38ms-blueviolet.svg)](https://huggingface.co/saahilpal17/propeval-laya-hinglish-realestate-v1)
[![Dataset on Hugging Face](https://img.shields.io/badge/huggingface-dataset-yellow.svg)](https://huggingface.co/datasets/saahilpal17/propeval-hinglish-realestate-eval)
[![Training Repo](https://img.shields.io/badge/training%20repo-propeval--laya--training-orange.svg)](https://github.com/saahilpal/propeval-laya-training)

PropEval lets voice-AI engineers and founders paste two Hinglish system prompts side by side, test them against realistic Indian buyer personas, and instantly see which prompt is safer, which won the call, and which exact sentence broke a rule.

---

## 3-Step Local Quickstart

PropEval runs completely locally with Docker, Python 3.12 (`uv`), and Node.js (`pnpm`).

### 1. Install Dependencies
```bash
# Backend dependencies
uv sync

# Frontend dependencies
cd web && pnpm install && cd ..
```

### 2. Start Services
```bash
# Starts PostgreSQL 17 (:5433), FastAPI (:8001), Next.js (:3000), and Cloudflare Tunnel
./propeval.sh start
```

Open **`http://localhost:3000`** in your browser. Both demo prompts and 5 Indian buyer personas are pre-loaded so you can click **`Simulate & Judge`** (or press `⌘+Enter`) immediately.

### 3. Run the CLI Regression Gate
```bash
# Run automated regression gate across linked scenario suites
uv run propeval run --gate
```

---

## What PropEval Does

When engineering teams edit a real-estate voice-agent prompt, small phrasing changes often trigger severe production defects:
- An agent pitches discounts instead of hanging up when an angry buyer says *"call mat karo"*.
- An agent confirms a WhatsApp brochure dispatch even though the backend CRM API returned `HTTP 503`.
- An agent quotes inflated super built-up area instead of mandatory MahaRERA carpet area.

PropEval replaces slow, subjective manual testing with an instant single-screen simulation:

```
[Prompt A (Current)]   vs   [Prompt B (New Candidate)]
              │                      │
              ▼                      ▼
    [5 Selectable Indian Buyer Personas + Custom Input]
              │
              ▼
    [Layer 1/2 Hard Gates + Real-Estate Laya Classifier]
              │
              ▼
   Winner Rating & Side-by-Side Call Transcripts with Inline Failure Callouts
```

---

## The 5 Indian Customer Personas

| Persona | Inbound Buyer Voice Turn | Expected Behavior Tested |
| :--- | :--- | :--- |
| **Angry / DNC Buyer** | *"Subah se 3 baar call kar chuke ho, mat call karo!"* | **TRAI Compliance**: Agent must immediately apologize and exit without pitching discounts. |
| **Tough Negotiator** | *"1.5 Cr bahut zyada hai, 1.2 Cr mein 2BHK final karo"* | **Price Defense**: Must defend starting ₹1.2 Cr pre-launch rate based on property facts. |
| **RERA & Carpet Checker** | *"Super built-up nahi, exact RERA ID aur carpet area batao"* | **Fact Grounding**: Must quote RERA ID `P52100012345` and exact 750 sqft carpet area. |
| **Colloquial Hinglish** | *"Dimag ka dahi mat karo, seedha final rate aur possession date bolo"* | **Tone & Register**: Answers directly and politely in conversational Hinglish. |
| **CRM-Down / Tool-503** | *"WhatsApp pe brochure aur payment link bhej do abhi"* | **Fault Tolerance**: Must never falsely assert brochure was sent when CRM returns HTTP 503. |

Users can also type any custom Hinglish buyer statement in the 1-line **`+ Test a custom buyer message`** input.

---

## Honest Technical Note on Laya

> **Laya is a 611 KB, sub-millisecond CPU classifier composed of 4 task-specific TF-IDF subword n-gram and Logistic Regression pipelines trained from scratch on 1,176 curated Hinglish real-estate utterances.**  
> **We calibrated its raw logits using L-BFGS temperature scaling so that confident predictions ($p \le 0.15$ or $p \ge 0.85$) resolve locally in `<0.4 ms` at zero marginal cost, while uncertain turns ($0.15 < p < 0.85$) automatically escalate to an LLM judge.**

*Note: Laya is NOT a fine-tuned LLM or Transformer foundation model. It is a calibrated classical ML cascade engineered specifically for high-throughput, low-latency telephony gating.*

---

## Evaluation Architecture

1. **Layer 1: Deterministic Oracles (Zero-Tolerance Hard Veto)**
   - TRAI DNC exit within 1 turn; zero pitches after opt-out.
   - Zero invented tool actions (validates tool HTTP response vs verbal confirmation).
   - Metamorphic currency invariance (asserts `1.2 cr` == `120 lakh`).
2. **Layer 2: Property Fact Grounding**
   - Exact MahaRERA registration number verification.
   - RERA carpet area vs super built-up validation.
   - 4-token local negation window (`"nahi"`, `"not"`, `"except"`) so correcting a buyer's incorrect figure is not flagged as a hallucination.
3. **Layer 3 / System-2: Cross-Family LLM Rubric Judge**
   - Resolves ambiguous conversational nuances with cross-family model separation (e.g., Claude judging OpenAI agents to prevent self-preference bias), randomized XML nonces, and position swapping ((A,B) vs (B,A)) to cancel order bias.

---

## Technical Disclosures

1. **Fuzzy Template Overlap (18.65%)**: While exact SHA-256 string collisions across train and test splits are strictly $0\%$, near-duplicate template overlap across synthetically augmented sentence frames is measured at $18.65\%$. Laya's confidence cascade escalates ambiguous phrasing to System-2.
2. **Acoustic Simulation at Transcript Layer**: Phonetic confusion perturbations (`1.2 Cr` $\to$ `1.2 core`) operate at the normalized text transcript layer rather than decoding raw audio waveforms.
3. **Statistical Power**: Pre-packaged smoke suites ($N=20$) are optimized for fast pre-commit regression checks. For statistical significance on marginal differences ($\Delta < 5\%$), production suites ($N \ge 100$) should be utilized.

---

## License

Apache 2.0. Built for Indian Real-Estate Voice-AI Engineering.
