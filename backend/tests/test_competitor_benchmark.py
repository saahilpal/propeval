"""Regression tests for Wave 2 Benchmark B: Laya vs Open-Source Competitors."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def competitor_results() -> dict:
    repo_root = Path(__file__).resolve().parent.parent.parent
    results_path = repo_root / "benchmarks" / "competitor_results.json"
    assert results_path.exists(), f"competitor_results.json not found at {results_path}"
    with open(results_path, encoding="utf-8") as f:
        return json.load(f)


def test_test_data_integrity(competitor_results: dict):
    meta = competitor_results["benchmark_metadata"]
    assert meta["test_sample_count"] == 252
    assert meta["dataset_sha256"] == "ff45cbfff04b6e082050792c8252ffa3f3bda100e41ba4f98ce5b32f92197d60"


def test_laya_production_sla_conformance(competitor_results: dict):
    laya = competitor_results["systems"]["prop_eval_real_estate_laya"]
    assert laya["macro_f1"] > 0.95
    assert laya["fail_class_recall"] > 0.95
    assert laya["ece"] < 0.05, f"ECE {laya['ece']} violated 0.05 SLA"
    assert laya["latency"]["p95_ms"] < 1.0, f"Latency {laya['latency']['p95_ms']} violated 1.0ms SLA"


def test_laya_latency_speedup_vs_competitors(competitor_results: dict):
    speedup = competitor_results["speedup_vs_competitors"]
    assert speedup["speedup_vs_mdeberta_ratio"] > 1000.0
    assert speedup["speedup_vs_setfit_ratio"] > 10.0
    assert speedup["artifact_size_reduction_ratio_vs_mdeberta"] > 500.0


def test_all_tasks_present_and_valid(competitor_results: dict):
    expected_tasks = {"dnc_refusal", "action_confirmation", "prompt_injection", "objection_class"}
    for sys_key, sys_data in competitor_results["systems"].items():
        assert set(sys_data["per_task"].keys()) == expected_tasks
        for task, m in sys_data["per_task"].items():
            assert 0.0 <= m["macro_f1"] <= 1.0
            assert 0.0 <= m["fail_recall"] <= 1.0
            assert 0.0 <= m["ece"] <= 1.0
            assert 0.0 <= m["brier"] <= 1.0
