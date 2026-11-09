"""Global, interaction-aware sensitivity analysis for the physical-AI models.

This module implements a variance-based Sobol analysis without adding a SALib
runtime dependency. It uses scrambled Sobol quasi-random designs, Saltelli's
A/B cross-sampling construction, first-order and total-order estimators, and
pairwise second-order indices. Because both simulators are stochastic, each
parameter vector is evaluated over replicated common-random-number contrasts.
The analysis is an uncertainty stress test over explicitly declared ranges; it
is not an empirical posterior analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterable
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import qmc

from figure_utils import save_figure
from individual_microsimulation import ARM_CONFIGS, simulate_arm, summarize as summarize_individual
from service_queue_simulation import CONFIGS, generate_random_stream, simulate_one_from_stream

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results" / "global_sensitivity_screening"
FIGURE_ROOT = ROOT / "figures" / "individual_displays"
SEED = 20260730


@dataclass(frozen=True)
class Parameter:
    name: str
    label: str
    low: float
    high: float
    unit: str
    discrete: bool = False


INDIVIDUAL_PARAMETERS = [
    Parameter("engagement_logit_advantage", "Engagement advantage", -0.10, 0.35, "logit units"),
    Parameter("embodiment_effect", "Embodiment symptom increment", 0.00, 0.12, "PHQ-9 points per engaged week"),
    Parameter("downtime", "Session downtime", 0.02, 0.20, "probability/session"),
    Parameter("initial_refusal", "Initial refusal", 0.025, 0.15, "probability"),
    Parameter("privacy_penalty", "Privacy penalty", 0.20, 0.55, "logit coefficient"),
    Parameter("discomfort_dropout", "Embodiment dropout increment", 0.00, 0.02, "probability/week"),
    Parameter("crisis_sensitivity", "Alert sensitivity", 0.70, 0.95, "probability"),
    Parameter("false_alert_probability", "False-alert probability", 0.015, 0.06, "probability/week"),
    Parameter("review_minutes_per_alert", "Review time per alert", 4.0, 15.0, "minutes"),
    Parameter("fallback_screen_probability", "Screen fallback", 0.00, 0.90, "probability when down"),
    Parameter("routine_audit_minutes", "Routine audit", 0.0, 6.0, "minutes/participant"),
    Parameter("physical_near_miss_per_active_week", "Physical near-miss rate", 0.0, 0.0015, "probability/active week"),
]

SERVICE_PARAMETERS = [
    Parameter("arrivals_per_day", "Demand", 25.0, 45.0, "arrivals/working day"),
    Parameter("intake_servers", "Robot intake stations", 2.0, 5.0, "servers", discrete=True),
    Parameter("intake_minutes_mean", "Robot intake duration", 10.0, 18.0, "minutes"),
    Parameter("downtime_day_probability", "Day-level downtime", 0.00, 0.20, "probability/day"),
    Parameter("incomplete_probability", "Incomplete assessment", 0.03, 0.15, "probability/arrival"),
    Parameter("clinician_summary_saving_minutes", "Summary time saving", 2.0, 10.0, "minutes/arrival"),
    Parameter("clinician_review_minutes", "Mandatory review", 4.0, 15.0, "minutes/arrival"),
    Parameter("false_alert_probability", "False-alert probability", 0.03, 0.12, "probability/non-high-acuity arrival"),
    Parameter("high_acuity_detection_sensitivity", "High-acuity sensitivity", 0.70, 0.95, "probability"),
    Parameter("physical_reset_minutes", "Physical reset work", 0.0, 6.0, "minutes/intake"),
    Parameter("clinician_servers", "Clinician servers", 4.0, 7.0, "servers", discrete=True),
]

INDIVIDUAL_OUTCOMES = {
    "response_difference_pp": "Response difference (percentage points)",
    "completion_difference_pp": "Completion difference (percentage points)",
    "mean_phq9_change_difference": "Mean PHQ-9 change difference",
    "review_minutes_difference": "Review-time difference (minutes/participant)",
    "missed_crisis_difference": "Missed crisis-weeks difference per 100 crisis-weeks",
    "near_miss_difference": "Physical near-miss difference per 100 participants",
}

SERVICE_OUTCOMES = {
    "mean_wait_difference_minutes": "Mean wait difference (minutes)",
    "p90_wait_difference_minutes": "P90 wait difference (minutes)",
    "throughput_difference_per_day": "Throughput difference (assessments/day)",
    "abandonment_difference_pp": "Abandonment difference (percentage points)",
    "false_alert_difference_per_100": "False-alert difference per 100 arrivals",
    "missed_high_acuity_difference_pp": "Missed high-acuity difference (percentage points)",
    "clinician_utilization_difference_pp": "Clinician-utilization difference (percentage points)",
}


def _scale_unit_design(unit: np.ndarray, params: list[Parameter]) -> np.ndarray:
    low = np.asarray([p.low for p in params], dtype=float)
    high = np.asarray([p.high for p in params], dtype=float)
    return low + unit * (high - low)


def saltelli_design(params: list[Parameter], n_base: int, seed: int) -> tuple[np.ndarray, np.ndarray, list[np.ndarray], list[np.ndarray]]:
    """Return A, B, AB_i, BA_i matrices from a scrambled Sobol sequence."""
    if n_base <= 0 or n_base & (n_base - 1):
        raise ValueError("n_base must be a positive power of two")
    d = len(params)
    sampler = qmc.Sobol(d=2 * d, scramble=True, seed=seed)
    unit = sampler.random_base2(int(np.log2(n_base)))
    A = _scale_unit_design(unit[:, :d], params)
    B = _scale_unit_design(unit[:, d:], params)
    AB: list[np.ndarray] = []
    BA: list[np.ndarray] = []
    for i in range(d):
        ab = A.copy(); ab[:, i] = B[:, i]; AB.append(ab)
        ba = B.copy(); ba[:, i] = A[:, i]; BA.append(ba)
    return A, B, AB, BA


def _coerce(value: float, parameter: Parameter) -> float | int:
    if parameter.discrete:
        return int(np.clip(np.rint(value), parameter.low, parameter.high))
    return float(value)


def evaluate_individual(x: np.ndarray, inner_replications: int = 2, seed_key: int = 0, n_per_arm: int = 350) -> dict[str, float]:
    values = {p.name: _coerce(v, p) for p, v in zip(INDIVIDUAL_PARAMETERS, x, strict=True)}
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_cfg = replace(
        ARM_CONFIGS["robot_hitl"],
        engagement_intercept=screen_cfg.engagement_intercept + float(values["engagement_logit_advantage"]),
        embodiment_effect=float(values["embodiment_effect"]),
        downtime=float(values["downtime"]),
        initial_refusal=float(values["initial_refusal"]),
        privacy_penalty=float(values["privacy_penalty"]),
        discomfort_dropout=float(values["discomfort_dropout"]),
        crisis_sensitivity=float(values["crisis_sensitivity"]),
        false_alert_probability=float(values["false_alert_probability"]),
        review_minutes_per_alert=float(values["review_minutes_per_alert"]),
        fallback_screen_probability=float(values["fallback_screen_probability"]),
        routine_audit_minutes=float(values["routine_audit_minutes"]),
        physical_near_miss_per_active_week=float(values["physical_near_miss_per_active_week"]),
    )
    rows: list[dict[str, float]] = []
    for r in range(inner_replications):
        cohort_seed = SEED + 30_000_000 + seed_key * 101 + r * 1_000_003
        screen, _ = simulate_arm(
            screen_cfg, n=n_per_arm, weeks=12, seed=cohort_seed,
            cohort_seed=cohort_seed, event_seed=cohort_seed + 17,
        )
        robot, _ = simulate_arm(
            robot_cfg, n=n_per_arm, weeks=12, seed=cohort_seed,
            cohort_seed=cohort_seed, event_seed=cohort_seed + 37,
        )
        s = summarize_individual(screen)
        q = summarize_individual(robot)
        rows.append({
            "response_difference_pp": float(q["response_percent"] - s["response_percent"]),
            "completion_difference_pp": float(q["completion_percent"] - s["completion_percent"]),
            "mean_phq9_change_difference": float(q["mean_phq9_change"] - s["mean_phq9_change"]),
            "review_minutes_difference": float(q["mean_clinician_review_minutes"] - s["mean_clinician_review_minutes"]),
            "missed_crisis_difference": float(q["missed_crises_per_100_crisis_weeks"] - s["missed_crises_per_100_crisis_weeks"]),
            "near_miss_difference": float(q["physical_near_misses_per_100"] - s["physical_near_misses_per_100"]),
        })
    return pd.DataFrame(rows).mean().to_dict()


def evaluate_service(x: np.ndarray, inner_replications: int = 2, seed_key: int = 0, days: int = 18) -> dict[str, float]:
    values = {p.name: _coerce(v, p) for p, v in zip(SERVICE_PARAMETERS, x, strict=True)}
    arrivals = float(values["arrivals_per_day"])
    clinicians = int(values["clinician_servers"])
    screen_cfg = replace(CONFIGS["screen"], days=days, arrivals_per_day=arrivals, clinician_servers=clinicians)
    robot_cfg = replace(
        CONFIGS["robot_hitl"],
        days=days,
        arrivals_per_day=arrivals,
        intake_servers=int(values["intake_servers"]),
        intake_minutes_mean=float(values["intake_minutes_mean"]),
        downtime_day_probability=float(values["downtime_day_probability"]),
        incomplete_probability=float(values["incomplete_probability"]),
        clinician_servers=clinicians,
        clinician_summary_saving_minutes=float(values["clinician_summary_saving_minutes"]),
        clinician_review_minutes=float(values["clinician_review_minutes"]),
        false_alert_probability=float(values["false_alert_probability"]),
        high_acuity_detection_sensitivity=float(values["high_acuity_detection_sensitivity"]),
        physical_reset_minutes=float(values["physical_reset_minutes"]),
    )
    rows: list[dict[str, float]] = []
    for r in range(inner_replications):
        stream_seed = SEED + 40_000_000 + seed_key * 101 + r * 1_000_003
        outages, arrivals_stream = generate_random_stream(screen_cfg, stream_seed)
        s = simulate_one_from_stream(screen_cfg, outages, arrivals_stream)
        q = simulate_one_from_stream(robot_cfg, outages, arrivals_stream)
        rows.append({
            "mean_wait_difference_minutes": float(q["mean_wait_minutes"] - s["mean_wait_minutes"]),
            "p90_wait_difference_minutes": float(q["p90_wait_minutes"] - s["p90_wait_minutes"]),
            "throughput_difference_per_day": float(q["throughput_per_day"] - s["throughput_per_day"]),
            "abandonment_difference_pp": float(q["abandonment_percent"] - s["abandonment_percent"]),
            "false_alert_difference_per_100": float(q["false_alerts_per_100_arrivals"] - s["false_alerts_per_100_arrivals"]),
            "missed_high_acuity_difference_pp": float(q["missed_high_acuity_percent"] - s["missed_high_acuity_percent"]),
            "clinician_utilization_difference_pp": float(q["mean_clinician_utilization_percent"] - s["mean_clinician_utilization_percent"]),
        })
    return pd.DataFrame(rows).mean().to_dict()


def evaluate_matrix(matrix: np.ndarray, evaluator: Callable[[np.ndarray, int, int], dict[str, float]], inner_replications: int, label: str) -> pd.DataFrame:
    rows = []
    for i, x in enumerate(matrix):
        result = evaluator(x, inner_replications, i)
        result["sample_id"] = i
        rows.append(result)
        if (i + 1) % 128 == 0:
            print(f"{label}: evaluated {i + 1}/{len(matrix)}", flush=True)
    return pd.DataFrame(rows).set_index("sample_id")


def sobol_indices(A: np.ndarray, B: np.ndarray, AB: list[np.ndarray], BA: list[np.ndarray], parameter_names: list[str], outcome: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    ya = A[outcome].to_numpy(dtype=float)
    yb = B[outcome].to_numpy(dtype=float)
    yab = [df[outcome].to_numpy(dtype=float) for df in AB]
    yba = [df[outcome].to_numpy(dtype=float) for df in BA]
    var_y = float(np.var(np.r_[ya, yb], ddof=1))
    if not np.isfinite(var_y) or var_y <= 1e-15:
        first = np.zeros(len(parameter_names)); total = np.zeros(len(parameter_names))
    else:
        first = np.asarray([np.mean(yb * (yab[i] - ya)) / var_y for i in range(len(parameter_names))])
        total = np.asarray([0.5 * np.mean((ya - yab[i]) ** 2) / var_y for i in range(len(parameter_names))])
    main = pd.DataFrame({"parameter": parameter_names, "S1": first, "ST": total})

    second_rows = []
    for j in range(len(parameter_names)):
        for k in range(j + 1, len(parameter_names)):
            if var_y <= 1e-15:
                value = 0.0
            else:
                value = float(np.mean(yba[j] * yab[k] - ya * yb) / var_y - first[j] - first[k])
            second_rows.append({"parameter_1": parameter_names[j], "parameter_2": parameter_names[k], "S2": value})
    return main, pd.DataFrame(second_rows)


def bootstrap_sobol(A: pd.DataFrame, B: pd.DataFrame, AB: list[pd.DataFrame], BA: list[pd.DataFrame], parameter_names: list[str], outcome: str, n_boot: int = 200, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compute point estimates and row-bootstrap intervals using NumPy arrays."""
    ya = A[outcome].to_numpy(dtype=float)
    yb = B[outcome].to_numpy(dtype=float)
    yab = np.vstack([df[outcome].to_numpy(dtype=float) for df in AB])
    yba = np.vstack([df[outcome].to_numpy(dtype=float) for df in BA])
    d, n = yab.shape
    pairs = [(j, k) for j in range(d) for k in range(j + 1, d)]

    def calc(idx: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        a = ya[idx]; b = yb[idx]; ab = yab[:, idx]; ba = yba[:, idx]
        var_y = float(np.var(np.r_[a, b], ddof=1))
        if not np.isfinite(var_y) or var_y <= 1e-15:
            return np.zeros(d), np.zeros(d), np.zeros(len(pairs))
        s1 = np.mean(b[None, :] * (ab - a[None, :]), axis=1) / var_y
        st = 0.5 * np.mean((a[None, :] - ab) ** 2, axis=1) / var_y
        s2 = np.asarray([
            np.mean(ba[j] * ab[k] - a * b) / var_y - s1[j] - s1[k]
            for j, k in pairs
        ], dtype=float)
        return s1, st, s2

    full_idx = np.arange(n)
    point_s1, point_st, point_s2 = calc(full_idx)
    rng = np.random.default_rng(seed)
    boot_s1 = np.empty((n_boot, d)); boot_st = np.empty((n_boot, d)); boot_s2 = np.empty((n_boot, len(pairs)))
    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        boot_s1[b], boot_st[b], boot_s2[b] = calc(idx)
    main = pd.DataFrame({
        "parameter": parameter_names,
        "S1": point_s1,
        "ST": point_st,
        "S1_low": np.quantile(boot_s1, 0.025, axis=0),
        "S1_high": np.quantile(boot_s1, 0.975, axis=0),
        "ST_low": np.quantile(boot_st, 0.025, axis=0),
        "ST_high": np.quantile(boot_st, 0.975, axis=0),
    })
    second = pd.DataFrame({
        "parameter_1": [parameter_names[j] for j, _ in pairs],
        "parameter_2": [parameter_names[k] for _, k in pairs],
        "S2": point_s2,
        "S2_low": np.quantile(boot_s2, 0.025, axis=0),
        "S2_high": np.quantile(boot_s2, 0.975, axis=0),
    })
    return main, second

def _run_model(
    model: str,
    params: list[Parameter],
    outcomes: dict[str, str],
    evaluator: Callable[[np.ndarray, int, int], dict[str, float]],
    n_base: int,
    inner_replications: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    A_x, B_x, AB_x, BA_x = saltelli_design(params, n_base=n_base, seed=SEED + (1 if model == "individual" else 2))
    A = evaluate_matrix(A_x, evaluator, inner_replications, f"{model}:A")
    B = evaluate_matrix(B_x, evaluator, inner_replications, f"{model}:B")
    AB = [evaluate_matrix(m, evaluator, inner_replications, f"{model}:AB{i + 1}") for i, m in enumerate(AB_x)]
    BA = [evaluate_matrix(m, evaluator, inner_replications, f"{model}:BA{i + 1}") for i, m in enumerate(BA_x)]

    raw_dir = OUTPUT_DIR / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # Retain the complete Saltelli design and every evaluated matrix so that
    # the indices can be recomputed without rerunning either simulator.
    input_frames: list[pd.DataFrame] = []
    output_frames: list[pd.DataFrame] = []
    parameter_columns = [p.name for p in params]
    for matrix_label, input_matrix, output_matrix in [
        ("A", A_x, A),
        ("B", B_x, B),
        *[(f"AB_{i + 1}", matrix, frame) for i, (matrix, frame) in enumerate(zip(AB_x, AB, strict=True))],
        *[(f"BA_{i + 1}", matrix, frame) for i, (matrix, frame) in enumerate(zip(BA_x, BA, strict=True))],
    ]:
        input_frame = pd.DataFrame(input_matrix, columns=parameter_columns)
        input_frame.insert(0, "sample_id", np.arange(len(input_frame), dtype=int))
        input_frame.insert(0, "matrix", matrix_label)
        input_frames.append(input_frame)

        output_frame = output_matrix.reset_index().copy()
        output_frame.insert(0, "matrix", matrix_label)
        output_frames.append(output_frame)

    pd.concat(input_frames, ignore_index=True).to_csv(
        raw_dir / f"{model}_saltelli_design_inputs.csv", index=False
    )
    pd.concat(output_frames, ignore_index=True).to_csv(
        raw_dir / f"{model}_saltelli_matrix_outputs.csv", index=False
    )

    all_main = []
    all_second = []
    names = [p.name for p in params]
    labels = {p.name: p.label for p in params}
    for k, (outcome, outcome_label) in enumerate(outcomes.items()):
        main, second = bootstrap_sobol(A, B, AB, BA, names, outcome, n_boot=200, seed=SEED + 10_000 + k)
        main.insert(0, "model", model); main.insert(1, "outcome", outcome); main.insert(2, "outcome_label", outcome_label)
        main["parameter_label"] = main["parameter"].map(labels)
        second.insert(0, "model", model); second.insert(1, "outcome", outcome); second.insert(2, "outcome_label", outcome_label)
        second["parameter_1_label"] = second["parameter_1"].map(labels)
        second["parameter_2_label"] = second["parameter_2"].map(labels)
        all_main.append(main); all_second.append(second)
    main_df = pd.concat(all_main, ignore_index=True)
    second_df = pd.concat(all_second, ignore_index=True)
    main_df["n_base"] = n_base; main_df["inner_replications"] = inner_replications
    second_df["n_base"] = n_base; second_df["inner_replications"] = inner_replications
    return main_df, second_df


def create_summary_figure(main_df: pd.DataFrame, second_df: pd.DataFrame, model: str, outcome: str, filename: str) -> None:
    subset = main_df[(main_df["model"] == model) & (main_df["outcome"] == outcome)].copy()
    subset["plot_ST"] = subset["ST"].clip(lower=0)
    subset["plot_S1"] = subset["S1"].clip(lower=0)
    subset = subset.sort_values("plot_ST", ascending=True).tail(10)
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 5.7), gridspec_kw={"width_ratios": [1.0, 1.05]})
    y = np.arange(len(subset))
    axes[0].barh(y, subset["plot_ST"], label="Total-order (ST)", alpha=0.85)
    axes[0].barh(y, subset["plot_S1"], label="First-order (S1)", alpha=0.85)
    axes[0].set_yticks(y, subset["parameter_label"])
    axes[0].set_xlabel("Sobol variance share")
    axes[0].set_title("Main and total effects")
    axes[0].legend(frameon=False)
    axes[0].grid(axis="x", alpha=0.25)

    inter = second_df[(second_df["model"] == model) & (second_df["outcome"] == outcome)].copy()
    labels = list(subset["parameter"].iloc[::-1])[:8]
    labels = list(dict.fromkeys(labels))
    matrix = np.zeros((len(labels), len(labels)))
    for i, p1 in enumerate(labels):
        for j, p2 in enumerate(labels):
            if i == j:
                matrix[i, j] = np.nan
            elif i < j:
                hit = inter[((inter.parameter_1 == p1) & (inter.parameter_2 == p2)) | ((inter.parameter_1 == p2) & (inter.parameter_2 == p1))]
                if not hit.empty:
                    matrix[i, j] = matrix[j, i] = float(hit.iloc[0].S2)
    max_abs = max(float(np.nanmax(np.abs(matrix))) if np.isfinite(matrix).any() else 0.01, 0.01)
    im = axes[1].imshow(matrix, vmin=-max_abs, vmax=max_abs, cmap="coolwarm")
    display = {p.name: p.label for p in (INDIVIDUAL_PARAMETERS if model == "individual" else SERVICE_PARAMETERS)}
    axes[1].set_xticks(range(len(labels)), [display[x] for x in labels], rotation=55, ha="right")
    axes[1].set_yticks(range(len(labels)), [display[x] for x in labels])
    axes[1].set_title("Pairwise second-order effects (S2)")
    fig.colorbar(im, ax=axes[1], label="Sobol interaction index", fraction=0.046, pad=0.04)
    fig.suptitle(subset["outcome_label"].iloc[0])
    fig.tight_layout()
    save_figure(fig, FIGURE_ROOT, filename)


def create_ranked_summary(main_df: pd.DataFrame, second_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, outcome, label), group in main_df.groupby(["model", "outcome", "outcome_label"], sort=False):
        top_total = group.sort_values("ST", ascending=False).iloc[0]
        inter = second_df[(second_df.model == model) & (second_df.outcome == outcome)].sort_values("S2", ascending=False)
        top_inter = inter.iloc[0] if not inter.empty else None
        rows.append({
            "model": model,
            "outcome": outcome,
            "outcome_label": label,
            "largest_total_order_parameter": top_total["parameter"],
            "largest_total_order_parameter_label": top_total["parameter_label"],
            "largest_total_order_ST": float(top_total["ST"]),
            "largest_first_order_S1": float(top_total["S1"]),
            "largest_interaction": "" if top_inter is None else f"{top_inter['parameter_1_label']} x {top_inter['parameter_2_label']}",
            "largest_interaction_S2": np.nan if top_inter is None else float(top_inter["S2"]),
        })
    return pd.DataFrame(rows)


def main(n_base: int = 128, inner_replications: int = 2) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    individual_main, individual_second = _run_model(
        "individual", INDIVIDUAL_PARAMETERS, INDIVIDUAL_OUTCOMES, evaluate_individual,
        n_base=n_base, inner_replications=inner_replications,
    )
    service_main, service_second = _run_model(
        "service", SERVICE_PARAMETERS, SERVICE_OUTCOMES, evaluate_service,
        n_base=n_base, inner_replications=inner_replications,
    )
    main_df = pd.concat([individual_main, service_main], ignore_index=True)
    second_df = pd.concat([individual_second, service_second], ignore_index=True)
    main_df.to_csv(OUTPUT_DIR / "sobol_first_total_indices.csv", index=False)
    second_df.to_csv(OUTPUT_DIR / "sobol_second_order_indices.csv", index=False)
    summary = create_ranked_summary(main_df, second_df)
    summary.to_csv(OUTPUT_DIR / "sobol_ranked_summary.csv", index=False)

    create_summary_figure(main_df, second_df, "individual", "response_difference_pp", "figure_16_global_sensitivity_individual")
    create_summary_figure(main_df, second_df, "service", "mean_wait_difference_minutes", "figure_17_global_sensitivity_service")

    metadata = {
        "method": "Scrambled Sobol A/B cross-sampling with Saltelli first-, total-, and second-order estimators",
        "seed": SEED,
        "n_base": n_base,
        "inner_replications": inner_replications,
        "bootstrap_resamples": 200,
        "input_distribution": "Independent Uniform distributions over the declared parameter ranges",
        "individual_parameters": len(INDIVIDUAL_PARAMETERS),
        "service_parameters": len(SERVICE_PARAMETERS),
        "individual_participants_per_arm_per_inner_evaluation": 350,
        "service_observed_days_per_inner_evaluation": 18,
        "individual_evaluations": n_base * (2 * len(INDIVIDUAL_PARAMETERS) + 2),
        "service_evaluations": n_base * (2 * len(SERVICE_PARAMETERS) + 2),
        "raw_design_files": [
            "raw/individual_saltelli_design_inputs.csv",
            "raw/service_saltelli_design_inputs.csv",
        ],
        "raw_output_files": [
            "raw/individual_saltelli_matrix_outputs.csv",
            "raw/service_saltelli_matrix_outputs.csv",
        ],
        "interpretation": "Variance decomposition over declared independent uniform ranges; not a posterior uncertainty distribution.",
    }
    (OUTPUT_DIR / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
