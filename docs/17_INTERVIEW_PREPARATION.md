# 17 — Interview Preparation & Deep Conceptual Defense Guide

This guide prepares you to defend every engineering, statistical, voice-AI, database, and security decision in PropEval from first principles—without relying on memorized buzzwords.

---

## 1. The 60-Second Product & Architecture Pitch (Plain English)

> "Huvo already built the hard parts of a real estate Voice AI OS—sub-minute calling, qualification, booking, and WhatsApp follow-ups. Your own Prompt Engineer and Backend JDs show the next bottleneck: iterating on Hinglish prompts safely without manually listening to hundreds of calls. PropEval is a paired prompt-regression workbench built specifically for Indian real estate. You pass Prompt V1 and Prompt V2 against an FSM-controlled Hinglish buyer simulator with injected 8 kHz ASR noise and tool failures. Instead of arbitrary 1–10 AI scores, it enforces zero-tolerance deterministic gates—Indian lakh/crore normalization, RERA fact grounding, DNC compliance, and zero invented WhatsApp/booking confirmations—paired with cross-family calibrated rubric judges and exact paired statistics (`McNemar`, `Wilcoxon`, `pass^k`, `Holm-Bonferroni`). Under the hood it's a FastAPI + PostgreSQL `FOR UPDATE SKIP LOCKED` modular monolith with fencing tokens, an idempotent LLM call ledger, and atomic USD budget caps."

---

## 2. Core Mental Models to Master (Not Memorize)

1. **Why Hybrid FSM + LLM beats Pure LLM Simulation:** Pure LLM simulators have two proven flaws: RLHF *assistant/benevolence bias* (they politely volunteer all slots instead of behaving like impatient buyers) and *40–47% simulator error rates* in multi-turn tool benchmarks ($\tau^2$-Bench). Separating **control** (deterministic FSM decides *when* to reveal `1.2 cr` or hang up) from **surface realization** (LLM renders natural Hinglish) eliminates goal drift while preserving realistic phrasing.
2. **Why $N=20$ Cannot Prove Statistical Significance:** Under exact McNemar's test, even with *zero* regressions ($c=0$), reaching $p < 0.05$ requires 6–0 flips (+30 pp), and 80% power requires +36.6 pp to +53.4 pp. Therefore $N=20$ is a **PR smoke gate** for zero-tolerance deterministic bugs, while $N=50\text{–}100$ with $K=3\text{–}5$ trials is the **release gate** for statistical claims.
3. **Why Fencing Tokens + `llm_call_ledger` Matter:** Holding a Postgres transaction open during a 30-second LLM call destroys connection pools. Releasing the lock after claiming requires a lease (`60 s`) + heartbeat (`20 s`). If Worker A freezes (GC pause), Worker B reclaims the job (`fence_token` increments from `1` to `2`). When zombie Worker A wakes up, its `WHERE fence_token = 1` commit affects `0` rows—preventing silent overwrites. Meanwhile, `llm_call_ledger` keyed by `sha256(tenant|run|case|turn|step|model|prompt)` guarantees retries never double-charge LLM tokens.
4. **Why Non-Compensatory Profiles Beat Composite Scores:** A +10% warmth improvement can never legally or commercially offset a 2% RERA/carpet-area hallucination or a missed TRAI DNC opt-out.

---

## 3. Challenging Interview Questions by Persona (with Grounded Answers & Follow-Up Probes)

### A. Startup Founder / CEO (Tushar Khustule — Quant & Data Scientist Lens)
* **Q1: "Why didn't you just use DeepEval, Promptfoo, or Langfuse instead of building PropEval?"**
  * *Grounded Answer:* We audited all three (`docs/07`). Langfuse v4 is a great OTel/ClickHouse observability platform, so we integrate via OTLP export rather than inheriting ClickHouse ops and `ee/LICENSE` boundaries. Promptfoo is Node.js-first and awkward inside a Python/SciPy async worker. DeepEval hides opaque judge prompts that make per-variant Rogan–Gladen calibration and paired statistical diffing hard. Our core runner is ~250 lines of transparent Python—while we *do* adopt OpenTelemetry (`1.45.2`), SciPy (`1.18.1`), statsmodels (`0.15.0`), and Presidio instead of reinventing them.
  * *Follow-up Probe:* "How do you know your own LLM judge isn't drifting or biased toward GPT-4.1 over Gemini?" $\to$ *Answer:* Cross-family isolation (forbidding same-family target & judge), position swapping `(A,B)` + `(B,A)`, and calibrating per-variant TPR/TNR on a locked 30+ human-labeled golden set ($\kappa \ge 0.70$, Rogan–Gladen / PPI++).
* **Q2: "My team edits a prompt and runs 25 test calls. V2 gets 22/25 vs V1's 19/25. Should we ship V2?"**
  * *Grounded Answer:* Not on pass-rate significance alone! A +12 pp lift at $N=25$ is well below the exact McNemar MDE (~+30–40 pp at 80% power)—the 95% Newcombe paired Wilson CI easily crosses zero. You check Hard Gates first (0 DNC/RERA/invented-action regressions), inspect the 3 discordant flips qualitatively, and run the Tier-2 $N=50\text{–}100, K=3$ suite before declaring a statistically significant win.

### B. Senior AI / Evaluation Engineer
* **Q3: "If an LLM generates your synthetic Hinglish buyers and another LLM grades the transcripts, isn't that circular validation?"**
  * *Grounded Answer:* Yes—if done naively, self-recognition linearly correlates with self-preference (Panickssery et al., 2024). We break circularity with four controls: (1) cross-family isolation across Simulator, Target, and Judge; (2) deterministic code/metamorphic oracles (`1.2 cr == 120 lakh`, tool schemas, mock DB hashes) that no LLM grades; (3) seeding personas from anonymized real transcripts; and (4) human-labeled golden calibration anchors.
  * *Follow-up Probe:* "You run $K=5$ trials on $N=20$ scenarios. Can you run a paired $t$-test with $n=100$?" $\to$ *Answer:* Absolutely not—that's pseudoreplication. Trials within the same scenario are correlated, inflating Type I error past 45% (Saravanan et al., 2020). You must resample at the **scenario cluster level** (two-stage hierarchical bootstrap) and report `pass^k` for production consistency.

### C. Voice AI Engineer
* **Q4: "Your MVP runs text simulation with injected typos. What real Hinglish phone failures will it completely miss?"**
  * *Grounded Answer:* Five major ones (`ADR-007`): (1) acoustic barge-in cancellation (<300 ms) and backchannel suppression (*"haan/achha"*); (2) prosody and "false empathy" where polite text sounds robotic in TTS; (3) Indic TTS mispronunciation (*"₹1.2 Cr"* read as *"C-R"*, *"Wakad"* mangled); (4) real 8 kHz G.711 8-bit quantization & competing-speech WER collapse; and (5) SIP jitter/playout buffer lag. That's why PropEval explicitly uses a **3-layer testing ladder** and keeps `TargetAgentAdapter` pluggable for Layer-2 recorded 8 kHz audio replay via Pipecat (`1.16.0`, BSD-2-Clause).
  * *Follow-up Probe:* "Why is WER a bad metric for Indian real estate ASR?" $\to$ *Answer:* WER weights filler words equally with deal-breaking entities. Turning *"1.2 cr"* into *"1.2 core"* is ~5% WER but 100% CRM failure. And PIER (ICASSP 2025) showed monolingual tuning can lower aggregate WER while hurting code-switched tokens. We gate on **Entity Error Rate (SEER)** + **SemDist**.

### D. Backend & Database Architect
* **Q5: "Why PostgreSQL `FOR UPDATE SKIP LOCKED` instead of Celery/Redis or Temporal?"**
  * *Grounded Answer:* With PostgreSQL, enqueueing `eval_jobs` and inserting `eval_runs` happens in one ACID transaction—zero dual-write race conditions and zero extra broker ops. Celery has an awkward `asyncio` story for high-concurrency LLM HTTP I/O, and Temporal adds cluster/determinism overhead before we need it. We mitigate PG queue risks with short claim transactions (<5 ms), 60 s leases + 20 s heartbeats, monotonic `fence_token` CAS commits, a partial index on `WHERE status IN ('QUEUED','RUNNING')`, and aggressive autovacuum. When sustained transitions exceed ~500/sec or multi-day HITL grading arrives, `storage/queue.py` swaps cleanly to Temporal.
  * *Follow-up Probe:* "How do you prevent a buggy infinite simulator loop from burning $500 of a customer's OpenAI credits?" $\to$ *Answer:* Three layered guards: (1) hard `max_turns` + 3-turn semantic similarity (>0.95) stall detector; (2) explicit `max_tokens` per call; and (3) an **atomic PostgreSQL `UPDATE eval_runs SET reserved_usd = reserved_usd + $est WHERE (spent_usd + reserved_usd + $est) <= max_budget_usd`** check before every single LLM request.

### E. Principal Security / Reliability Architect
* **Q6: "Customers give you a staging target-agent webhook URL and upload real production call transcripts. What are your top two security risks?"**
  * *Grounded Answer:* (1) **SSRF & DNS Rebinding** on the webhook URL probing `169.254.169.254` or internal Postgres—mitigated by HTTPS-only allowlist, `follow_redirects=False`, resolving DNS + validating public IP + connecting directly to the pinned IP with SNI/Host preservation through a dedicated egress proxy with IMDSv2. (2) **DPDP Act 2023 PII Leakage + OWASP LLM01 Indirect Prompt Injection** on imported transcripts—mitigated by in-VPC Presidio redaction (Indian mobile, PAN, Verhoeff-validated Aadhaar) *before* DB storage or LLM calls, randomized XML nonce framing around transcripts in judge prompts, KMS per-tenant envelope encryption for BYOK keys, and PostgreSQL `FORCE ROW LEVEL SECURITY`.
