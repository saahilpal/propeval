# 06 — Techniques & Algorithms Research

This document synthesizes independent multi-perspective research across dataset engineering, conversation simulation, evaluation methods, voice-specific telephony evaluation, failure analysis, and 10 adjacent engineering disciplines—focusing on *algorithms and mechanisms*, not merely vendor libraries.

---

## 1. Dataset Engineering & Avoiding Circular Validation

### Dataset Paradigms Compared
1. **Golden Datasets (Human-Verified Anchors):** Curated, high-stakes scenarios labeled by domain experts. Both [Hamel Husain (2024)](https://hamel.dev/blog/posts/evals/index.html) (using a real-estate assistant example) and [Anthropic's agent evaluation guide (2026)](https://daily.dev/posts/0fxjcpvym) recommend starting with 20–50 realistic failure-derived cases and expanding to 100–200 labeled examples per failure mode ([Husain, 2026](https://hamel.dev/blog/posts/evals-faq/)).
2. **Human-Validated Synthetic Generation:** Define explicit stratification dimensions (*City × Price Band × Language Mix × Buyer Friction*) and synthesize candidate cases pruned by human reviewers to remove unrealistic "textbook Hindi" phrasing ([Husain, 2025](https://hamel.dev/blog/posts/field-guide/)).
3. **Conversation-Derived Prefix Replay:** Convert anonymized production call failures into permanent tests, supporting both full-trajectory replay and **prefix replay** (replaying turns $1 \dots t-1$ verbatim and evaluating turn $t$ to isolate prompt bugs from upstream ASR drift; [arXiv:2611.00518, Oct 31, 2026](https://arxiv.org/html/2611.00518v1)).
4. **Policy-Graph & State-Machine Generation:** Following [IntellAgent (Levi & Kadar, Jan 19, 2025)](https://arxiv.org/abs/2501.11067) and [$\tau$-bench (Yao et al., Jun 17, 2024)](https://arxiv.org/abs/2406.12045), model domain policies as a co-occurrence graph and sample realistic combinations (*under-construction RERA query + budget revision + WhatsApp brochure request*) backed by deterministic mock DB states.
5. **Adversarial & CheckList Discovery:** Adapt [CheckList (Ribeiro et al., 2020)](https://arxiv.org/abs/2005.04118) into Minimum Functionality Tests (MFT), Invariance Tests (INV), and Directional Expectation Tests (DIR — e.g., dropping buyer budget from `1.5 cr` to `60 lakh` must alter recommended inventory).

### Breaking Circular Validation
When an LLM generates synthetic dialogues *and* grades the agent on them, self-recognition linearly correlates with self-preference ([Panickssery, Bowman, & Feng, 2024](https://arxiv.org/abs/2404.13076)) and extends to LLM-as-Benchmark-Generator pipelines ([Silencer, arXiv:2505.20738, 2025](https://arxiv.org/html/2505.20738v1)). PropEval breaks circularity with four mandatory controls:
* **Cross-family isolation** across Simulator, Target Agent, and Judge ([arXiv:2602.13862, 2026](https://arxiv.org/html/2602.13862v2)).
* **Locked human-labeled calibration anchors** audited by real-estate QA reviewers ([Shankar et al., 2024](https://arxiv.org/abs/2404.12272)).
* **Deterministic & metamorphic code oracles** (DB state hashing, currency canonicalization, schema validation).
* **Real-transcript seeding** so Hinglish idioms and telephony noise reflect Indian callers rather than LLM stereotypes.

---

## 2. Conversation Simulation Techniques & Simulator Bias

| Technique | Primary Research | Strengths | Failure Modes / Bias | PropEval Decision |
| :--- | :--- | :--- | :--- | :--- |
| **Scripted / Deterministic Replay** | [Evalgent (Oct 4, 2026)](https://www.evalgent.com/blog/replace-manual-test-calls-voice-agent) | 100% reproducible, near-zero cost | Breaks immediately when Prompt V2 alters turn order | **Use for Turn-1/2 PR smoke checks only** |
| **Pure FSM / Agenda-Based** | [Schatzmann et al. (NAACL 2007)](https://aclanthology.org/N07-2038/) | Zero goal drift, exact reveal control | Robotic templates, lacks Hinglish pragmatics | **Use as control backbone** |
| **Pure LLM Persona Simulator** | [$\tau$-bench (2024)](https://arxiv.org/abs/2406.12045); [$\tau^2$-Bench (Jun 2025)](https://arxiv.org/abs/2506.07982) | Natural phrasing, high diversity | **40–47% simulator error rate** (12–13% critical); **assistant/benevolence bias** ([Jeong et al., Sep 2026](https://arxiv.org/abs/2609.00608)); **worst calibration on Indian English** ($ECE=18.9$ vs $13.0$; [Seshadri et al., Jan 2026](https://arxiv.org/abs/2601.17087)) | **REJECT as standalone simulator** |
| **Hybrid FSM / Goal-Graph + LLM** | [arXiv:2402.13374 (2024)](https://arxiv.org/abs/2402.13374); [PPol (Chopra et al., May 2026)](https://arxiv.org/abs/2605.12894) | Programmatic slot gating + natural Hinglish realization; PPol boosted live human-agent success +23% | Requires explicit FSM authoring + fidelity auditing | **ADOPT as PropEval core engine** |

---

## 3. Evaluation Methods & Documented Judge Pitfalls

* **Why Reference-Based & Embedding Similarity Fail Real Estate:** BLEU/ROUGE penalize valid Hinglish paraphrases while rewarding hallucinated overlaps; BERTScore ([Zhang et al., 2020](https://arxiv.org/abs/1904.09675)) fails on numeric swaps (`₹1.2 cr` $\to$ `₹2.1 cr`; [FinNuE, arXiv:2511.09997, 2025](https://arxiv.org/html/2511.09997v1)); cosine similarity of learned embeddings yields arbitrary rankings ([Steck, Ekanadham, & Kallus, 2024](https://arxiv.org/abs/2403.05440)). **Decision:** Never use cosine similarity or BERTScore as a factual gate.
* **LLM-as-a-Judge Biases:** Documented **position bias**, **verbosity bias** (dangerous for voice UX where concise turns win), **self-enhancement bias** ([Zheng et al., 2023](https://arxiv.org/abs/2306.05685); [Wang et al., ACL 2024](https://aclanthology.org/2024.acl-long.511/)), and **cross-lingual scoring distortion** ([arXiv:2607.14480, 2026](https://arxiv.org/html/2607.14480v3)).
* **Multi-Judge Panels (PoLL) & Calibration:** [Verga et al. (2024)](https://arxiv.org/abs/2404.18796) showed diverse smaller cross-family panels beat single large judges—but correlated errors inflate effective vote count ([arXiv:2605.29800, 2026](https://arxiv.org/html/2605.29800v1)). PropEval uses **binary pass/fail rubrics** with position swapping (`(A,B)` + `(B,A)`), calibrated against human golden sets via **Cohen's $\kappa$**, **Fail-class Precision/Recall**, and **Rogan–Gladen / PPI++** bias-adjusted estimation ([Rogan & Gladen, 1978](https://pubmed.ncbi.nlm.nih.gov/623091/); [OpenReview TMLR](https://openreview.net/forum?id=J2Yg9vJcYb)).
* **Rejecting Single Composite Scores:** [Real World Voice EQ Bench (2026)](https://arxiv.org/abs/2607.14846) proves voice capabilities are orthogonal. PropEval enforces a **non-compensatory multidimensional profile** so a +10% tone gain can never mask a single RERA or DNC failure.

---

## 4. Voice-Specific Evaluation & The Text-vs-Audio Boundary

* **Beyond WER:** On Hinglish code-switched audio, [PIER (ICASSP 2025)](https://arxiv.org/abs/2501.09512) proved monolingual tuning can lower aggregate WER while *degrading* code-switched words. PropEval pairs **Semantic Distance (SemDist)** ([Kim et al., Interspeech 2021](https://arxiv.org/abs/2104.02138)) with **Slot & Entity Error Rate (SEER)** ([OpenReview, Oct 2026](https://openreview.net/forum?id=a5BDWp6FJ7)) over real-estate entities (currency units, RERA IDs, micro-markets).
* **8 kHz G.711 PSTN Reality:** [Indic ASR Codec Study (arXiv:2606.09335, Jun 8, 2026)](https://arxiv.org/html/2606.09335v1) proved 8-bit quantization and competing background speech cause sharp WER spikes—and neural audio upsamplers (VoiceFixer/AudioSR) *worsen* ASR WER compared to classical `soxr_hq` resampling.
* **VAD vs. Semantic EoT & Turn-Taking:** 59.6% of human within-speaker pauses exceed 500 ms ([Evalgent, Oct 4, 2026](https://www.evalgent.com/blog/pipecat-interruption-strategy-smart-turn)). Acoustic VAD (Silero VAD) cannot distinguish mid-thought pauses from turn ends; native-audio EoT models ([LiveKit Turn Detector v1.0, Jun 17, 2026](https://livekit.com/blog/solving-end-of-turn-detection): 9.9% false-cutoff at 300 ms; [Pipecat Smart Turn v3.2, Jan 7, 2026](https://www.daily.co/blog/smart-turn-v3-2-handling-noisy-environments-and-short-responses/): 12 ms CPU across 23 languages including Hindi/Marathi) close this gap—though [Pipecat Issue #3844 (Feb 2026)](https://github.com/pipecat-ai/pipecat/issues/3844) showed 8 kHz resampling bugs silently break EoT.
* **Explicit Boundary:** Layer 1 text simulation (with ASR perturbation) validates **prompt logic, slot normalization, tool contracts, RERA grounding, and DNC exits** (~$0.02/call). It **cannot** validate acoustic barge-in (<300 ms), backchannel (*"haan/achha"*) suppression, TTS Indic pronunciation (UTMOS misses *"₹1.2 Cr"* / *"Wakad"* errors; [Saeki et al., 2022](https://arxiv.org/abs/2204.02152)), false empathy prosody, or SIP jitter—which require Layer 2 (recorded 8 kHz audio replay via Pipecat) and Layer 3 (live telephony).

---

## 5. Failure Analysis Methodology

1. **Open & Axial Coding:** Follow [Husain & Shankar (2025)](https://hamel.dev/blog/posts/evals-faq/why-is-error-analysis-so-important-in-llm-evals-and-how-is-it-performed.html): manually inspect 30–100 raw traces (open coding), synthesize mutually exclusive failure categories (axial coding), and re-align judges as criteria drift ([Shankar et al., 2024](https://arxiv.org/abs/2404.12272)).
2. **Stage-Level Root-Cause Attribution:** Attribute every failure to the *earliest* diverging stage (`ASR_NOISE -> SLOT_EXTRACT -> KB_RETRIEVAL -> LLM_REASONING -> TOOL_EXEC -> TTS`), mirroring [VoiceAgentBench (2025)](https://arxiv.org/html/2510.07978v1).
3. **Semantic Clustering of Critiques:** Embed failure *rationales* (not raw transcripts) to cluster novel production regressions before human review.

---

## 6. Adjacent Engineering Fields Investigated (Adopt / Adapt / Reject)

| Field & Primary Source | Original Purpose & Mechanism | PropEval Application | Detects | Limitations | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Property-Based Testing** ([QuickCheck, 2000](https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf); [Hypothesis](https://hypothesis.readthedocs.io/)) | Test universal invariants across random generated inputs with shrinking | Fuzz currency normalizers (`₹15L–₹25Cr`), fixture precedence, and FSM state transitions | Parsing edge cases, constraint & state-machine bugs | Expensive to shrink across live LLM calls | **ADOPT** (deterministic layers) |
| **Mutation Testing** ([Jia & Harman, IEEE TSE 2011](https://www.computer.org/csdl/journal/ts/2011/05/tts2011050649/13rRUyogGBV)) | Inject deliberate faults (mutants) to measure test-suite kill rate | Inject 10–20 curated prompt/tool mutants (drop DNC rule, stale RERA date, swap lakh/crore) | Weak eval suites & rubber-stamp judges | High cost if run per PR; equivalent mutants | **ADAPT** (weekly meta-eval) |
| **Differential Testing** ([McKeeman, 1998](https://www.semanticscholar.org/paper/Differential-Testing-for-Software-McKeeman/fc881e8d0432ea8e4dd5fda4979243cac5e4b9e3)) | Run identical inputs on two versions and flag behavioral divergence | Paired Prompt V1 vs V2 on identical FSM seeds & fixtures | Silent regressions & verbosity creep | Blind to bugs present in *both* V1 and V2 | **ADOPT** (core PR workflow) |
| **Metamorphic Testing** ([Chen et al., ACM CSUR 2018](https://ro.uow.edu.au/articles/journal_contribution/Metamorphic_Testing_A_Review_of_Challenges_and_Opportunities/27764520)) | Verify invariance relations when no ground-truth oracle exists | Assert `"1.2 cr"` $\equiv$ `"120 lakh"` $\equiv$ `"ek crore bees lakh"` & Romanized/Devanagari equivalence | Hinglish & Indian unit fragility | Both variants can fail identically | **ADOPT** (first-class suite) |
| **Fuzzing & Fault Injection** ([Chaos Engineering](https://principlesofchaos.org/)) | Inject malformed inputs & infrastructure failures | Domain-aware 8 kHz Indian ASR confusion matrix + mocked `503`/timeout tool errors | Invented actions & ASR error cascades | Random byte-fuzzing wastes tokens | **ADAPT** (domain noise + tool mocks) |
| **Information Retrieval Eval** ([Järvelin & Kekäläinen, 2002](https://faculty.cc.gatech.edu/~zha/CS8803WST/dcg.pdf)) | Evaluate ranked retrieval via Recall@k, MRR, NDCG@k | Grade property KB retrieval independently from LLM generation | Hinglish-to-English brochure retrieval misses | Requires relevance labels (qrels) | **ADOPT** (decoupled KB layer) |
| **Test Case Prioritization** ([Rothermel et al., 2001](https://digitalcommons.unl.edu/csearticles/9/)) | Order regression tests to maximize early fault detection (APFD) | Run historically flaky & high-severity DNC/RERA cases first in CI | Faster CI feedback under token budgets | Needs run-history metadata | **ADAPT** (Tier 1 CI ordering) |
| **Monte Carlo Simulation** ([Wadi & Fredette, EMNLP 2025](https://aclanthology.org/2025.findings-emnlp.500/)) | Repeated stochastic rollouts to estimate distribution & entropy | $K=3\text{–}5$ trials per scenario computing `pass^k` & cluster CIs | Flaky prompts passing by luck | Multiplies LLM token cost by $K$ | **ADOPT** (Tier 2 release gate) |
| **Sequential Testing (mSPRT)** ([Johari et al., 2022](https://pubsonline.informs.org/doi/10.1287/opre.2021.2135)) | Always-valid $p$-values via mixture likelihood ratios | Early-abort large ($N \ge 100$) runs on catastrophic harm (-20 pp) | Saves API spend on broken prompts | Wider bounds; useless at $N=20$ | **ADAPT** (harm-only early stop) |
| **Statistical Process Control** ([NIST EWMA](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)) | $p$-charts & EWMA charts detecting process drift over time | Longitudinal drift monitoring on nightly fixed canary suites | Silent upstream LLM/STT provider drift | Needs stable Phase I baseline | **ADOPT** (post-MVP canary) |
| **HCI Turn-Taking Norms** ([Stivers et al., PNAS 2009](https://www.pnas.org/doi/10.1073/pnas.0903616106)) | Universal 0–200 ms modal turn gap; >700 ms signals dispreference | Defines TTFA & turn-latency SLO budgets (500 ms p50, <1000 ms p95) | Latency-induced buyer hang-ups | Requires Layer 2/3 audio measurement | **ADOPT** (SLO design basis) |
