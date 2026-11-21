"""Paired Statistical Tests for PropEval.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md & ADR-005
Handles:
- Quarantined-pair exclusion: drops both arms if either V1 or V2 was quarantined.
- SMOKE_TEST_UNDERPOWERED tagging for N < 50.
- Exact Binomial McNemar's Test + Newcombe Method 10 CI for K=1 or binary pass^k.
- Wilcoxon Signed-Rank Test + Rank-Biserial correlation + Paired Cohen's dz for K>1.
- Holm-Bonferroni multi-testing correction for family-wise release guardrails.
"""

from __future__ import annotations

import math
from typing import Any, NamedTuple

import numpy as np
from scipy import stats


class ContingencyTable2x2(NamedTuple):
    both_pass_a: int      # (1, 1)
    v1_fail_v2_pass_b: int  # (0, 1) - positive flip
    v1_pass_v2_fail_c: int  # (1, 0) - regression flip
    both_fail_d: int      # (0, 0)
    total_n: int


class McNemarResult(NamedTuple):
    p_value: float
    risk_difference: float  # p2 - p1 (V2 - V1)
    ci_lower: float         # Newcombe Method 10 95% CI
    ci_upper: float
    cohens_h: float
    table: ContingencyTable2x2
    effective_n: int
    is_underpowered: bool   # True when N < 50


class WilcoxonResult(NamedTuple):
    statistic: float
    p_value: float
    mean_difference: float  # V2 - V1
    rank_biserial_r: float  # Kerby 2014
    cohens_dz: float
    effective_n: int
    is_underpowered: bool


def exclude_quarantined_pairs(
    v1_results: list[dict[str, Any]],
    v2_results: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, bool]:
    """Exclude both arms if either V1 or V2 on scenario i is quarantined.

    Returns:
        clean_v1, clean_v2, effective_n, is_underpowered
    """
    if len(v1_results) != len(v2_results):
        raise ValueError(f"Arm length mismatch: {len(v1_results)} vs {len(v2_results)}")

    clean_v1 = []
    clean_v2 = []

    for r1, r2 in zip(v1_results, v2_results):
        q1 = (
            r1.get("status") == "QUARANTINED_SIM_FAULT"
            or r1.get("is_quarantined", False)
            or r1.get("last_error_code") == "QUARANTINED_SIM_FAULT"
        )
        q2 = (
            r2.get("status") == "QUARANTINED_SIM_FAULT"
            or r2.get("is_quarantined", False)
            or r2.get("last_error_code") == "QUARANTINED_SIM_FAULT"
        )

        if not q1 and not q2:
            clean_v1.append(r1)
            clean_v2.append(r2)

    effective_n = len(clean_v1)
    is_underpowered = effective_n < 50

    return clean_v1, clean_v2, effective_n, is_underpowered


def compute_2x2_table(
    v1_binary: list[int] | np.ndarray,
    v2_binary: list[int] | np.ndarray,
) -> ContingencyTable2x2:
    """Build 2x2 contingency table for paired binary outcomes."""
    arr1 = np.asarray(v1_binary, dtype=int)
    arr2 = np.asarray(v2_binary, dtype=int)

    if len(arr1) != len(arr2):
        raise ValueError("Length mismatch between paired binary arrays")

    a = int(np.sum((arr1 == 1) & (arr2 == 1)))
    b = int(np.sum((arr1 == 0) & (arr2 == 1)))
    c = int(np.sum((arr1 == 1) & (arr2 == 0)))
    d = int(np.sum((arr1 == 0) & (arr2 == 0)))
    total = a + b + c + d

    return ContingencyTable2x2(
        both_pass_a=a,
        v1_fail_v2_pass_b=b,
        v1_pass_v2_fail_c=c,
        both_fail_d=d,
        total_n=total,
    )


def _wilson_score_interval(x: int, n: int, z: float) -> tuple[float, float]:
    """Compute marginal Wilson score interval [l, u]."""
    if n == 0:
        return 0.0, 1.0

    p_hat = x / n
    denom = 1.0 + (z**2 / n)
    center = (p_hat + (z**2 / (2.0 * n))) / denom
    spread = (z * math.sqrt((p_hat * (1.0 - p_hat) / n) + (z**2 / (4.0 * (n**2))))) / denom

    l_val = max(0.0, center - spread)
    u_val = min(1.0, center + spread)
    return l_val, u_val


def compute_newcombe_method10_ci(
    table: ContingencyTable2x2,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """Compute Newcombe Paired Wilson 95% CI (Method 10) for delta_p = p2 - p1.

    Reference: Newcombe (1998), Method 10.
    """
    n = table.total_n
    if n == 0:
        return 0.0, 0.0

    a, b, c, d = (
        table.both_pass_a,
        table.v1_fail_v2_pass_b,
        table.v1_pass_v2_fail_c,
        table.both_fail_d,
    )
    p1_hat = (a + c) / n
    p2_hat = (a + b) / n
    delta_p = p2_hat - p1_hat

    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    l1, u1 = _wilson_score_interval(a + c, n, z)
    l2, u2 = _wilson_score_interval(a + b, n, z)

    # Continuity-corrected empirical correlation phi
    phi_denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    det = (a * d) - (b * c)
    if phi_denom > 1e-12:
        cc_det = max(abs(det) - (n / 2.0), 0.0) * (1.0 if det >= 0 else -1.0)
        phi = cc_det / phi_denom
    else:
        phi = 0.0

    # Half-widths
    term_low = (p1_hat - l1) ** 2 - 2.0 * phi * (p1_hat - l1) * (u2 - p2_hat) + (u2 - p2_hat) ** 2
    delta_lower = math.sqrt(max(0.0, term_low))

    term_up = (u1 - p1_hat) ** 2 - 2.0 * phi * (u1 - p1_hat) * (p2_hat - l2) + (p2_hat - l2) ** 2
    delta_upper = math.sqrt(max(0.0, term_up))

    ci_low = max(-1.0, min(1.0, delta_p - delta_lower))
    ci_high = max(-1.0, min(1.0, delta_p + delta_upper))

    return ci_low, ci_high


def compute_exact_mcnemar_test(
    v1_binary: list[int] | np.ndarray,
    v2_binary: list[int] | np.ndarray,
    alpha: float = 0.05,
) -> McNemarResult:
    """Exact Binomial McNemar test + Newcombe Method 10 CI for K=1 or binary pass^k.

    Enforces:
    - Exact binomial test on discordant pairs (b, c) without asymptotic chi2 bias.
    - Explicit is_underpowered flag when effective N < 50.
    """
    table = compute_2x2_table(v1_binary, v2_binary)
    n = table.total_n
    is_underpowered = n < 50

    b = table.v1_fail_v2_pass_b
    c = table.v1_pass_v2_fail_c
    discordant = b + c

    if discordant == 0:
        p_val = 1.0
    else:
        res = stats.binomtest(min(b, c), discordant, p=0.5, alternative="two-sided")
        p_val = float(res.pvalue)

    p1_hat = (table.both_pass_a + c) / n if n > 0 else 0.0
    p2_hat = (table.both_pass_a + b) / n if n > 0 else 0.0
    risk_diff = p2_hat - p1_hat

    ci_low, ci_high = compute_newcombe_method10_ci(table, alpha=alpha)

    # Cohen's h
    h = 2.0 * math.asin(math.sqrt(p2_hat)) - 2.0 * math.asin(math.sqrt(p1_hat))

    return McNemarResult(
        p_value=p_val,
        risk_difference=risk_diff,
        ci_lower=ci_low,
        ci_upper=ci_high,
        cohens_h=h,
        table=table,
        effective_n=n,
        is_underpowered=is_underpowered,
    )


def compute_wilcoxon_paired_test(
    v1_scores: list[float] | np.ndarray,
    v2_scores: list[float] | np.ndarray,
) -> WilcoxonResult:
    """Wilcoxon signed-rank test on paired scenario scores for K>1 or continuous metrics."""
    s1 = np.asarray(v1_scores, dtype=float)
    s2 = np.asarray(v2_scores, dtype=float)

    if len(s1) != len(s2):
        raise ValueError("Length mismatch between paired score arrays")

    n = len(s1)
    is_underpowered = n < 50

    if n == 0:
        return WilcoxonResult(
            statistic=0.0,
            p_value=1.0,
            mean_difference=0.0,
            rank_biserial_r=0.0,
            cohens_dz=0.0,
            effective_n=0,
            is_underpowered=True,
        )

    diffs = s2 - s1
    mean_diff = float(np.mean(diffs))

    # Check for all zeroes or identical differences
    non_zero = diffs[diffs != 0]
    if len(non_zero) == 0:
        return WilcoxonResult(
            statistic=0.0,
            p_value=1.0,
            mean_difference=mean_diff,
            rank_biserial_r=0.0,
            cohens_dz=0.0,
            effective_n=n,
            is_underpowered=is_underpowered,
        )

    # Wilcoxon signed-rank test with Pratt method for zero-handling
    w_res: Any = stats.wilcoxon(s2, s1, zero_method="pratt", alternative="two-sided")
    p_val = float(w_res.pvalue)
    stat = float(w_res.statistic)

    # Matched-pairs rank-biserial correlation: r_rb = (W+ - W-) / (W+ + W-)
    ranks = stats.rankdata(np.abs(diffs))
    w_plus = float(np.sum(ranks[diffs > 0]))
    w_minus = float(np.sum(ranks[diffs < 0]))
    w_sum = w_plus + w_minus
    r_rb = (w_plus - w_minus) / w_sum if w_sum > 0 else 0.0

    # Paired Cohen's dz = mean(diff) / std(diff)
    std_diff = float(np.std(diffs, ddof=1)) if n > 1 else 0.0
    cohens_dz = (mean_diff / std_diff) if std_diff > 1e-12 else 0.0

    return WilcoxonResult(
        statistic=stat,
        p_value=p_val,
        mean_difference=mean_diff,
        rank_biserial_r=r_rb,
        cohens_dz=cohens_dz,
        effective_n=n,
        is_underpowered=is_underpowered,
    )


def holm_bonferroni_correction(
    p_values: list[float] | dict[str, float],
    alpha: float = 0.05,
) -> tuple[list[float], list[bool]] | dict[str, dict[str, Any]]:
    """Apply Holm-Bonferroni step-down correction to control family-wise error rate (FWER)."""
    is_dict = isinstance(p_values, dict)

    if is_dict:
        keys = list(p_values.keys())
        raw_pvals = [p_values[k] for k in keys]
    else:
        keys = []
        raw_pvals = list(p_values)

    m = len(raw_pvals)
    if m == 0:
        return {} if is_dict else ([], [])

    # Sort indices by p-value
    sorted_indices = sorted(range(m), key=lambda i: raw_pvals[i])

    adj_pvals = [0.0] * m
    rejected = [False] * m

    cum_max = 0.0
    for rank, idx in enumerate(sorted_indices):
        k = rank + 1
        factor = m - k + 1
        adj_p = min(1.0, factor * raw_pvals[idx])
        cum_max = max(cum_max, adj_p)
        adj_pvals[idx] = min(1.0, cum_max)

    # Step-down rejection
    for rank, idx in enumerate(sorted_indices):
        k = rank + 1
        threshold = alpha / (m - k + 1)
        if raw_pvals[idx] <= threshold:
            rejected[idx] = True
        else:
            # Once a null hypothesis is not rejected, stop rejecting subsequent hypotheses
            break

    if is_dict:
        result_dict = {}
        for i, k in enumerate(keys):
            result_dict[k] = {
                "raw_p_value": raw_pvals[i],
                "adjusted_p_value": adj_pvals[i],
                "significant": rejected[i],
            }
        return result_dict

    return adj_pvals, rejected


def compute_pass_at_k(trial_passes: list[list[int]] | np.ndarray, k: int | None = None) -> np.ndarray:
    """Compute pass^k per scenario.

    If k is None or k == K: returns 1 if all K trials passed, 0 otherwise.
    If k < K: returns unbiased estimator comb(c, k) / comb(K, k).
    """
    arr = np.asarray(trial_passes, dtype=int)
    n_scenarios, total_k = arr.shape

    target_k = total_k if k is None else k
    if target_k > total_k:
        raise ValueError(f"Requested k={target_k} exceeds available trials K={total_k}")

    success_counts = np.sum(arr, axis=1)

    if target_k == total_k:
        return (success_counts == total_k).astype(int)

    # Unbiased combinatorial pass^k
    pass_k_vals = np.empty(n_scenarios, dtype=float)
    for i, c in enumerate(success_counts):
        if c < target_k:
            pass_k_vals[i] = 0.0
        else:
            pass_k_vals[i] = math.comb(c, target_k) / math.comb(total_k, target_k)

    return pass_k_vals
