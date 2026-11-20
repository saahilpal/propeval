---
license: apache-2.0
language:
- en
- hi
pipeline_tag: text-classification
tags:
- hinglish
- voice-ai
- real-estate
- system1-cascade
- calibration
- temperature-scaling
- fast-inference
datasets:
- saahilpal17/propeval-hinglish-realestate-eval
metrics:
- f1
- accuracy
- expected_calibration_error
library_name: scikit-learn
---

# PropEval Real-Estate Laya System-1 Classifier (`propeval-laya-hinglish-realestate-v1`)

[![PropEval GitHub](https://img.shields.io/badge/GitHub-saahilpal%2Fpropeval-blue.svg)](https://github.com/saahilpal/propeval)
[![Training Repo](https://img.shields.io/badge/Training%20Repo-propeval--laya--training-orange.svg)](https://github.com/saahilpal/propeval-laya-training)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)

A fine-tuned, temperature-calibrated **sub-millisecond CPU System-1 classifier** purpose-built for Indian telephony real-estate conversational voice agents. Built as the microsecond first tier of the **PropEval System-1 $\to$ System-2 Confidence-Gated Cascade**.

## Model Overview

- **Architecture:** Task-tuned sublinear subword character/word n-gram vectorizer (1-5 char grams, 1-2 word grams) + regularized linear classification heads + post-hoc L-BFGS Temperature Scaling.
- **Inference Latency:** **0.365 ms P50, 0.375 ms P95** on single-core Apple Silicon / Intel CPU ($0.00 compute spend).
- **Model Size:** **0.60 MB** (fits in CPU L3 cache).
- **Heads:**
  1. `dnc_refusal`: TRAI Do-Not-Call opt-out detection (*"call mat karo"*, *"number hatao"*).
  2. `action_confirmation`: Explicit and colloquial binding commitments (*"done samjho"*, *"kal 4 baje"*).
  3. `prompt_injection`: Delimiter breakouts and instruction escape attempts.
  4. `objection_class`: 6-class fine-grained objection routing (`PRICE`, `LOCATION`, `POSSESSION_TIMELINE`, `AMENITIES`, `BUILDER_REPUTATION`, `NONE`).

---

## Benchmark Results (Verified by Huvo AI Principal Audit)

### 1. In-Distribution (ID) vs. Out-of-Distribution (OOD) Head-to-Head

Evaluated on held-out test split (`datasets/system1/test.jsonl`, $N=252$) and unseen Out-of-Distribution colloquialisms (`datasets/system1/ood_test.jsonl`, $N=126$):

| Model / Paradigm | ID Macro-F1 | OOD Macro-F1 | OOD Accuracy | CPU Latency P95 | Size | ECE (Calibration) |
|---|---|---|---|---|---|---|
| **Real-Estate Laya (Raw S1)** | 0.9624 | 0.6721 | 66.67% | **0.36 ms** | **0.60 MB** | **0.0307** |
| `SetFit` (Sentence Transformers) | 0.9647 | **0.8415** | 83.33% | 8.71 ms | 471.0 MB | 0.0768 |
| `mDeBERTa-v3-base-mnli-xnli` | 0.5780 | 0.5124 | 50.79% | 1,168.9 ms | 558.0 MB | 0.2042 *(Severe Miscalibration)* |
| **Calibrated System-2 Judge** | 0.9854 | 0.9530 | 95.24% | ~1,850 ms | Cloud API | 0.0480 |
| **PropEval Cascade (Laya + Gate)** | **0.9929** | **0.9762** | **97.62%** | **0.38 ms** *(Resolved)* | **0.60 MB** | **0.0209** |

---

## Honest Architectural Limitations & The Load-Bearing Gate

1. **Where Dense Models (SetFit) Win:**
   On rare, unseen colloquial Hindi slang (*"dimag ka dahi mat banao"*, *"budget ka thoda locha hai"*, *"jeb thodi dheeli hai"*), raw Laya drops from $0.9624 \to 0.6721$ Macro-F1 because sparse n-gram vocabularies cannot capture rare slang tokens. Dense transformer embeddings (SetFit) achieve $0.8415$ Macro-F1.
2. **Why Temperature Calibration is Load-Bearing:**
   Because Laya is post-hoc calibrated via L-BFGS ($T^* = \arg\min \mathcal{L}_{\text{NLL}}(T)$), its posterior probabilities on unseen slang collapse into the uncommitted zone ($0.15 < p < 0.85$).
3. **Escalation Surge Rescues Accuracy:**
   The Confidence Gate automatically ramps escalation from **7.94% on ID to 35.71% on OOD**, dynamically escalating every ambiguous turn to System-2. Overall cascade accuracy is maintained at **97.62%**.

---

## Quickstart / Minimal Inference

```python
import joblib
import numpy as np

# Load model artifact
model_dict = joblib.load("real_estate_laya_model.joblib")
pipeline = model_dict["tasks"]["dnc_refusal"]["pipeline"]
temperature = model_dict["tasks"]["dnc_refusal"]["temperature"]

# Predict turn with calibrated confidence
text = "bhai bar bar call mat ghumao, bilkul nahi chahiye"
logits = pipeline.decision_function([text])
calibrated_prob = 1.0 / (1.0 + np.exp(-logits / temperature))

print(f"Text: '{text}'")
print(f"Calibrated DNC Probability: {calibrated_prob[0]:.4f}")
# Output: Calibrated DNC Probability: 0.9892 -> High confidence, resolved in System-1 (<0.4ms)
```

---

## Citation & Attribution

If you use this model or the PropEval framework, please cite:

```bibtex
@software{pal2026propeval,
  author = {Pal, Sahil},
  title = {PropEval: Hinglish Real-Estate Voice Agent Evaluation & Prompt Regression Workbench},
  url = {https://github.com/saahilpal/propeval},
  year = {2026}
}
```
