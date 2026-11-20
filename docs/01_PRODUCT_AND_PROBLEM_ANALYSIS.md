# 01 — Product & Problem Analysis

## 1. Business Context: Huvo AI & Indian Real Estate Voice AI

[Huvo AI](https://huvo.ai/) (operated by [Ligatrix Technologies Private Limited](https://tracxn.com/d/legal-entities/india/ligatrix-technologies-private-limited/__asMwfU10xBoP-MWvOI8sJkLbdjeZNunIdn_wp6ka61c), incorporated September 2, 2025, operating out of Gurugram and Bengaluru) builds a vertical **Real Estate Sales OS** combining sub-minute outbound/inbound AI voice calling, lead qualification, 0–100 intent scoring, live calendar site-visit booking, WhatsApp/SMS/Gmail follow-ups, and an AI-native CRM across English, Hindi, Hinglish, Kannada, and Tamil ([Huvo How It Works](https://huvo.ai/how-it-works); [Integrations](https://huvo.ai/integrations); [Privacy Policy](https://huvo.ai/privacy), Nov 5, 2026).

### Why Real Estate Voice AI Is Uniquely Fragile
Unlike generic customer support chatbots, Indian real estate sales calls combine five high-stakes failure surfaces simultaneously:
1. **Intra-sentence Hinglish code-switching & Indian numeric systems:** Buyers routinely say *"Sir, ek point do crore ke aas-paas 3BHK chahiye Wakad side, possession kab tak milega?"* If an agent or post-call extractor fails to normalize `"1.2 cr"`, `"120 lakh"`, and `"ek point do crore"` to the exact same integer (`12000000`), CRM budget-tier routing breaks silently ([Sell.Do, Oct 7, 2026](https://www.sell.do/blog/ai-voice-agents-real-estate-lead-calling-india-2026)).
2. **8 kHz G.711 PSTN telephony degradation:** Indian PSTN calls run at 8 kHz narrowband with 8-bit quantization and heavy ambient noise (traffic, office chatter). General ASR WER climbs to **25–40%** ([Shunya Labs, Jun 15, 2026](https://www.shunyalabs.ai/blog/when-voice-bots-cant-understand-rx80); [arXiv:2606.09335, Jun 8, 2026](https://arxiv.org/html/2606.09335v1)), corrupting high-value entities (`"crore"` $\to$ `"core"`, RERA IDs, project names).
3. **High-liability factual grounding (RERA & pricing):** Misquoting carpet area vs. super built-up area, floor-rise charges, festive 20:80 payment plans, or RERA possession dates destroys buyer trust and exposes developers to legal/regulatory liability ([Antoc.ai, Oct 13, 2026](https://www.antoc.ai/blog/ai-for-real-estate-agents-india); [MagickVoice, Nov 5, 2026](https://www.magickvoice.com/blog/ai-voice-agent-real-estate-india)).
4. **TRAI DND & strict exit rules:** Huvo's [Terms of Service](https://huvo.ai/terms) (Oct 20, 2026) place TRAI/TCPA compliance liability squarely on customers. When an irritated buyer says *"mat call karo, wrong number hai"* or *"DND pe daalo"*, failing to invoke `mark_dnc` and exit cleanly within one turn triggers regulatory complaints and churn.
5. **Conversation-to-tool integrity:** Calling `book_site_visit` or `send_whatsapp_brochure` with malformed parameters—or verbally confirming a booking when the tool returned HTTP `503`—directly burns paid Meta/Google Ads leads ([StackAI, Feb 6, 2026](https://www.stackai.com/insights/prevent-ai-agent-hallucinations-in-production-environments)).

---

## 2. Primary Evidence of the Bottleneck at Huvo AI

| Signal Type | Verified Evidence | Implication for PropEval |
| :--- | :--- | :--- |
| **Manual QA Bottleneck** | [Huvo Prompt Engineer JD (Wellfound, reposted Oct 2026)](https://wellfound.com/jobs/4543729-prompt-engineer): 60–70% of role is prompt design, Hindi/English objection tuning, and *"Review call recordings, transcripts, outcomes, and failure cases to improve agent performance"* to cut hallucinations. | Prompt iteration is currently labor-intensive and vulnerable to silent regressions across 8 campaign types. |
| **Backend Eval Need** | [Huvo Backend Engineer JD (Wellfound, reposted Nov 2026)](https://wellfound.com/jobs/4544645-backend-engineer-python): Explicitly lists integration with external STT/TTS/LLM endpoints, **evaluation tooling**, retries, idempotency, and cost-performance tuning on Python/FastAPI/PostgreSQL/Redis. | Architecture must fit cleanly into a Python/FastAPI/PostgreSQL ecosystem and measure both quality and token/latency cost. |
| **Custom Onboarding Load** | [Huvo Forward Deployed Engineer JD (Weekday, Oct 31, 2026)](https://www.weekday.works/jobs/jobs-in-gurgaon-4): Embedded with real estate clients to turn custom workflows into scalable product features. | Every new developer/project onboarding requires fast verification of project-specific facts, pricing, and objections. |
| **Competitive Gap** | Global platforms ([Retell Batch Simulation, Nov 12, 2026](https://docs.retellai.com/test/batch-test-simulation); [Vapi Turn-Based Evals, Dec 3, 2025](https://vapi.ai/blog/evals)) and specialized QA vendors ([Hamming](https://hamming.ai/resources/voice-agent-testing-guide), [Cekura](https://www.cekura.ai/blogs/voice-ai-evals), [Coval](https://www.coval.ai/blog/the-three-layer-testing-framework-for-voice-ai-regression-adversarial-and-production-derived/)) treat automated pre-release simulation as standard; Huvo documents none publicly. | A domain-specific Hinglish real-estate regression workbench is a net-new capability, not a duplicate of Huvo's CRM or dialer. |

---

## 3. Stakeholders & Core Jobs-to-Be-Done

1. **Prompt Engineers & Forward Deployed Engineers (Primary Users):** Need to edit a system prompt or project fact sheet, run a paired comparison against the current production prompt (`V1 vs V2`), inspect exact deterministic failures and transcript diffs within minutes, and know whether a change is safe to ship.
2. **AI / Backend Engineers:** Need CI/CD merge gates (`propeval run --gate`) that block catastrophic regressions (DNC violations, broken JSON tool schemas, currency misparsing, RERA hallucinations), plus API/CLI hooks to turn real production failed calls into permanent regression tests.
3. **Engineering Leadership / Founder (e.g., CEO Tushar Khustule — IIT BHU CS, ex-WorldQuant/Mastercard/Pocket FM):** Demands statistically defensible evidence (paired confidence intervals, `pass^k` reliability, token/latency cost deltas, and human-calibrated judge agreement) rather than uncalibrated LLM "vibe scores."

---

## 4. Fundamental Technical Challenges Decomposed

| Challenge | What Must Be Deterministic (Code) | What Requires AI (LLM / ML) | What Remains Uncertain / Requires Human Anchors |
| :--- | :--- | :--- | :--- |
| **Scenario Execution** | FSM agenda transitions, slot-reveal gating, mock CRM/inventory DB state, ASR perturbation injection, turn caps, USD budget caps | Natural Hinglish surface realization of buyer utterances within FSM constraints; Target Voice Agent responses | Whether synthetic buyer phrasing fully mirrors real tier-2/tier-3 Indian homebuyer pragmatics |
| **Outcome Verification** | Indian currency/unit normalization (`1.2 cr == 12000000`), tool-call JSON schemas, DNC exit check, tool-error-vs-claim check, metamorphic invariance, numeric RERA/carpet-area lookup | Soft conversational rubrics (empathy, objection de-escalation, Hinglish register naturalness, simulator-fidelity auditing) | Evolving "good sales tone" criteria (criteria drift; [Shankar et al., 2024](https://arxiv.org/abs/2404.12272)) requiring human-labeled golden sets |
| **Statistical Decision** | Exact McNemar, Wilcoxon signed-rank, cluster/hierarchical bootstrap CIs, Holm-Bonferroni / BH-FDR, `pass^k`, mSPRT, EWMA SPC | None — statistics must be 100% deterministic via `SciPy`/`statsmodels` | Small-$N$ statistical power ($N=20$ cannot prove small $+5\text{–}10\text{ pp}$ gains) |
| **Voice Fidelity** | Latency histograms (TTFT, TTFA), entity error rate (SEER), audio resampling (`soxr_hq`) | ASR/TTS models, semantic EoT (Smart Turn / LiveKit v1) in Layer 2+ | Acoustic barge-in, prosody/false empathy, and 8 kHz G.711 PSTN carrier artifacts cannot be validated in Layer 1 text simulation |

---

## 5. Strict Scope Boundaries

* **In Scope for PropEval:** Versioned prompt & project-fixture registries; Hybrid FSM+LLM Hinglish buyer simulation; 8 kHz ASR perturbation & tool-fault injection; non-compensatory deterministic + calibrated rubric evaluation; paired statistical regression diffing & CI gating; production-call replay import; DPDP-compliant PII redaction; OpenTelemetry observability; and a clean adapter seam for future Pipecat/LiveKit Layer-2 audio replay.
* **Explicitly Out of Scope:** Building a real-estate CRM, WhatsApp inbox, live PSTN/Twilio outbound dialer, billing portal, or replacing Huvo's production orchestration engine.
