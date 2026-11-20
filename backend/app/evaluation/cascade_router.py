"""Confidence-Gated Cascade Router for PropEval Voice Agent Evaluation.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md, ADR-004, benchmarks/BENCHMARK_REPORT.md
Dual-Tier Decision Hierarchy:
- Tier 1: System-1 Fast Local Classifier (<25ms CPU SLA, $0 LLM cost).
- Tier 2: System-2 Frontier LLM Judge (Claude 3.5 / GPT-4o, ~$0.025 / turn).

Routing Policy:
- High confidence: $p \\ge \tau_{\text{high}}$ ($0.85$) or $p \\le \tau_{\text{low}}$ ($0.15$)
  (or decision margin $\\ge 0.70$) -> Instant System-1 resolution.
- Ambiguous / Low confidence: $\tau_{\text{low}} < p < \tau_{\text{high}}$ ($0.15 < p < 0.85$)
  -> Escalate to System-2 LLM Judge.
"""

from __future__ import annotations

import math
import time
from pathlib import Path
from typing import Any, Callable, Literal

import joblib
import numpy as np
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Task Head Definitions & Constants
# ---------------------------------------------------------------------------

DEFAULT_MODEL_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "models"
    / "system1"
    / "real_estate_laya_model.joblib"
)

OBJECTION_CLASSES: list[str] = [
    "PRICE_TOO_HIGH",
    "POSSESSION_DELAY",
    "RERA_APPROVAL",
    "LOCATION_CONNECTIVITY",
    "BUILDER_REPUTATION",
    "NONE",
]

BINARY_TASK_CLASSES: dict[str, tuple[str, str]] = {
    # (negative_class_0, positive_class_1)
    "dnc_refusal": ("NORMAL_CONVERSATION", "DNC_REFUSAL"),
    "action_confirmation": ("NO_ACTION_CONFIRMED", "ACTION_CONFIRMED"),
    "prompt_injection": ("BENIGN_QUERY", "PROMPT_INJECTION"),
}

SUPPORTED_TASKS = {
    "dnc_refusal",
    "action_confirmation",
    "prompt_injection",
    "objection_class",
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

class CascadeDecision(BaseModel):
    """Structured decision output from the Confidence-Gated Cascade Router."""

    task: str
    text: str
    predicted_label: str
    confidence: float = Field(ge=0.0, le=1.0)
    margin: float = Field(ge=0.0, le=1.0)
    calibrated_probability: float | dict[str, float]
    escalated_to_system2: bool
    escalation_reason: str | None = None
    cost_usd: float = Field(ge=0.0)
    latency_ms: float = Field(ge=0.0)
    system1_resolved: bool
    system_tier: Literal["SYSTEM_1", "SYSTEM_2"]
    status: Literal["SYSTEM1_RESOLVED", "ESCALATED_SYSTEM2"]
    system2_reasoning: str | None = None


# ---------------------------------------------------------------------------
# Cascade Router Engine
# ---------------------------------------------------------------------------

class CascadeRouter:
    """Confidence-Gated Cascade Router coordinating System-1 and System-2 tiers."""

    def __init__(
        self,
        model_path: str | Path | None = None,
        tau_high: float = 0.85,
        tau_low: float = 0.15,
        margin_threshold: float = 0.70,
        system2_cost_estimate: float = 0.025,
        max_latency_ms_sla: float = 25.0,
    ) -> None:
        self.tau_high = float(tau_high)
        self.tau_low = float(tau_low)
        self.margin_threshold = float(margin_threshold)
        self.system2_cost_estimate = float(system2_cost_estimate)
        self.max_latency_ms_sla = float(max_latency_ms_sla)

        resolved_path = Path(model_path) if model_path is not None else DEFAULT_MODEL_PATH
        if not resolved_path.exists():
            raise FileNotFoundError(
                f"System-1 model artifact not found at {resolved_path}. "
                "Ensure scripts/train_system1_models.py has been executed."
            )

        self.model_path = resolved_path
        self._heads: dict[str, dict[str, Any]] = joblib.load(resolved_path)

    @property
    def supported_tasks(self) -> set[str]:
        return set(self._heads.keys())

    def _predict_head(self, text: str, task: str) -> tuple[np.ndarray, bool, list[str]]:
        """Run feature extraction, logits, and temperature scaling on text for task."""
        if task not in self._heads:
            raise ValueError(
                f"Unknown task '{task}'. Supported tasks: {sorted(self._heads.keys())}"
            )

        head = self._heads[task]
        pipe = head["pipeline"]
        temp = max(float(head["temperature"]), 1e-3)
        is_multiclass = bool(head.get("is_multiclass", False))
        classes = list(head.get("classes", []))

        feats = pipe.named_steps["features"].transform([text])
        logits = pipe.named_steps["clf"].decision_function(feats)

        if is_multiclass:
            scaled = logits[0] / temp
            max_s = np.max(scaled)
            exp_s = np.exp(scaled - max_s)
            probs = exp_s / np.sum(exp_s)
            return probs, True, classes
        else:
            raw_logit = float(logits[0]) if logits.ndim == 1 else float(logits[0][0])
            scaled = raw_logit / temp
            clipped = max(-30.0, min(30.0, scaled))
            p1 = 1.0 / (1.0 + math.exp(-clipped))
            return np.array([1.0 - p1, p1]), False, classes

    def route_turn(self, text: str, task: str) -> CascadeDecision:
        """Evaluate a conversational turn with sub-25ms SLA and dual confidence gating."""
        t0 = time.perf_counter()
        probs, is_multiclass, classes = self._predict_head(text, task)
        latency_ms = (time.perf_counter() - t0) * 1000.0

        if not is_multiclass:
            # Binary classification
            neg_class, pos_class = BINARY_TASK_CLASSES.get(
                task, (classes[0], classes[1]) if len(classes) == 2 else ("0", "1")
            )
            p1 = float(probs[1])
            confidence = max(p1, 1.0 - p1)
            margin = abs(2.0 * p1 - 1.0)

            # High confidence Pass / Defect: resolved by System-1
            if p1 >= self.tau_high:
                return CascadeDecision(
                    task=task,
                    text=text,
                    predicted_label=pos_class,
                    confidence=round(confidence, 4),
                    margin=round(margin, 4),
                    calibrated_probability=round(p1, 4),
                    escalated_to_system2=False,
                    escalation_reason=None,
                    cost_usd=0.00,
                    latency_ms=round(latency_ms, 3),
                    system1_resolved=True,
                    system_tier="SYSTEM_1",
                    status="SYSTEM1_RESOLVED",
                )
            elif p1 <= self.tau_low:
                return CascadeDecision(
                    task=task,
                    text=text,
                    predicted_label=neg_class,
                    confidence=round(confidence, 4),
                    margin=round(margin, 4),
                    calibrated_probability=round(p1, 4),
                    escalated_to_system2=False,
                    escalation_reason=None,
                    cost_usd=0.00,
                    latency_ms=round(latency_ms, 3),
                    system1_resolved=True,
                    system_tier="SYSTEM_1",
                    status="SYSTEM1_RESOLVED",
                )
            else:
                # Ambiguous / Low confidence band (tau_low < p1 < tau_high)
                provisional_label = pos_class if p1 >= 0.5 else neg_class
                reason = (
                    f"Calibrated probability {p1:.4f} is in ambiguous band "
                    f"({self.tau_low}, {self.tau_high}) with margin {margin:.4f} "
                    f"< {self.margin_threshold}"
                )
                return CascadeDecision(
                    task=task,
                    text=text,
                    predicted_label=provisional_label,
                    confidence=round(confidence, 4),
                    margin=round(margin, 4),
                    calibrated_probability=round(p1, 4),
                    escalated_to_system2=True,
                    escalation_reason=reason,
                    cost_usd=self.system2_cost_estimate,
                    latency_ms=round(latency_ms, 3),
                    system1_resolved=False,
                    system_tier="SYSTEM_2",
                    status="ESCALATED_SYSTEM2",
                )
        else:
            # Multi-class classification (e.g. objection_class)
            sorted_indices = np.argsort(probs)[::-1]
            top1_idx = int(sorted_indices[0])
            top2_idx = int(sorted_indices[1])
            top1_p = float(probs[top1_idx])
            top2_p = float(probs[top2_idx])
            margin = top1_p - top2_p
            predicted_label = classes[top1_idx]

            prob_dict = {
                classes[i]: round(float(probs[i]), 4)
                for i in range(len(classes))
            }

            if top1_p >= self.tau_high or margin >= self.margin_threshold:
                return CascadeDecision(
                    task=task,
                    text=text,
                    predicted_label=predicted_label,
                    confidence=round(top1_p, 4),
                    margin=round(margin, 4),
                    calibrated_probability=prob_dict,
                    escalated_to_system2=False,
                    escalation_reason=None,
                    cost_usd=0.00,
                    latency_ms=round(latency_ms, 3),
                    system1_resolved=True,
                    system_tier="SYSTEM_1",
                    status="SYSTEM1_RESOLVED",
                )
            else:
                reason = (
                    f"Top class confidence {top1_p:.4f} < {self.tau_high} and margin "
                    f"{margin:.4f} < {self.margin_threshold}"
                )
                return CascadeDecision(
                    task=task,
                    text=text,
                    predicted_label=predicted_label,
                    confidence=round(top1_p, 4),
                    margin=round(margin, 4),
                    calibrated_probability=prob_dict,
                    escalated_to_system2=True,
                    escalation_reason=reason,
                    cost_usd=self.system2_cost_estimate,
                    latency_ms=round(latency_ms, 3),
                    system1_resolved=False,
                    system_tier="SYSTEM_2",
                    status="ESCALATED_SYSTEM2",
                )

    def route_batch(self, items: list[tuple[str, str]]) -> list[CascadeDecision]:
        """Process a list of (text, task) pairs sequentially."""
        return [self.route_turn(text, task) for text, task in items]

    def evaluate_with_cascade(
        self,
        text: str,
        task: str,
        system2_judge_fn: Callable[[str, str], tuple[str, str]] | None = None,
    ) -> CascadeDecision:
        """Evaluate with cascade gating, optionally dispatching to System-2 judge on escalation."""
        decision = self.route_turn(text, task)
        if not decision.escalated_to_system2:
            return decision

        if system2_judge_fn is not None:
            t0 = time.perf_counter()
            s2_label, s2_reasoning = system2_judge_fn(text, task)
            s2_latency = (time.perf_counter() - t0) * 1000.0

            return CascadeDecision(
                task=task,
                text=text,
                predicted_label=s2_label,
                confidence=decision.confidence,
                margin=decision.margin,
                calibrated_probability=decision.calibrated_probability,
                escalated_to_system2=True,
                escalation_reason=decision.escalation_reason,
                cost_usd=decision.cost_usd,
                latency_ms=round(decision.latency_ms + s2_latency, 3),
                system1_resolved=False,
                system_tier="SYSTEM_2",
                status="ESCALATED_SYSTEM2",
                system2_reasoning=s2_reasoning,
            )

        return decision
