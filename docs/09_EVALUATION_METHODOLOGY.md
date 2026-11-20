# 09 — Evaluation & Statistical Methodology

PropEval treats prompt evaluation as a **controlled, paired statistical experiment** rather than a dashboard of uncalibrated AI scores. Every methodological decision below is grounded in peer-reviewed statistics and AI evaluation literature.

---

## 1. Non-Compensatory Multidimensional Capability Profile

PropEval **forbids** collapsing all dimensions into a single weighted average. Following [Real World Voice EQ Bench (2026)](https://arxiv.org/abs/2607.14846), prompt regressions are evaluated across four independent, non-compensatory tiers:

| Tier | Evaluation Dimension | Oracle Type | Gate Behavior |
| :--- | :--- | :--- | :--- |
| **Hard Gate A (Safety & Compliance)** | TRAI DNC exit (`mark_dnc` + terminate within 1 turn); zero unauthorized financial/legal guarantees | Deterministic tool/turn check + regex/entailment hybrid | **Zero-tolerance block** |
| **Hard Gate B (Action & Data Integrity)** | Zero invented actions (cross-checking tool HTTP status vs confirmation intent); valid tool JSON schema; Metamorphic currency invariance (`1.2 cr == 120 lakh`) | Deterministic tool/schema verifier + Hinglish entailment fallback for ambiguous phrasing | **Zero-tolerance block** |
| **Hard Gate C (Property Fact Grounding)** | Entailment of quoted price, carpet area, floor-rise, RERA ID, and possession quarter against active `project_fixtures` | Deterministic numeric/negation extractor + fixture lookup (+ binary entailment for colloquial dates) | **Zero-tolerance block** |
| **Statistical Primary & Secondary Metrics** | (1) End-to-end Task Completion Rate (Primary); (2) Slot Extraction F1; (3) Calibrated Hinglish Tone/Objection Rubric; (4) p95 TTFT Latency & Token Cost | Paired statistical comparison (`SciPy 1.18.1` / `statsmodels 0.15.0`) + calibrated cross-family binary judge | **Holm-Bonferroni adjusted gate** (Tier 2 runs, $N \ge 50$) |

---

## 2. Paired Experimental Design & Variance Reduction

Prompt V1 and Prompt V2 are executed on the **exact same $N$ initial scenario seeds**, FSM specs, ASR perturbation seeds, and project fixtures. For paired scores $X_i, Y_i$ with difference $D_i = Y_i - X_i$:

$$\operatorname{Var}(\bar{Y} - \bar{X}) = \frac{\sigma_X^2 + \sigma_Y^2 - 2\rho_{XY}\sigma_X\sigma_Y}{N}$$

Pairing subtracts out between-scenario difficulty variance via $-2\rho_{XY}\sigma_X\sigma_Y$, cutting required sample size by up to $4\times$ when $\rho_{XY} = 0.75$ ([Evan Miller / Anthropic, 2024](https://arxiv.org/html/2411.00640v1); [Dror et al., ACL 2018](https://aclanthology.org/P18-1128/)). Unpaired two-sample tests are **strictly prohibited**. If either V1 or V2 on scenario $i$ is `QUARANTINED_SIM_FAULT`, **both** arms for scenario $i$ are dropped before computing paired statistics so pairing remains intact.

---

## 3. Exact Statistical Tests by Outcome Type & Trial Count ($K$)

### 3.1 Binary Paired Outcomes (Strictly $K = 1$, or Binary `pass^k` per Scenario)
Build the $2 \times 2$ paired table ($a$: both pass, $b$: V1 fail $\to$ V2 pass, $c$: V1 pass $\to$ V2 fail, $d$: both fail; discordant pairs $D = b + c$):
* **Hypothesis Test:** **Exact Binomial McNemar's Test** (`statsmodels.stats.contingency_tables.mcnemar(table, exact=True)` / `scipy.stats.binomtest(min(b, c), b + c, 0.5)`) whenever $N \le 50$ or $b + c < 25$. Asymptotic CLT/$\chi^2$ approximations systematically under-cover in small-$N$ LLM evals ([Bowyer, Aitchison, & Ivanova, ICML 2025 Spotlight](https://arxiv.org/abs/2503.01747)).
* **Confidence Interval:** **Newcombe's Hybrid Paired Wilson Score Interval** (Method 10, [Newcombe, 1998](https://pubmed.ncbi.nlm.nih.gov/9839354/), clamped to $[-1, 1]$) or Bayesian Dirichlet-Multinomial credible interval over $(a,b,c,d)$ for $N < 50$.
* **Effect Sizes:** Risk Difference $\hat{\Delta p} = (b - c)/N$ and Cohen's $h = 2\arcsin(\sqrt{p_2}) - 2\arcsin(\sqrt{p_1})$.

### 3.2 Multi-Trial Pass Rates ($K > 1$) & Continuous / Ordinal Outcomes
**Critical Rule:** When $K > 1$, each scenario's mean pass rate $\bar{Y}_i \in \{0, 1/K, \dots, 1\}$ is **not** binary. PropEval **never** runs McNemar or Newcombe on pooled $N \times K$ trials (which violates independence and inflates Type I error past **45%**; [Saravanan, Berman, & Sober, 2020](https://pmc.ncbi.nlm.nih.gov/articles/PMC7906290/)).
* **Hypothesis Test:** **Wilcoxon Signed-Rank Test** (`scipy.stats.wilcoxon`, `zero_method='pratt'`) on per-scenario means $\bar{X}_i, \bar{Y}_i$ (also used for skewed latency, token cost, and ordinal rubrics; [Dror et al., 2018](https://aclanthology.org/P18-1128/)). Use **Paired $t$-test** (`scipy.stats.ttest_rel`) only on symmetric differences (e.g., log-latency).
* **Confidence Intervals:** **Two-Stage Hierarchical / Cluster BCa Bootstrap** (resampling $N$ scenario pairs with replacement, then resampling $K$ trials within each scenario, `n_resamples=9999`), automatically falling back to `method='percentile'` if BCa returns `NaN` on heavily tied discrete scores.
* **Effect Sizes:** Matched-pairs rank-biserial correlation $r_{rb} = \frac{W^+ - W^-}{W^+ + W^-}$ ([Kerby, 2014](https://www.researchgate.net/publication/304355151_The_Simple_Difference_Formula_An_Approach_to_Teaching_Nonparametric_Correlation)) for Wilcoxon; paired Cohen's $d_z = \bar{D}/s_D$ plus $d_{av}$ ([Lakens, 2013](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2013.00863/full)) for paired $t$-tests.
* **Production Consistency (`pass^k`):** Compute binary `pass^k` per scenario ($\mathbb{I}[\text{all } K \text{ trials pass}]$, or unbiased $\binom{c_i}{k}/\binom{K}{k}$; [$\tau$-bench, Yao et al., 2024](https://arxiv.org/abs/2406.12045)). Because `pass^k` at $k = K$ is binary per scenario, Exact McNemar + Newcombe CI *is* mathematically valid on `pass^K`.

---

## 4. Brutally Honest Power Analysis & Two-Tier Gating

Testing $m = 10$ metrics at $\alpha = 0.05$ inflates FWER to $1 - 0.95^{10} = \mathbf{40.1\%}$. PropEval pre-registers **1 primary metric** ($\alpha = 0.05$), applies **Holm-Bonferroni** (`statsmodels.stats.multitest.multipletests(..., method='holm')`; [Holm, 1979](https://openalex.org/works/W2121044470)) to release guardrails, and **Benjamini-Hochberg FDR** (`scipy.stats.false_discovery_control(..., method='bh')`; [Benjamini & Hochberg, 1995](https://academic.oup.com/jrsssb/article/57/1/289/7035855)) to diagnostic sub-rubrics.

Exact Minimum Detectable Effects (MDEs) at **80% statistical power** (two-sided):

| Scenario Count ($N$) | Exact McNemar MDE ($p_{10}=0.00$) | Exact McNemar MDE ($p_{10}=0.05$) | Exact McNemar MDE ($p_{10}=0.10$) | Paired $t$-Test MDE ($d_z, \alpha=0.05$) | Paired $t$-Test MDE ($d_z, \alpha=0.005$) | Operational Role in PropEval |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **$N = 20$** | **+36.6 pp** | **+46.0 pp** | **+53.4 pp** | **0.660** (large) | **0.912** (very large) | **Tier 1 PR Smoke Gate ONLY** (hard gates + wide CIs; never claims significance) |
| **$N = 50$** | **+15.4 pp** | **+23.0 pp** | **+28.2 pp** | **0.404** (small-med) | **0.538** (medium) | **Tier 2 Fast Release Gate** (detects major prompt wins/regressions) |
| **$N = 100$** | **+7.8 pp** | **+14.2 pp** | **+17.7 pp** | **0.283** (small) | **0.372** (small-med) | **Tier 2 Full Release Gate** (detects realistic +10–15 pp prompt gains) |

---

## 5. Judge Calibration, Sequential Early-Abort & Longitudinal SPC

1. **Clamped Rogan–Gladen & PPI++ Calibration:** Calibrate every cross-family binary rubric judge on a locked human-labeled golden set ($n \ge 30$) computing **Cohen's $\kappa$** ($\ge 0.70$ required) and **Fail-class Precision/Recall**. When $\text{TPR} + \text{TNR} > 1.05$, compute clamped **Rogan–Gladen** $\hat{\pi}_{\text{RG}} = \operatorname{clip}\!\left(\frac{\hat{p} + \text{TNR} - 1}{\text{TPR} + \text{TNR} - 1}, 0, 1\right)$ ([Rogan & Gladen, 1978](https://pubmed.ncbi.nlm.nih.gov/623091/)) with bootstrap propagation of golden-set estimation variance—or **PPI++** (Angelopoulos, Duchi, & Zrnic, 2023; [OpenReview TMLR](https://openreview.net/forum?id=J2Yg9vJcYb)): $\hat{\theta}_{\text{PPI++}} = \frac{1}{N}\sum_{i=1}^N \lambda \hat{f}(X_i) + \frac{1}{n}\sum_{j=1}^n (Y_j - \lambda \hat{f}(\tilde{X}_j))$, which delivers asymptotically valid CIs without Rogan–Gladen's $1/J^2$ variance blow-up.
2. **Sequential Harm Early-Stopping (mSPRT):** For $N \ge 100$ runs, evaluate an asymmetric one-sided mSPRT always-valid $p$-value ([Johari et al., Operations Research 2022](https://pubsonline.informs.org/doi/10.1287/opre.2021.2135)) every 20 scenarios to abort early on catastrophic harm ($-20\text{ pp}$).
3. **Longitudinal Production Drift (SPC):** Monitor a fixed nightly canary suite ($N=50$) via **Shewhart $p$-charts** ([NIST §6.3.3.2](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc332.htm)) and **EWMA charts** ($\lambda = 0.2, L = 2.8$; [NIST §6.3.2.4](https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc324.htm)).
