---
license: apache-2.0
language:
- en
- hi
task_categories:
- text-classification
tags:
- hinglish
- voice-ai
- real-estate
- speech-evaluation
- evaluation
- out-of-distribution
size_categories:
- 1K<n<10K
---

# PropEval Hinglish Real-Estate Telephony Evaluation Dataset (`propeval-hinglish-realestate-eval`)

[![PropEval GitHub](https://img.shields.io/badge/GitHub-saahilpal%2Fpropeval-blue.svg)](https://github.com/saahilpal/propeval)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)

A zero-PII, production-derived evaluation and calibration benchmark purpose-built for **telephony-based Hinglish real-estate voice AI agents**. It contains 1,806 stratified and globally deduplicated turns spanning customer compliance opt-outs, binding commitments, adversarial prompt injection attempts, and multi-class buyer objections.

## Dataset Structure & Splits

All records are globally deduplicated by normalized NFKC lowercase text SHA-256 with **zero collision across splits**:

| Split | File | Records | SHA-256 Cryptographic Checksum | Purpose |
|---|---|---|---|---|
| **Train** | `train.jsonl` | 1,176 | `def11441bb2fff4ccae831c3d09851f50091214107a4d84ba1a1461d31c07a41` | Balanced training partition across 4 tasks |
| **Validation** | `val.jsonl` | 252 | `01aeb881f657da6478f114244727efa2c6b61cdd2dc6d1c505d7b67134e7fb4d` | Model hyperparameter selection & calibration |
| **Test (ID)** | `test.jsonl` | 252 | `ff45cbfff04b6e082050792c8252ffa3f3bda100e41ba4f98ce5b32f92197d60` | Held-out in-distribution benchmark split |
| **Test (OOD)** | `ood_test.jsonl` | 126 | `b23d820eeaac003e19395440f1a0e9d15f91943c3e647f427ac06cecbd04c088` | Unseen regional Hinglish colloquialisms & slang |

---

## Tasks & Schema

Each row is a single JSON object with the following fields:
- `text` (*string*): The customer's conversational turn (Hinglish/Hindi/English code-switched text, e.g. *"1.2 cr chalega, but possession 2026 tak chahiye"*).
- `task` (*string*): Target classification head (`dnc_refusal`, `action_confirmation`, `prompt_injection`, or `objection_class`).
- `label` (*int* or *string*):
  - `dnc_refusal`: `1` (DNC Opt-Out) or `0` (Normal conversation).
  - `action_confirmation`: `1` (Binding commitment) or `0` (No binding action).
  - `prompt_injection`: `1` (Delimiter escape / injection attempt) or `0` (Benign turn).
  - `objection_class`: `PRICE`, `LOCATION`, `POSSESSION_TIMELINE`, `AMENITIES`, `BUILDER_REPUTATION`, or `NONE`.

---

## Data Provenance & Upstream Dataset Citations

This benchmark incorporates curated and normalized subsets of open-source research datasets alongside real-estate specific telephony turns:
1. **`ankitdhiman/colloquial-hinglish-conversations`** (HuggingFace, Apache 2.0 / MIT) — Indian conversational speech patterns and code-switching syntax.
2. **`DSMJ910/hinglish-instruct-10k`** (HuggingFace, Apache 2.0) — Instruction-following syntax and mixed Devanagari numerals.
3. **`AmazonScience/massive`** (`hi-IN` subset, CC-BY-4.0) — High-quality localized Hindi acoustic intent utterances.
4. **`deepset/prompt-injections`** & **`S-Labs/prompt-injection-dataset`** (Apache 2.0) — Adversarial delimiter and instruction breakout controls.

All telephone numbers, Aadhaar IDs, PAN numbers, and customer names have been **fully anonymized / synthetic** according to DPDP (Digital Personal Data Protection) standards. Zero real customer PII is present.

---

## Citation & Licensing

PropEval is distributed under the [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0).

```bibtex
@dataset{pal2026propeval_dataset,
  author = {Pal, Sahil},
  title = {PropEval Hinglish Real-Estate Telephony Evaluation Dataset},
  url = {https://huggingface.co/datasets/sahilpal/propeval-hinglish-realestate-eval},
  year = {2026}
}
```
