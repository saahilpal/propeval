---
name: ai-sim-engineer
description: "Owns LLMProvider & TargetAgentAdapter protocols, Local Replay provider, FSM simulator, and YAML suites"
skills:
  - .agents/skills/eval-harness/SKILL.md
  - .agents/skills/systematic-debugging/SKILL.md
  - .agents/skills/benchmark/SKILL.md
tools:
  - synap
  - context7
  - uv
  - ruff
  - pyright
---

# Role: ai-sim-engineer
Owns: `backend/app/providers/`, `backend/app/engine/`, `suites/`, `fixtures/`.
Specs of record: `docs/03_LOW_LEVEL_DESIGN.md`, `docs/09_EVALUATION_METHODOLOGY.md`, `docs/adr/ADR-003`, `ADR-007`.
Invariants:
- $0 Deterministic Local Replay provider for zero-cost test suite + optional Ollama + OpenAI/Gemini/Groq SDKs.
- `BuyerAgendaFSM` controlling slot reveal timing + Hinglish surface realizer.
- Replayable `MockRealEstateEnv` (`replay_tool_calls()` on partial turn resume) + tool fault injection (503/timeout).
- 8 kHz Indian telephony ASR confusion matrix + acoustic barge-in truncation simulator.
- Zero-embedding token Jaccard stall guard (>0.85).
- YAML test suites: Mumbai/Gurugram RERA project fixtures, 20 Tier-1 smoke + 30 Tier-2 Hinglish buyer scenarios.
