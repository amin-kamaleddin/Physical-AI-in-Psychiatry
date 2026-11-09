"""Deterministic uncertainty and inference utilities for simulation outputs.

The primary uncertainty unit is the independent simulation replication.  For
paired pathway comparisons, replication identifiers are resampled as intact
pairs so common-random-number matching is preserved.

These calculations quantify uncertainty in expected *model output under fixed
assumptions*.  They do not create confidence intervals or p-values for a
real-world clinical treatment effect.
"""
from __future__ import annotations

from collections.abc import Iterable
import math
import zlib

import numpy as np
import pandas as pd
from scipy import stats

BOOTSTRAP_RESAMPLES = 10_000
PERMUTATION_RESAMPLES = 100_000
CONFIDENCE_LEVEL = 0.95
STATISTICAL_SEED = 20260729


def stable_seed(label: str, base_seed: int = STATISTICAL_SEED) -> int:
    """Return a process-stable seed derived from a human-readable label."""
    return int((base_seed + zlib.crc32(label.encode("utf-8"))) % (2**32 - 1))


def _clean(values: Iterable[float]) -> np.ndarray:
    x = np.asarray(list(values) if not isinstance(values, np.ndarray) else values, dtype=float)
    return x[np.isfinite(x)]


def bootstrap_mean_ci(
    values: Iterable[float],
    *,
    confidence_level: float = CONFIDENCE_LEVEL,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
    seed: int | str = STATISTICAL_SEED,
    method: str = "BCa",
) -> dict[str, float | int | str]:
    """Estimate a mean and nonparametric bootstrap confidence interval.

    BCa is used by default. Degenerate samples fall back to the observed
    constant. If BCa cannot be evaluated, a percentile interval is used and
    the returned ``bootstrap_method`` records the fallback.
    """
    x = _clean(values)
    if x.size == 0:
        return {
            "mean": math.nan,
            "bootstrap_ci_low": math.nan,
            "bootstrap_ci_high": math.nan,
            "bootstrap_se": math.nan,
            "n": 0,
            "bootstrap_resamples": int(n_resamples),
            "confidence_level": float(confidence_level),
            "bootstrap_method": method,
        }
    point = float(np.mean(x))
    if x.size < 2 or np.allclose(x, x[0]):
        return {
            "mean": point,
            "bootstrap_ci_low": point,
            "bootstrap_ci_high": point,
            "bootstrap_se": 0.0,
            "n": int(x.size),
            "bootstrap_resamples": int(n_resamples),
            "confidence_level": float(confidence_level),
            "bootstrap_method": "degenerate",
        }

    rng_seed = stable_seed(seed) if isinstance(seed, str) else int(seed)
    rng = np.random.default_rng(rng_seed)
    used_method = method
    try:
        result = stats.bootstrap(
            (x,),
            np.mean,
            confidence_level=confidence_level,
            n_resamples=n_resamples,
            method=method,
            rng=rng,
            batch=min(2_000, n_resamples),
        )
        low = float(result.confidence_interval.low)
        high = float(result.confidence_interval.high)
        se = float(result.standard_error)
        if not (np.isfinite(low) and np.isfinite(high) and np.isfinite(se)):
            raise ValueError("non-finite BCa result")
    except Exception:
        used_method = "percentile-fallback"
        rng = np.random.default_rng(rng_seed)
        result = stats.bootstrap(
            (x,),
            np.mean,
            confidence_level=confidence_level,
            n_resamples=n_resamples,
            method="percentile",
            rng=rng,
            batch=min(2_000, n_resamples),
        )
        low = float(result.confidence_interval.low)
        high = float(result.confidence_interval.high)
        se = float(result.standard_error)
    return {
        "mean": point,
        "bootstrap_ci_low": low,
        "bootstrap_ci_high": high,
        "bootstrap_se": se,
        "n": int(x.size),
        "bootstrap_resamples": int(n_resamples),
        "confidence_level": float(confidence_level),
        "bootstrap_method": used_method,
    }


def sign_flip_pvalue(
    differences: Iterable[float],
    *,
    n_resamples: int = PERMUTATION_RESAMPLES,
    seed: int | str = STATISTICAL_SEED,
) -> float:
    """Two-sided paired randomization p-value using sign flips.

    The plus-one correction prevents reporting a zero Monte Carlo p-value.
    """
    x = _clean(differences)
    if x.size == 0:
        return math.nan
    if np.allclose(x, 0.0):
        return 1.0
    observed = abs(float(np.mean(x)))
    rng_seed = stable_seed(seed) if isinstance(seed, str) else int(seed)
    rng = np.random.default_rng(rng_seed)
    extreme = 0
    remaining = int(n_resamples)
    chunk = 5_000
    while remaining > 0:
        size = min(chunk, remaining)
        signs = rng.integers(0, 2, size=(size, x.size), dtype=np.int8) * 2 - 1
        permuted = np.abs((signs * x).mean(axis=1))
        extreme += int(np.count_nonzero(permuted >= observed - 1e-15))
        remaining -= size
    return float((extreme + 1) / (n_resamples + 1))


def paired_contrast_statistics(
    differences: Iterable[float],
    *,
    label: str,
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES,
    permutation_resamples: int = PERMUTATION_RESAMPLES,
) -> dict[str, float | int | str]:
    """Summarize one paired replication-level contrast."""
    x = _clean(differences)
    boot = bootstrap_mean_ci(
        x,
        n_resamples=bootstrap_resamples,
        seed=f"bootstrap:{label}",
        method="BCa",
    )
    if x.size < 2 or np.allclose(x, x[0]):
        t_stat = math.inf if boot["mean"] != 0 else 0.0
        t_pvalue = 0.0 if boot["mean"] != 0 else 1.0
        sd = 0.0
        mcse = 0.0
        dz = math.copysign(math.inf, float(boot["mean"])) if boot["mean"] != 0 else 0.0
    else:
        t_result = stats.ttest_1samp(x, popmean=0.0, nan_policy="omit")
        t_stat = float(t_result.statistic)
        t_pvalue = float(t_result.pvalue)
        sd = float(np.std(x, ddof=1))
        mcse = float(sd / np.sqrt(x.size))
        dz = float(np.mean(x) / sd) if sd > 0 else math.nan
    bootstrap_seed = stable_seed(f"bootstrap:{label}")
    randomization_seed = stable_seed(f"signflip:{label}")
    return {
        "mean_difference": float(boot["mean"]),
        "bootstrap_ci_low": float(boot["bootstrap_ci_low"]),
        "bootstrap_ci_high": float(boot["bootstrap_ci_high"]),
        "bootstrap_se": float(boot["bootstrap_se"]),
        "bootstrap_method": str(boot["bootstrap_method"]),
        "bootstrap_resamples": int(boot["bootstrap_resamples"]),
        "bootstrap_seed": int(bootstrap_seed),
        "confidence_level": float(boot["confidence_level"]),
        "replication_p025_difference": float(np.quantile(x, 0.025)),
        "replication_p975_difference": float(np.quantile(x, 0.975)),
        # Backward-compatible aliases now deliberately point to the CI for the mean.
        "p025_difference": float(boot["bootstrap_ci_low"]),
        "p975_difference": float(boot["bootstrap_ci_high"]),
        "sd_difference": sd,
        "mcse_mean_difference": mcse,
        "median_difference": float(np.median(x)),
        "fraction_draws_above_zero": float(np.mean(x > 0)),
        "paired_t_statistic": t_stat,
        "paired_t_degrees_of_freedom": int(max(x.size - 1, 0)),
        "paired_t_pvalue": t_pvalue,
        "sign_flip_pvalue": sign_flip_pvalue(
            x, n_resamples=permutation_resamples, seed=f"signflip:{label}"
        ),
        "cohen_dz": dz,
        "replications": int(x.size),
        "permutation_resamples": int(permutation_resamples),
        "randomization_seed": int(randomization_seed),
        "minimum_monte_carlo_pvalue": float(1.0 / (permutation_resamples + 1)),
        "rng_algorithm": "NumPy PCG64",
        "alternative": "two-sided",
    }


def holm_adjust(pvalues: Iterable[float]) -> np.ndarray:
    """Holm step-down family-wise-error adjustment."""
    p = np.asarray(list(pvalues), dtype=float)
    result = np.full(p.shape, np.nan, dtype=float)
    valid = np.isfinite(p)
    pv = p[valid]
    if pv.size == 0:
        return result
    order = np.argsort(pv)
    sorted_p = pv[order]
    adjusted_sorted = np.maximum.accumulate((pv.size - np.arange(pv.size)) * sorted_p)
    adjusted_sorted = np.minimum(adjusted_sorted, 1.0)
    adjusted = np.empty_like(adjusted_sorted)
    adjusted[order] = adjusted_sorted
    result[np.flatnonzero(valid)] = adjusted
    return result


def add_holm_columns(
    frame: pd.DataFrame,
    *,
    group_columns: list[str],
    p_columns: tuple[str, ...] = ("sign_flip_pvalue", "paired_t_pvalue"),
) -> pd.DataFrame:
    """Add Holm-adjusted p-values within each declared outcome family."""
    out = frame.copy()
    out["holm_family_size"] = 0
    for _, indices in out.groupby(group_columns, sort=False).groups.items():
        out.loc[list(indices), "holm_family_size"] = len(indices)
    for p_col in p_columns:
        target = f"holm_{p_col}"
        out[target] = np.nan
        for _, indices in out.groupby(group_columns, sort=False).groups.items():
            idx = list(indices)
            out.loc[idx, target] = holm_adjust(out.loc[idx, p_col].to_numpy())
    return out


def bootstrap_group_summary(
    frame: pd.DataFrame,
    *,
    group_column: str,
    metrics: list[str],
    label_prefix: str,
    n_resamples: int = BOOTSTRAP_RESAMPLES,
) -> pd.DataFrame:
    """Wide bootstrap summary of replication-level arm or scenario means."""
    rows: list[dict[str, float | int | str]] = []
    for group_name, group in frame.groupby(group_column, sort=False):
        row: dict[str, float | int | str] = {group_column: str(group_name), "replications": int(len(group))}
        for metric in metrics:
            result = bootstrap_mean_ci(
                group[metric].to_numpy(),
                n_resamples=n_resamples,
                seed=f"{label_prefix}:{group_name}:{metric}",
                method="BCa",
            )
            row[f"{metric}_mean"] = float(result["mean"])
            row[f"{metric}_ci_low"] = float(result["bootstrap_ci_low"])
            row[f"{metric}_ci_high"] = float(result["bootstrap_ci_high"])
            row[f"{metric}_bootstrap_se"] = float(result["bootstrap_se"])
            row[f"{metric}_replication_p025"] = float(group[metric].quantile(0.025))
            row[f"{metric}_replication_p975"] = float(group[metric].quantile(0.975))
        rows.append(row)
    return pd.DataFrame(rows)
