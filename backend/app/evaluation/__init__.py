"""Evaluation package for PropEval: Layer 1, Layer 2, Layer 3 & Calibration."""

from __future__ import annotations

from backend.app.evaluation.cascade_router import (
    BINARY_TASK_CLASSES,
    OBJECTION_CLASSES,
    SUPPORTED_TASKS,
    CascadeDecision,
    CascadeRouter,
)
from backend.app.evaluation.deterministic import (
    evaluate_dnc_compliance,
    evaluate_invented_actions,
    evaluate_metamorphic_currency_invariance,
    evaluate_tool_schema_compliance,
)
from backend.app.evaluation.fact_verifier import evaluate_property_fact_grounding
from backend.app.evaluation.normalizers import (
    are_currencies_equivalent,
    parse_area_sqft,
    parse_bhk,
    parse_indian_currency,
)
from backend.app.evaluation.rubric_judge import (
    CrossFamilyError,
    PairwiseJudgment,
    RubricJudgment,
    evaluate_pairwise_with_position_swap,
    evaluate_single_rubric,
    get_model_family,
    verify_cross_family,
)

__all__ = [
    "BINARY_TASK_CLASSES",
    "CascadeDecision",
    "CascadeRouter",
    "CrossFamilyError",
    "OBJECTION_CLASSES",
    "PairwiseJudgment",
    "RubricJudgment",
    "SUPPORTED_TASKS",
    "are_currencies_equivalent",
    "evaluate_dnc_compliance",
    "evaluate_invented_actions",
    "evaluate_metamorphic_currency_invariance",
    "evaluate_pairwise_with_position_swap",
    "evaluate_property_fact_grounding",
    "evaluate_single_rubric",
    "evaluate_tool_schema_compliance",
    "get_model_family",
    "parse_area_sqft",
    "parse_bhk",
    "parse_indian_currency",
    "verify_cross_family",
]
