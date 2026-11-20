---
name: systematic-debugging
description: "Root cause isolation workflow based on obra/superpowers: reproduce failure first, form falsifiable hypothesis, verify root cause before editing code, and confirm fix with regression test."
---

# Systematic Debugging Protocol

## 1. The Core Rule
Never guess or attempt symptom-patching. If a test fails, a bug is reported, or an unexpected regression occurs:
1. **Reproduce deterministically:** Write a minimal reproduction test or script that fails consistently.
2. **Inspect evidence:** Read the exact stack trace, query execution plan, or network payload. Never hypothesize without data.
3. **Form falsifiable hypothesis:** State clearly: "If X is the root cause, then modifying or mocking Y will yield Z."
4. **Fix the root cause:** Make the minimal required architectural or code fix. Do not introduce speculative abstractions.
5. **Verify regression immunity:** Run the full test suite and confirm the reproduction test now passes.
