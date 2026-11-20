# 18 — Assumptions, Unresolved Uncertainties & Open Questions

Per Section 7 of our engineering discipline, we explicitly preserve unresolved uncertainties and assumptions that require validation with Huvo AI's engineering or product team rather than fabricating internal knowledge.

---

## 1. Key Technical & Product Assumptions

| ID | Assumption | Risk if Wrong | Mitigation Built into PropEval |
| :--- | :--- | :--- | :--- |
| **A-01** | Huvo AI does not currently operate an automated pre-release Hinglish prompt regression workbench (inferred from Oct 2026 Prompt JD & zero public QA docs). | If Huvo already has a private internal harness, PropEval's positioning shifts from "greenfield tool" to "domain-specific statistical & FSM upgrade." | Modular adapters (`TargetAgentAdapter`, `stats/`, `evaluation/`) allow adopting individual layers (e.g., FSM simulator or statistical gating) independently. |
| **A-02** | Target agents expose either a prompt+tools configuration or an HTTP/WebSocket staging endpoint accepting text turns. | If Huvo's agent is tightly coupled to Twilio Media Streams without a text-turn seam, Layer-1 live webhook testing requires a thin shim. | `TargetAgentAdapter` supports local prompt replay immediately and leaves a clean seam for `PipecatAudioAgentAdapter` in Layer 2. |
| **A-03** | Typical Indian real-estate qualification calls complete within 8–15 turns (~2–3 minutes). | Longer negotiation calls increase token cost and simulator drift risk. | Configurable `max_turns`, semantic stall detector, and atomic `max_budget_usd` circuit breaker prevent runaway spend. |
| **A-04** | Cross-family commercial LLMs (e.g., Gemini 2.5 Flash/Pro, GPT-4.1, Llama 3.3 via Groq) remain available under ZDR terms with acceptable Hinglish quality. | Provider pricing or Hinglish quality shifts could degrade simulator realism or judge $\kappa$. | Official SDKs behind thin `LLMProvider` Protocol allow 50-line swaps to Sarvam AI, Anthropic, or self-hosted vLLM. |

---

## 2. Unresolved Uncertainties (Preserved Disagreements from Multi-Perspective Research)

1. **Per-Variant vs. Pooled Judge Calibration Cost:** Statistical rigor requires estimating judge TPR/TNR *separately* for Prompt V1 and Prompt V2 when applying Rogan–Gladen bias adjustment (since judge error rates can shift across prompt styles). However, human-labeling 30+ V2 transcripts on *every* minor prompt edit is operationally infeasible for a 10-person startup. **Current compromise:** Calibrate on a frozen 30–50 transcript golden set per major prompt family and treat Layer 3 rubric scores as *advisory* unless re-calibrated, while relying on Layer 1/2 deterministic oracles for hard CI merge gates.
2. **Real-World Indian Hinglish ASR Confusion Matrix:** Published benchmarks prove 15–40% WER on 8 kHz Indian telephony, but exact error distributions depend heavily on Huvo's actual STT vendor (Deepgram vs. Sarvam vs. Whisper vs. Azure). MVP perturbation rules are educated approximations until seeded from Huvo's actual anonymized audio/transcript pairs.
3. **Optimal Trial Count $K$ vs. CI Budget:** Running $K=5$ trials on $N=100$ scenarios = 1,000 simulated conversations per release (~$15–$25 and 10–15 min). Whether Huvo prefers $N=100, K=3$ nightly or $N=50, K=5$ depends on their actual prompt deployment frequency.

---

## 3. High-Signal Validation Questions for Huvo AI's Team (Interview Leverage)

1. *"When a Prompt Engineer edits a Hindi/Hinglish objection-handling script today, how do you verify it didn't regress budget extraction or DNC exit rules on existing developer campaigns?"*
2. *"Which STT/TTS stack and telephony carrier (Twilio vs. Exotel) currently drive the largest share of your Hinglish entity misparses—especially lakh/crore numbers and project names?"*
3. *"Do your project facts (floor-rise, carpet area, RERA possession slabs) live in structured prompt templates or a vector/hybrid knowledge base, and how often do builder price revisions cause stale quotes?"*
4. *"How frequently do async WhatsApp Cloud API errors (`131026`/`131049`) or CRM webhook timeouts create a gap between what the agent promised on the call and what actually landed in the buyer's WhatsApp?"*
