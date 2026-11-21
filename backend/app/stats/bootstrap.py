"""Two-Stage Hierarchical / Cluster BCa Bootstrap for PropEval.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md & ADR-005
Handles:
- Cluster-level resampling of N scenarios (Stage 1).
- Within-cluster resampling of K trials (Stage 2) to eliminate pseudoreplication.
- Bias-Corrected and Accelerated (BCa) confidence intervals.
- Automatic robust fallback to percentile bootstrap on ties / small N / NaN.
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
from scipy import stats


class BootstrapResult(NamedTuple):
    estimate: float
    ci_lower: float
    ci_upper: float
    standard_error: float
    method_used: str  # "bca" | "percentile_fallback"
    n_resamples: int


def two_stage_cluster_bca_bootstrap(
    v1_trials: list[list[float]] | np.ndarray,
    v2_trials: list[list[float]] | np.ndarray,
    alpha: float = 0.05,
    n_resamples: int = 2000,
    random_state: int | None = 42,
) -> BootstrapResult:
    """Compute Two-Stage Cluster BCa Bootstrap CI for paired difference (V2 - V1).

    Stage 1: Resample N scenarios with replacement.
    Stage 2: Within each selected scenario, resample K trials with replacement.
    """
    rng = np.random.default_rng(random_state)

    arr_v1 = np.asarray(v1_trials, dtype=float)
    arr_v2 = np.asarray(v2_trials, dtype=float)

    if arr_v1.ndim == 1:
        arr_v1 = arr_v1[:, np.newaxis]
    if arr_v2.ndim == 1:
        arr_v2 = arr_v2[:, np.newaxis]

    n_scenarios, k_trials_v1 = arr_v1.shape
    n_scenarios_v2, k_trials_v2 = arr_v2.shape

    if n_scenarios != n_scenarios_v2:
        raise ValueError(f"Scenario count mismatch: {n_scenarios} vs {n_scenarios_v2}")

    if n_scenarios == 0:
        return BootstrapResult(
            estimate=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            standard_error=0.0,
            method_used="empty",
            n_resamples=0,
        )

    # Point estimate: mean difference across scenario means
    scenario_means_v1 = np.mean(arr_v1, axis=1)
    scenario_means_v2 = np.mean(arr_v2, axis=1)
    diffs = scenario_means_v2 - scenario_means_v1
    theta_hat = float(np.mean(diffs))

    # All differences exactly identical -> zero variance
    if np.allclose(diffs, diffs[0]):
        return BootstrapResult(
            estimate=theta_hat,
            ci_lower=theta_hat,
            ci_upper=theta_hat,
            standard_error=0.0,
            method_used="degenerate",
            n_resamples=n_resamples,
        )

    # Perform Two-Stage Resampling
    boot_thetas = np.empty(n_resamples, dtype=float)

    for b in range(n_resamples):
        # Stage 1: Resample N cluster indices
        cluster_idx = rng.integers(0, n_scenarios, size=n_scenarios)

        # Stage 2: Within each resampled cluster, resample K trials
        if k_trials_v1 > 1:
            trial_idx_v1 = rng.integers(0, k_trials_v1, size=(n_scenarios, k_trials_v1))
            resampled_v1 = np.take_along_axis(arr_v1[cluster_idx], trial_idx_v1, axis=1)
            b_means_v1 = np.mean(resampled_v1, axis=1)
        else:
            b_means_v1 = arr_v1[cluster_idx, 0]

        if k_trials_v2 > 1:
            trial_idx_v2 = rng.integers(0, k_trials_v2, size=(n_scenarios, k_trials_v2))
            resampled_v2 = np.take_along_axis(arr_v2[cluster_idx], trial_idx_v2, axis=1)
            b_means_v2 = np.mean(resampled_v2, axis=1)
        else:
            b_means_v2 = arr_v2[cluster_idx, 0]

        boot_thetas[b] = np.mean(b_means_v2 - b_means_v1)

    se = float(np.std(boot_thetas, ddof=1))

    # Percentile bounds as safe fallback
    p_low = 100.0 * (alpha / 2.0)
    p_high = 100.0 * (1.0 - alpha / 2.0)
    perc_lower = float(np.percentile(boot_thetas, p_low))
    perc_upper = float(np.percentile(boot_thetas, p_high))

    # Attempt BCa calculation
    try:
        # Bias-correction z0
        prop_less = np.mean(boot_thetas < theta_hat)
        if prop_less <= 0.0 or prop_less >= 1.0:
            return BootstrapResult(
                estimate=theta_hat,
                ci_lower=perc_lower,
                ci_upper=perc_upper,
                standard_error=se,
                method_used="percentile_fallback",
                n_resamples=n_resamples,
            )

        z0 = float(stats.norm.ppf(prop_less))

        # Acceleration 'a' via cluster jackknife
        jack_thetas = np.empty(n_scenarios, dtype=float)
        for i in range(n_scenarios):
            # Omit cluster i
            mask = np.ones(n_scenarios, dtype=bool)
            mask[i] = False
            jack_thetas[i] = np.mean(diffs[mask])

        jack_mean = np.mean(jack_thetas)
        u_i = jack_mean - jack_thetas
        sum_sq = np.sum(u_i**2)
        sum_cubes = np.sum(u_i**3)

        if sum_sq < 1e-12:
            acc = 0.0
        else:
            acc = float(sum_cubes / (6.0 * (sum_sq**1.5)))

        if math.isnan(acc) or math.isinf(acc) or abs(acc) > 1.0:
            return BootstrapResult(
                estimate=theta_hat,
                ci_lower=perc_lower,
                ci_upper=perc_upper,
                standard_error=se,
                method_used="percentile_fallback",
                n_resamples=n_resamples,
            )

        z_alpha1 = float(stats.norm.ppf(alpha / 2.0))
        z_alpha2 = float(stats.norm.ppf(1.0 - alpha / 2.0))

        denom1 = 1.0 - acc * (z0 + z_alpha1)
        denom2 = 1.0 - acc * (z0 + z_alpha2)

        if denom1 <= 0 or denom2 <= 0:
            return BootstrapResult(
                estimate=theta_hat,
                ci_lower=perc_lower,
                ci_upper=perc_upper,
                standard_error=se,
                method_used="percentile_fallback",
                n_resamples=n_resamples,
            )

        alpha1_adj = float(stats.norm.cdf(z0 + (z0 + z_alpha1) / denom1))
        alpha2_adj = float(stats.norm.cdf(z0 + (z0 + z_alpha2) / denom2))

        if not (0.0 < alpha1_adj < alpha2_adj < 1.0):
            return BootstrapResult(
                estimate=theta_hat,
                ci_lower=perc_lower,
                ci_upper=perc_upper,
                standard_error=se,
                method_used="percentile_fallback",
                n_resamples=n_resamples,
            )

        bca_lower = float(np.percentile(boot_thetas, 100.0 * alpha1_adj))
        bca_upper = float(np.percentile(boot_thetas, 100.0 * alpha2_adj))

        if math.isnan(bca_lower) or math.isnan(bca_upper):
            return BootstrapResult(
                estimate=theta_hat,
                ci_lower=perc_lower,
                ci_upper=perc_upper,
                standard_error=se,
                method_used="percentile_fallback",
                n_resamples=n_resamples,
            )

        return BootstrapResult(
            estimate=theta_hat,
            ci_lower=bca_lower,
            ci_upper=bca_upper,
            standard_error=se,
            method_used="bca",
            n_resamples=n_resamples,
        )

    except (ValueError, ZeroDivisionError, FloatingPointError, IndexError, RuntimeError, TypeError):
        return BootstrapResult(
            estimate=theta_hat,
            ci_lower=perc_lower,
            ci_upper=perc_upper,
            standard_error=se,
            method_used="percentile_fallback",
            n_resamples=n_resamples,
        )
