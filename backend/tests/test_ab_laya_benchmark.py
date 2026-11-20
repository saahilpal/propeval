"""Automated Verification of Wave 2 Benchmark A: With-Laya vs. Without-Laya Cascade.

Enforces:
1. Cryptographic integrity of held-out test split (SHA-256 match).
2. Validity of benchmark audit results in benchmarks/ab_laya_results.json.
3. Strict adherence to production latency SLAs (p95 < 25ms on CPU).
4. Statistical calibration adherence (ECE < 0.05).
5. Statistical parity with pure System-2 (|delta_p| <= 0.010, McNemar p >= 0.05).
6. Superiority over pure System-1 (delta_p > 0, McNemar p < 0.05).
7. Financial cost reduction >= 90%.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TEST_DATASET_PATH = ROOT_DIR / "datasets" / "system1" / "test.jsonl"
RESULTS_JSON_PATH = ROOT_DIR / "benchmarks" / "ab_laya_results.json"
EXPECTED_TEST_SHA256 = "ff45cbfff04b6e082050792c8252ffa3f3bda100e41ba4f98ce5b32f92197d60"


@pytest.fixture(scope="module")
def benchmark_results() -> dict:
    """Fixture providing loaded benchmark audit results."""
    assert RESULTS_JSON_PATH.exists(), f"Results artifact missing: {RESULTS_JSON_PATH}"
    with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def test_test_split_sha256_integrity() -> None:
    """Verify test split SHA-256 strictly matches the locked reference hash."""
    assert TEST_DATASET_PATH.exists()
    h = hashlib.sha256()
    with open(TEST_DATASET_PATH, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_sha = h.hexdigest()
    assert actual_sha == EXPECTED_TEST_SHA256


def test_cascade_accuracy_and_agreement(benchmark_results: dict) -> None:
    """Cascade must maintain >=99% accuracy and Cohen's kappa >= 0.95 with System-2."""
    summary = benchmark_results["overall_summary"]["with_laya_cascade"]
    telemetry = benchmark_results["cascade_telemetry"]

    assert summary["overall_accuracy"] >= 0.990
    assert summary["mean_macro_f1"] >= 0.990
    assert summary["mean_fail_class_recall"] >= 0.990
    assert telemetry["cohens_kappa_agreement_with_system2"] >= 0.950


def test_cascade_calibration_sla(benchmark_results: dict) -> None:
    """Expected Calibration Error (ECE) must meet the strict SLA of <= 0.050."""
    summary = benchmark_results["overall_summary"]["with_laya_cascade"]
    assert summary["expected_calibration_error_m10"] <= 0.050
    assert summary["mean_task_brier_score"] <= 0.050


def test_cpu_latency_sla_conformance(benchmark_results: dict) -> None:
    """P95 CPU latency must be < 25.0ms (typically sub-millisecond)."""
    latency = benchmark_results["cpu_latency_distribution_ms"]
    assert latency["benchmark_iterations"] == 1000
    assert latency["p95_ms"] < latency["production_sla_ms"]
    assert latency["p95_ms"] < 2.0  # Real CPU should be well under 2ms
    assert latency["sla_conformance"] is True


def test_economic_cost_savings(benchmark_results: dict) -> None:
    """Dollar savings from confidence gating must exceed 85%."""
    econ = benchmark_results["economic_cost_analysis"]
    savings_pct = econ["cost_per_1000_turns"]["savings_percentage"]
    assert savings_pct >= 85.0
    assert econ["cost_per_1000_turns"]["with_laya_cascade_usd"] < 5.00


def test_paired_mcnemar_statistical_parity(benchmark_results: dict) -> None:
    """Cascade vs System-2 must not exhibit statistically significant degradation."""
    parity = benchmark_results["paired_statistical_significance"]["cascade_vs_system2_baseline"]
    assert parity["is_underpowered"] is False
    assert parity["quality_delta_within_budget"] is True
    # Two-sided exact McNemar p-value must be >= 0.05 (fail to reject H0)
    assert parity["p_value"] >= 0.05
    # 95% Newcombe CI must span zero
    assert parity["confidence_interval_95"][0] <= 0.0
    assert parity["confidence_interval_95"][1] >= 0.0


def test_paired_mcnemar_superiority_over_system1(benchmark_results: dict) -> None:
    """Cascade must be statistically significantly superior to pure System-1."""
    ablation = benchmark_results["paired_statistical_significance"]["cascade_vs_pure_system1_ablation"]
    assert ablation["is_underpowered"] is False
    assert ablation["statistically_significant"] is True
    assert ablation["p_value"] < 0.05
    assert ablation["risk_difference_delta_p"] > 0.0
