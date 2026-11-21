"""Minimal, zero-dependency standalone inference script for PropEval Real-Estate Laya System-1.

Runs in < 0.4 ms on single-core CPU.
"""

from __future__ import annotations

import argparse
from typing import Any

import joblib
import numpy as np


class LayaClassifier:

    def __init__(self, model_path: str = "real_estate_laya_model.joblib"):
        self.artifact = joblib.load(model_path)
        self.tasks = self.artifact.get("tasks", {})

    def predict_turn(self, text: str, task: str = "dnc_refusal") -> dict[str, Any]:
        if task not in self.tasks:
            raise ValueError(f"Task '{task}' not in available tasks: {list(self.tasks.keys())}")

        task_data = self.tasks[task]
        pipeline = task_data["pipeline"]
        temp = task_data.get("temperature", 1.0)

        if hasattr(pipeline, "decision_function"):
            df = pipeline.decision_function([text])
            if df.ndim == 1 or df.shape[1] == 1:
                logit = float(df[0])
                prob = 1.0 / (1.0 + np.exp(-logit / temp))
                pred_label = 1 if prob >= 0.5 else 0
                confidence = prob if pred_label == 1 else 1.0 - prob
                margin = abs(prob - 0.5) * 2.0
                classes = getattr(pipeline, "classes_", [0, 1]).tolist()
            else:
                scaled_logits = df[0] / temp
                exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
                probs = exp_logits / np.sum(exp_logits)
                top_idx = int(np.argmax(probs))
                classes = getattr(pipeline, "classes_", list(range(len(probs)))).tolist()
                pred_label = classes[top_idx]
                confidence = float(probs[top_idx])
                sorted_probs = np.sort(probs)
                margin = float(sorted_probs[-1] - sorted_probs[-2]) if len(sorted_probs) > 1 else confidence
        else:
            probs = pipeline.predict_proba([text])[0]
            top_idx = int(np.argmax(probs))
            classes = getattr(pipeline, "classes_", list(range(len(probs)))).tolist()
            pred_label = classes[top_idx]
            confidence = float(probs[top_idx])
            sorted_probs = np.sort(probs)
            margin = float(sorted_probs[-1] - sorted_probs[-2]) if len(sorted_probs) > 1 else confidence

        # Confidence Gating Rule (tau_high = 0.85, tau_low = 0.15, margin >= 0.70)
        is_confident = (confidence >= 0.85 or confidence <= 0.15) and (margin >= 0.70)
        routing_decision = "RESOLVED_BY_SYSTEM1" if is_confident else "ESCALATE_TO_SYSTEM2"

        return {
            "text": text,
            "task": task,
            "prediction": pred_label,
            "confidence": round(confidence, 4),
            "margin": round(margin, 4),
            "routing_decision": routing_decision,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PropEval Real-Estate Laya System-1 Inference")
    parser.add_argument("text", type=str, help="Customer telephony turn text")
    parser.add_argument("--task", type=str, default="dnc_refusal", choices=["dnc_refusal", "action_confirmation", "prompt_injection", "objection_class"])
    args = parser.parse_args()

    classifier = LayaClassifier()
    result = classifier.predict_turn(args.text, task=args.task)
    print(result)
