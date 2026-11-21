"""Tests for PropEval Paired Statistics and Bootstrap Engine.

Validates:
- Exact McNemar binomial test + Newcombe Method 10 CI.
- Wilcoxon signed-rank test + rank-biserial correlation.
- Two-Stage Cluster BCa bootstrap & percentile fallback.
- Quarantined-pair exclusion and SMOKE_TEST_UNDERPOWERED tagging.
- Holm-Bonferroni step-down correction.
- pass^k production consistency metric.
"""

from __future__ import annotations

import numpy as np
import pytest

from backend.app.evaluation.calibration import (
    compute_judge_calibration,
    compute_ppi_plus_plus,
    compute_rogan_gladen,
)
from backend.app.stats.bootstrap import two_stage_cluster_bca_bootstrap
from backend.app.stats.paired_tests import (
    compute_exact_mcnemar_test,
    compute_pass_at_k,
    compute_wilcoxon_paired_test,
    exclude_quarantined_pairs,
    holm_bonferroni_correction,
)


def test_quarantined_pair_exclusion_and_underpowered_tag():
    # 25 scenarios, but 2 scenarios have one arm quarantined
    v1_results = [{"id": f"s_{i}", "status": "COMPLETED"} for i in range(25)]
    v2_results = [{"id": f"s_{i}", "status": "COMPLETED"} for i in range(25)]

    # Scenario 3: V1 crashed with simulation fault
    v1_results[3]["status"] = "QUARANTINED_SIM_FAULT"
    # Scenario 7: V2 crashed with simulation fault
    v2_results[7]["status"] = "QUARANTINED_SIM_FAULT"

    clean_v1, clean_v2, eff_n, is_underpowered = exclude_quarantined_pairs(v1_results, v2_results)

    # Both arms dropped for scenario 3 and 7
    assert eff_n == 23
    assert len(clean_v1) == 23
    assert len(clean_v2) == 23
    # N = 23 < 50 => SMOKE_TEST_UNDERPOWERED is True
    assert is_underpowered is True

    # When N >= 50
    v1_large = [{"status": "COMPLETED"} for _ in range(55)]
    v2_large = [{"status": "COMPLETED"} for _ in range(55)]
    _, _, eff_large, underpowered_large = exclude_quarantined_pairs(v1_large, v2_large)
    assert eff_large == 55
    assert underpowered_large is False


def test_exact_mcnemar_and_newcombe_known_distribution():
    # Table: a=15 (both pass), b=10 (v1 fail -> v2 pass), c=1 (v1 pass -> v2 fail), d=4 (both fail)
    # N = 30
    v1 = [1] * 15 + [0] * 10 + [1] * 1 + [0] * 4
    v2 = [1] * 15 + [1] * 10 + [0] * 1 + [0] * 4

    result = compute_exact_mcnemar_test(v1, v2)

    # Effective N is 30 (< 50 => underpowered)
    assert result.effective_n == 30
    assert result.is_underpowered is True

    # Discordant pairs: b=10, c=1 (sum = 11)
    # Exact two-sided binomial p-value for min(b, c)=1 out of 11:
    # 2 * (comb(11, 0) + comb(11, 1)) * 0.5^11 = 2 * (1 + 11) / 2048 = 24 / 2048 = 0.01171875
    assert result.p_value == pytest.approx(0.01171875, rel=1e-5)

    # Risk difference: (10 - 1) / 30 = 9 / 30 = 0.30
    assert result.risk_difference == pytest.approx(0.30, abs=1e-5)

    # Newcombe Method 10 CI should contain 0.30 and be within [-1, 1]
    assert result.ci_lower < 0.30 < result.ci_upper
    assert result.ci_lower >= -1.0
    assert result.ci_upper <= 1.0


def test_exact_mcnemar_ties_and_zero_discordant():
    # Identical runs: b=0, c=0
    v1 = [1, 0, 1, 1, 0]
    v2 = [1, 0, 1, 1, 0]
    res = compute_exact_mcnemar_test(v1, v2)
    assert res.p_value == 1.0
    assert res.risk_difference == 0.0
    assert res.table.v1_fail_v2_pass_b == 0
    assert res.table.v1_pass_v2_fail_c == 0


def test_wilcoxon_paired_test():
    # Synthetic paired data where V2 is strictly better than V1
    rng = np.random.default_rng(42)
    v1 = rng.normal(loc=5.0, scale=1.0, size=60)
    v2 = v1 + rng.normal(loc=0.8, scale=0.3, size=60)  # Clear positive shift

    res = compute_wilcoxon_paired_test(v1, v2)
    assert res.effective_n == 60
    assert res.is_underpowered is False
    assert res.p_value < 1e-4
    assert res.mean_difference > 0.5
    assert res.rank_biserial_r > 0.8  # Strong positive rank-biserial correlation
    assert res.cohens_dz > 1.0


def test_wilcoxon_identical():
    v1 = [2.0, 3.5, 4.0, 1.2]
    v2 = [2.0, 3.5, 4.0, 1.2]
    res = compute_wilcoxon_paired_test(v1, v2)
    assert res.p_value == 1.0
    assert res.mean_difference == 0.0
    assert res.rank_biserial_r == 0.0


def test_two_stage_cluster_bca_bootstrap():
    # 30 scenarios, K=3 trials per scenario with known positive shift of +0.25
    rng = np.random.default_rng(123)
    n_scenarios = 30
    k_trials = 3

    base = rng.uniform(0.3, 0.7, size=(n_scenarios, 1))
    v1 = np.clip(base + rng.normal(0, 0.05, size=(n_scenarios, k_trials)), 0, 1)
    v2 = np.clip(base + 0.25 + rng.normal(0, 0.05, size=(n_scenarios, k_trials)), 0, 1)

    boot = two_stage_cluster_bca_bootstrap(v1, v2, n_resamples=1000, random_state=42)

    assert boot.ci_lower < boot.estimate < boot.ci_upper
    assert boot.ci_lower > 0.10  # True shift is ~0.25
    assert boot.method_used in ("bca", "percentile_fallback")
    assert boot.n_resamples == 1000


def test_two_stage_bootstrap_fallback_on_heavy_ties():
    # Degenerate tied discrete data where jackknife variance is tiny or acceleration degenerates
    v1 = np.zeros((20, 2))
    v2 = np.ones((20, 2))
    boot = two_stage_cluster_bca_bootstrap(v1, v2, n_resamples=500, random_state=42)
    assert boot.estimate == 1.0
    assert boot.ci_lower == 1.0
    assert boot.ci_upper == 1.0


def test_holm_bonferroni_multi_testing_correction():
    # 4 metrics: Task Completion, Extraction F1, Latency, Cost
    pvals = {
        "task_completion": 0.005,
        "extraction_f1": 0.015,
        "latency_p95": 0.040,
        "cost_usd": 0.200,
    }

    results = holm_bonferroni_correction(pvals, alpha=0.05)

    # m = 4:
    # rank 1: p = 0.005 <= 0.05 / 4 = 0.0125 -> Significant
    # rank 2: p = 0.015 <= 0.05 / 3 = 0.0167 -> Significant
    # rank 3: p = 0.040 > 0.05 / 2 = 0.0250 -> Not significant
    # rank 4: p = 0.200 > 0.05 / 1 = 0.0500 -> Not significant
    assert results["task_completion"]["significant"] is True
    assert results["extraction_f1"]["significant"] is True
    assert results["latency_p95"]["significant"] is False
    assert results["cost_usd"]["significant"] is False


def test_pass_at_k_computation():
    # 3 scenarios, K=3 trials each
    # Scenario 0: [1, 1, 1] -> pass^3 = 1.0
    # Scenario 1: [1, 1, 0] -> pass^3 = 0.0
    # Scenario 2: [0, 0, 0] -> pass^3 = 0.0
    trials = np.array([
        [1, 1, 1],
        [1, 1, 0],
        [0, 0, 0],
    ])

    pass_all = compute_pass_at_k(trials, k=3)
    np.testing.assert_array_equal(pass_all, [1, 0, 0])

    # Unbiased pass^2 for scenario 1: comb(2, 2) / comb(3, 2) = 1/3
    pass_k2 = compute_pass_at_k(trials, k=2)
    assert pass_k2[0] == 1.0
    assert pass_k2[1] == pytest.approx(1.0 / 3.0)
    assert pass_k2[2] == 0.0


def test_calibration_and_rogan_gladen():
    # Golden set of 40 samples
    y_true = [1] * 20 + [0] * 20
    # High accuracy judge (18/20 on positive, 18/20 on negative)
    y_pred = [1] * 18 + [0] * 2 + [1] * 2 + [0] * 18

    calib = compute_judge_calibration(y_true, y_pred)
    assert calib.is_calibrated is True
    assert calib.cohens_kappa >= 0.70
    assert calib.tpr == pytest.approx(0.90)
    assert calib.tnr == pytest.approx(0.90)

    # Clamped Rogan Gladen
    # Observed rate in unlabelled run is 0.60
    rg = compute_rogan_gladen(0.60, tpr=0.90, tnr=0.90, kappa=calib.cohens_kappa)
    assert rg.status == "CALIBRATED"
    # pi_hat = (0.60 + 0.90 - 1) / (0.90 + 0.90 - 1) = 0.50 / 0.80 = 0.625
    assert rg.calibrated_rate == pytest.approx(0.625)

    # Uncalibrated judge fallback
    bad_rg = compute_rogan_gladen(0.60, tpr=0.52, tnr=0.51, kappa=0.40)
    assert bad_rg.status == "UNCALIBRATED_ADVISORY_ONLY"
    assert bad_rg.calibrated_rate == 0.60


def test_ppi_plus_plus():
    rng = np.random.default_rng(42)
    # Unlabelled: 200 predictions
    unlabelled = rng.uniform(0.6, 0.9, size=200)
    # Labelled: 30 paired predictions and truth
    lab_pred = rng.uniform(0.6, 0.9, size=30)
    lab_truth = np.clip(lab_pred + rng.normal(0, 0.05, size=30), 0, 1)

    ppi = compute_ppi_plus_plus(unlabelled, lab_pred, lab_truth)
    assert 0.0 <= ppi.theta_ppi <= 1.0
    assert ppi.ci_lower <= ppi.theta_ppi <= ppi.ci_upper
