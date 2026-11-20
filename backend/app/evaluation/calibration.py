"""Judge Calibration: Cohen's Kappa, Fail-P/R, Clamped Rogan-Gladen & PPI++.

Architecture Spec: docs/09_EVALUATION_METHODOLOGY.md & ADR-004
References:
- Rogan & Gladen (1978): Estimating prevalence from screening test results.
- Angelopoulos, Duchi, & Zrnic (2023): Prediction-Powered Inference (PPI++).
"""

from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np


class JudgeCalibrationMetrics(NamedTuple):
    cohens_kappa: float
    tpr: float  # Sensitivity
    tnr: float  # Specificity
    fail_precision: float
    fail_recall: float
    is_calibrated: bool
    status: str


class RoganGladenResult(NamedTuple):
    calibrated_rate: float
    raw_rate: float
    tpr: float
    tnr: float
    status: str


class PPIResult(NamedTuple):
    theta_ppi: float
    ci_lower: float
    ci_upper: float
    lambda_weight: float
    standard_error: float


def compute_judge_calibration(
    true_labels: list[int] | np.ndarray,
    predicted_labels: list[int] | np.ndarray,
) -> JudgeCalibrationMetrics:
    """Compute Cohen's kappa, TPR, TNR, and Fail-class Precision/Recall.

    Labels: 1 = Pass, 0 = Fail.
    """
    y_true = np.asarray(true_labels, dtype=int)
    y_pred = np.asarray(predicted_labels, dtype=int)

    if len(y_true) != len(y_pred):
        raise ValueError("Length mismatch between true labels and predictions")

    n = len(y_true)
    if n == 0:
        return JudgeCalibrationMetrics(
            cohens_kappa=0.0,
            tpr=0.0,
            tnr=0.0,
            fail_precision=0.0,
            fail_recall=0.0,
            is_calibrated=False,
            status="EMPTY_DATA",
        )

    # Confusion matrix
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))

    # TPR & TNR
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    tnr = tn / (tn + fp) if (tn + fp) > 0 else 1.0

    # Fail class (0) metrics
    fail_precision = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    fail_recall = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    # Cohen's Kappa
    po = (tp + tn) / n
    p_yes = ((tp + fn) / n) * ((tp + fp) / n)
    p_no = ((tn + fp) / n) * ((tn + fn) / n)
    pe = p_yes + p_no

    if abs(1.0 - pe) < 1e-9:
        kappa = 1.0 if po >= 0.999 else 0.0
    else:
        kappa = (po - pe) / (1.0 - pe)

    is_calibrated = (kappa >= 0.70) and ((tpr + tnr) > 1.05)
    status = "CALIBRATED" if is_calibrated else "UNCALIBRATED_ADVISORY_ONLY"

    return JudgeCalibrationMetrics(
        cohens_kappa=float(kappa),
        tpr=float(tpr),
        tnr=float(tnr),
        fail_precision=float(fail_precision),
        fail_recall=float(fail_recall),
        is_calibrated=is_calibrated,
        status=status,
    )


def compute_rogan_gladen(
    observed_rate: float,
    tpr: float,
    tnr: float,
    kappa: float = 1.0,
) -> RoganGladenResult:
    """Compute Clamped Rogan-Gladen prevalence estimator.

    If TPR + TNR <= 1.05 or kappa < 0.70, marks as UNCALIBRATED_ADVISORY_ONLY.
    Formula: pi_hat = (p_hat + TNR - 1) / (TPR + TNR - 1), clamped to [0, 1].
    """
    denom = tpr + tnr - 1.0
    if denom <= 0.05 or kappa < 0.70:
        return RoganGladenResult(
            calibrated_rate=float(observed_rate),
            raw_rate=float(observed_rate),
            tpr=tpr,
            tnr=tnr,
            status="UNCALIBRATED_ADVISORY_ONLY",
        )

    raw_pi = (observed_rate + tnr - 1.0) / denom
    clamped_pi = max(0.0, min(1.0, raw_pi))

    return RoganGladenResult(
        calibrated_rate=float(clamped_pi),
        raw_rate=float(observed_rate),
        tpr=tpr,
        tnr=tnr,
        status="CALIBRATED",
    )


def compute_ppi_plus_plus(
    unlabelled_predictions: list[float] | np.ndarray,
    labelled_predictions: list[float] | np.ndarray,
    labelled_ground_truth: list[float] | np.ndarray,
    alpha: float = 0.05,
) -> PPIResult:
    """Compute Prediction-Powered Inference++ (PPI++) rectified point estimate and CI.

    Reference: Angelopoulos et al., 2023.
    """
    f_unlabelled = np.asarray(unlabelled_predictions, dtype=float)
    f_labelled = np.asarray(labelled_predictions, dtype=float)
    y_labelled = np.asarray(labelled_ground_truth, dtype=float)

    n = len(y_labelled)
    big_n = len(f_unlabelled)

    if n == 0:
        mean_unlabelled = float(np.mean(f_unlabelled)) if big_n > 0 else 0.0
        return PPIResult(
            theta_ppi=mean_unlabelled,
            ci_lower=0.0,
            ci_upper=1.0,
            lambda_weight=1.0,
            standard_error=0.0,
        )

    # Compute optimal lambda
    cov_matrix = np.cov(y_labelled, f_labelled)
    cov_yf = cov_matrix[0, 1] if cov_matrix.shape == (2, 2) else 0.0
    var_f = float(np.var(f_labelled, ddof=1)) if n > 1 else 0.0

    if var_f > 1e-9:
        lam = float(np.clip(cov_yf / var_f, 0.0, 2.0))
    else:
        lam = 1.0

    # PPI point estimate
    # theta = (1/N) sum(lam * f(X_i)) + (1/n) sum(Y_j - lam * f(X_j_tilde))
    term_unlabelled = float(np.mean(lam * f_unlabelled)) if big_n > 0 else 0.0
    residuals = y_labelled - (lam * f_labelled)
    term_residual = float(np.mean(residuals))

    theta_raw = term_unlabelled + term_residual
    theta_ppi = max(0.0, min(1.0, theta_raw))

    # Variance of the estimator
    var_residual = float(np.var(residuals, ddof=1)) if n > 1 else 0.0
    var_unlabelled = float(np.var(lam * f_unlabelled, ddof=1)) if big_n > 1 else 0.0

    se = math.sqrt((var_residual / n) + (var_unlabelled / big_n if big_n > 0 else 0.0))

    from scipy import stats
    z = float(stats.norm.ppf(1.0 - alpha / 2.0))
    ci_lower = max(0.0, theta_ppi - z * se)
    ci_upper = min(1.0, theta_ppi + z * se)

    return PPIResult(
        theta_ppi=float(theta_ppi),
        ci_lower=float(ci_lower),
        ci_upper=float(ci_upper),
        lambda_weight=float(lam),
        standard_error=float(se),
    )
