"""Create reviewer-facing statistical summaries from generated simulation outputs."""
from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
DOCS = ROOT / "docs"


def p_display(p: float) -> str:
    if p < 0.0001:
        return "<0.0001"
    return f"{p:.4f}"


def main() -> None:
    DOCS.mkdir(exist_ok=True)
    frames = []
    for scale, filename in [
        ("Individual microsimulation", "individual_contrast_summary.csv"),
        ("Service discrete-event simulation", "system_contrast_summary.csv"),
    ]:
        df = pd.read_csv(OUT / filename).copy()
        df.insert(0, "scale", scale)
        frames.append(df)
    combined = pd.concat(frames, ignore_index=True)
    combined.to_csv(OUT / "statistical_analysis_summary.csv", index=False)

    columns = [
        "scale", "comparator", "reference", "metric", "mean_difference",
        "bootstrap_ci_low", "bootstrap_ci_high", "mcse_mean_difference",
        "cohen_dz", "sign_flip_pvalue", "holm_sign_flip_pvalue",
        "paired_t_pvalue", "holm_paired_t_pvalue", "replications",
        "bootstrap_resamples", "bootstrap_seed", "permutation_resamples",
        "randomization_seed", "minimum_monte_carlo_pvalue", "holm_family_size",
    ]
    compact = combined[columns].copy()
    compact["95% BCa bootstrap CI"] = compact.apply(
        lambda r: f"{r.bootstrap_ci_low:.4f} to {r.bootstrap_ci_high:.4f}", axis=1
    )
    compact["Holm-adjusted sign-flip p"] = compact["holm_sign_flip_pvalue"].map(p_display)

    lines = [
        "# Statistical analysis and uncertainty report",
        "",
        "## Estimand and resampling unit",
        "",
        "The primary estimand is the expected paired pathway difference under the fixed base-case data-generating assumptions. The independent simulation replication is the uncertainty unit. For paired comparisons, replication identifiers are resampled as intact pairs, preserving the common synthetic cohort or common demand stream.",
        "",
        "## Primary uncertainty analysis",
        "",
        "Primary contrasts use 10,000 nonparametric bias-corrected and accelerated (BCa) bootstrap resamples to obtain 95% confidence intervals for the mean simulation contrast. Monte Carlo standard errors are also reported. The empirical 2.5th-97.5th percentile range of individual replication contrasts is retained separately as a stochastic prediction-range diagnostic; it is not the confidence interval for the mean.",
        "",
        "## Hypothesis tests and multiplicity",
        "",
        "Each paired contrast is evaluated using a two-sided paired t-test and a two-sided paired sign-flip randomization test with 100,000 draws and a plus-one correction. The minimum attainable Monte Carlo p-value is therefore 1/100,001. The NumPy PCG64 generator is used; deterministic bootstrap and randomization seeds are exported for every primary contrast. Holm adjustment controls the family-wise error rate across the seven prespecified outcomes within each comparator and model. Cohen's dz describes standardized separation across paired replications. The randomization test is the primary robustness test because it does not require normal replication-level contrasts; the t-test is reported as a concordance analysis.",
        "",
        "## Interpretation boundary",
        "",
        "These CIs, p-values, and effect sizes refer only to stochastic uncertainty in expected model output under fixed synthetic assumptions. They are not estimates of clinical sampling uncertainty, efficacy, safety incidence, causal effects, or external validity. Small p-values can arise because the model is deliberately repeated many times; they should be described as model-internal inferential separation, not clinical statistical significance.",
        "",
        "## Complete primary contrasts",
        "",
        "| Scale | Comparator | Metric | Mean difference | 95% BCa bootstrap CI | Holm-adjusted sign-flip p | Cohen dz | MCSE |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for _, r in compact.iterrows():
        lines.append(
            f"| {r['scale']} | {r['comparator']} | {r['metric']} | {r['mean_difference']:.4f} | "
            f"{r['95% BCa bootstrap CI']} | {r['Holm-adjusted sign-flip p']} | "
            f"{r['cohen_dz']:.3f} | {r['mcse_mean_difference']:.4f} |"
        )
    lines += [
        "",
        "## Reviewer-facing checks",
        "",
        "- Fixed random seeds are declared in source code and bootstrap/randomization seeds are derived deterministically from analysis labels.",
        "- Common-random-number pairing is preserved during simulation and resampling.",
        "- All primary outcome families and multiplicity adjustments are machine-readable in the contrast CSV files.",
        "- Bootstrap method, number of resamples, confidence level, test statistics, raw and adjusted p-values, effect sizes, MCSEs, and empirical replication ranges are exported.",
        "- Sensitivity-grid cells and warm-up diagnostics include bootstrap intervals; heatmaps identify cells whose interval excludes the null.",
        "- Scenario-uncertainty proportions use clearly labeled resampling-stability intervals and are not presented as posterior probabilities.",
        "- Figure-generation tests verify live SVG text, absence of embedded raster images, Arial/Arimo-compatible font declarations, and a minimum SVG font size of 10 pt.",
        "",
    ]
    (DOCS / "STATISTICAL_ANALYSIS.md").write_text("\n".join(lines), encoding="utf-8")
    print("Wrote outputs/statistical_analysis_summary.csv")
    print("Wrote docs/STATISTICAL_ANALYSIS.md")


if __name__ == "__main__":
    main()
