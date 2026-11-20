---
name: deep-engineering-research
description: Primary-source research methodology for AI evaluation, frontier LLM failure modes, anti-cheat mechanisms, and lightweight local defenses.
---

# Deep Engineering Research Protocol

This skill enforces strict, high-signal research methodology for AI evaluation systems, prompt regression engines, and adversarial robustness.

## Core Rules

1. **Primary Sources Only:**
   - arXiv papers, peer-reviewed ML conferences (NeurIPS, ICML, ICLR), and official research blogs (Anthropic, OpenAI, DeepMind).
   - High-signal practitioner engineering posts (Hamel Husain, Shreya Shankar, Eugene Yan, Chip Huyen) and authoritative OSS source implementations.
   - Reject synthetic marketing summaries, SEO linkfarms, and unsubstantiated medium posts.

2. **Always Seek Counter-Evidence & Failure Modes:**
   - Every recommended technique must be cross-examined: Where does it break? What are its false-positive failure modes?
   - How can an adversary game or cheat this metric?

3. **Scoring Rubric for Discovered Tools & Classifiers:**
   - **$0 Local CPU Feasibility:** Can it run deterministically in < 10ms on a single modern CPU without GPU dependencies or cloud API calls?
   - **License:** Permissive OSS (MIT, Apache 2.0, BSD).
   - **Maintenance & Stability:** Modern (2024–2026), well-tested, lean dependencies.
   - **Signal-to-Bloat Ratio:** Zero giant black-box frameworks; prefer focused mathematical primitives and targeted algorithms over bloated monolithic wrappers.
