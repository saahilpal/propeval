"""Stats package for PropEval: Paired Tests, Bootstrap & Multi-Testing Corrections."""

from __future__ import annotations

from backend.app.stats.bootstrap import (
    BootstrapResult,
    two_stage_cluster_bca_bootstrap,
)
from backend.app.stats.paired_tests import (
    ContingencyTable2x2,
    McNemarResult,
    WilcoxonResult,
    compute_2x2_table,
    compute_exact_mcnemar_test,
    compute_newcombe_method10_ci,
    compute_pass_at_k,
    compute_wilcoxon_paired_test,
    exclude_quarantined_pairs,
    holm_bonferroni_correction,
)

__all__ = [
    "BootstrapResult",
    "ContingencyTable2x2",
    "McNemarResult",
    "WilcoxonResult",
    "compute_2x2_table",
    "compute_exact_mcnemar_test",
    "compute_newcombe_method10_ci",
    "compute_pass_at_k",
    "compute_wilcoxon_paired_test",
    "exclude_quarantined_pairs",
    "holm_bonferroni_correction",
    "two_stage_cluster_bca_bootstrap",
]
