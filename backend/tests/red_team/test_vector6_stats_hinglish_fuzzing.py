from __future__ import annotations

import numpy as np
import pytest

from backend.app.evaluation.normalizers import (
    are_currencies_equivalent,
    parse_area_sqft,
    parse_bhk,
    parse_indian_currency,
)
from backend.app.stats.bootstrap import two_stage_cluster_bca_bootstrap
from backend.app.stats.paired_tests import (
    compute_exact_mcnemar_test,
    compute_wilcoxon_paired_test,
)


def test_mcnemar_zero_discordant_pairs():
    """When both models have identical pass/fail profiles (b=0, c=0), McNemar must return p=1.0 and delta=0.0."""
    # Case 1: All 1s
    res_ones = compute_exact_mcnemar_test([1] * 20, [1] * 20)
    assert res_ones.p_value == 1.0
    assert res_ones.risk_difference == 0.0
    assert res_ones.is_underpowered is True
    assert res_ones.ci_lower <= 0.0 <= res_ones.ci_upper

    # Case 2: All 0s
    res_zeros = compute_exact_mcnemar_test([0] * 30, [0] * 30)
    assert res_zeros.p_value == 1.0
    assert res_zeros.risk_difference == 0.0
    assert res_zeros.ci_lower <= 0.0 <= res_zeros.ci_upper

    # Case 3: Mixed identical
    res_mixed = compute_exact_mcnemar_test([1, 0, 1, 1, 0] * 4, [1, 0, 1, 1, 0] * 4)
    assert res_mixed.p_value == 1.0
    assert res_mixed.risk_difference == 0.0


def test_mcnemar_underpowered_flag_threshold():
    """Effective N < 50 must explicitly flag is_underpowered=True; N >= 50 must flag False."""
    res_small = compute_exact_mcnemar_test([1] * 49, [0] * 49)
    assert res_small.is_underpowered is True

    res_large = compute_exact_mcnemar_test([1] * 50, [0] * 50)
    assert res_large.is_underpowered is False


def test_wilcoxon_all_tied_scores():
    """When all paired score differences are 0.0, Wilcoxon must gracefully return p=1.0 and r=0.0."""
    scores = [0.85, 0.90, 0.70, 0.95, 0.60] * 5
    res = compute_wilcoxon_paired_test(scores, scores)
    assert res.p_value == 1.0
    assert res.statistic == 0.0
    assert res.mean_difference == 0.0
    assert res.rank_biserial_r == 0.0
    assert res.cohens_dz == 0.0


def test_wilcoxon_empty_and_single_input():
    """Empty and degenerate array inputs handle without exceptions."""
    res_empty = compute_wilcoxon_paired_test([], [])
    assert res_empty.p_value == 1.0
    assert res_empty.effective_n == 0

    res_single = compute_wilcoxon_paired_test([0.5], [0.5])
    assert res_single.p_value == 1.0
    assert res_single.mean_difference == 0.0


def test_two_stage_bootstrap_zero_variance():
    """Identical scenario trial matrices return degenerate bootstrap result without crashing."""
    v1 = [[0.8, 0.8], [0.9, 0.9], [0.7, 0.7]]
    v2 = [[0.8, 0.8], [0.9, 0.9], [0.7, 0.7]]

    b_res = two_stage_cluster_bca_bootstrap(v1, v2, n_resamples=500)
    assert b_res.estimate == 0.0
    assert b_res.ci_lower == 0.0
    assert b_res.ci_upper == 0.0
    assert b_res.standard_error == 0.0
    assert b_res.method_used == "degenerate"


def test_devanagari_numeral_and_hindi_unit_normalizers():
    """Fuzz Devanagari numerals and Hindi script real-estate units across all normalization functions."""
    # 1. Currency Parsing
    assert parse_indian_currency("१२ लाख") == 1200000
    assert parse_indian_currency("१.५ करोड़") == 15000000
    assert parse_indian_currency("५० हज़ार") == 50000
    assert parse_indian_currency("डेढ़ करोड़") == 15000000
    assert parse_indian_currency("ढाई लाख") == 250000

    # 2. Currency Equivalence
    assert are_currencies_equivalent("१.५ करोड़", "1.5 cr") is True
    assert are_currencies_equivalent("१२ लाख", "12,00,000") is True
    assert are_currencies_equivalent("५० हज़ार", "50k") is True

    # 3. BHK Parsing
    assert parse_bhk("३ बीएचके") == 3.0
    assert parse_bhk("२ कमरा") == 2.0
    assert parse_bhk("४ बेडरूम") == 4.0
    assert parse_bhk("स्टूडियो") == 0.5
    assert parse_bhk("२.५ बीएचके") == 2.5

    # 4. Area SqFt Parsing
    assert parse_area_sqft("१२०० वर्ग फुट") == 1200.0
    assert parse_area_sqft("१०० वर्ग मीटर") == pytest.approx(1076.39, rel=1e-2)
