"""Build journal-oriented figures from current simulation outputs.

The original v4 figures are preserved. This script creates a separate set that
uses distribution-revealing plots for replicated outcomes, grayscale-safe line
encodings, and the reviewer-motivated sensitivity analyses.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from figure_utils import save_figure
from individual_microsimulation import ARM_CONFIGS
from service_queue_simulation import CONFIGS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
REVIEW = OUT / "reviewer_reanalysis"
FIG = ROOT / "figures" / "journal"


def _box_with_mean_ci(ax, datasets, labels, means, lows, highs, ylabel, title):
    positions = np.arange(1, len(labels) + 1)
    box = ax.boxplot(datasets, positions=positions, widths=0.58, showfliers=False, patch_artist=True)
    for patch in box["boxes"]:
        patch.set_facecolor("white")
        patch.set_edgecolor("black")
    for key in ["whiskers", "caps", "medians"]:
        for artist in box[key]:
            artist.set_color("black")
    rng = np.random.default_rng(41)
    for x, values in zip(positions, datasets, strict=True):
        jitter = rng.normal(0, 0.045, len(values))
        ax.scatter(np.full(len(values), x) + jitter, values, s=8, alpha=0.17, color="black", linewidths=0)
    means = np.asarray(means, float)
    lows = np.asarray(lows, float)
    highs = np.asarray(highs, float)
    ax.errorbar(positions, means, yerr=np.vstack([means - lows, highs - means]), fmt="D", color="black", mfc="white", capsize=3, label="Mean and 95% BCa CI")
    ax.set_xticks(positions, labels, rotation=18, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.20)


def patient_trajectory():
    df = pd.read_csv(OUT / "individual_weekly_bootstrap_summary.csv")
    order = [ARM_CONFIGS[k].name for k in ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]]
    labels = ["Usual care", "Screen agent", "Embodied robot", "Robot plus human gate"]
    styles = ["-", "--", "-.", ":"]
    markers = ["o", "s", "^", "D"]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for arm, label, style, marker in zip(order, labels, styles, markers, strict=True):
        group = df[df["arm"] == arm].sort_values("week")
        ax.plot(group["week"], group["mean_phq9_locf_mean"], linestyle=style, marker=marker, color="black", label=label)
        ax.fill_between(group["week"], group["mean_phq9_locf_ci_low"], group["mean_phq9_locf_ci_high"], color="black", alpha=0.06)
    ax.set_xlabel("Week")
    ax.set_ylabel("Mean PHQ-9 under last-observation-carried-forward")
    ax.set_title("Synthetic symptom trajectories")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.20)
    fig.tight_layout()
    save_figure(fig, FIG, "figure_1_patient_trajectories")


def patient_endpoints():
    rep = pd.read_csv(OUT / "individual_replication_results.csv")
    summary = pd.read_csv(OUT / "individual_arm_replication_summary.csv").set_index("arm")
    order = [ARM_CONFIGS[k].name for k in ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]]
    labels = ["Usual care", "Screen", "Robot", "Robot plus gate"]
    metrics = [
        ("response_percent", "Participants (%)", "Response"),
        ("remission_percent", "Participants (%)", "Remission"),
        ("completion_percent", "Participants (%)", "Completed 12 weeks"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.5), constrained_layout=True)
    for ax, (metric, ylabel, title) in zip(axes, metrics, strict=True):
        datasets = [rep.loc[rep["arm"] == arm, metric].to_numpy() for arm in order]
        means = [summary.loc[arm, f"{metric}_mean"] for arm in order]
        lows = [summary.loc[arm, f"{metric}_ci_low"] for arm in order]
        highs = [summary.loc[arm, f"{metric}_ci_high"] for arm in order]
        _box_with_mean_ci(ax, datasets, labels, means, lows, highs, ylabel, title)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.04))
    save_figure(fig, FIG, "figure_2_patient_endpoints")


def patient_contrasts():
    con = pd.read_csv(OUT / "individual_contrast_summary.csv")
    robot = ARM_CONFIGS["robot_hitl"].name
    subset = con[(con["comparator"] == robot) & con["metric"].isin(["response_percent", "remission_percent", "completion_percent"])].copy()
    order = ["completion_percent", "remission_percent", "response_percent"]
    subset["metric"] = pd.Categorical(subset["metric"], categories=order, ordered=True)
    subset = subset.sort_values("metric")
    labels = {"response_percent": "Response", "remission_percent": "Remission", "completion_percent": "Completion"}
    means = subset["mean_difference"].to_numpy(float)
    low = means - subset["bootstrap_ci_low"].to_numpy(float)
    high = subset["bootstrap_ci_high"].to_numpy(float) - means
    fig, ax = plt.subplots(figsize=(7.8, 4.2))
    ax.errorbar(means, np.arange(len(subset)), xerr=np.vstack([low, high]), fmt="o", color="black", mfc="white", capsize=4, linestyle="none")
    ax.axvline(0, linestyle="--", linewidth=1, color="black")
    ax.set_yticks(np.arange(len(subset)), [labels[str(x)] for x in subset["metric"]])
    ax.set_xlabel("Robot plus human gate minus screen percentage points")
    ax.set_title("Primary patient-level threshold contrasts")
    ax.grid(axis="x", alpha=0.20)
    fig.tight_layout()
    save_figure(fig, FIG, "figure_3_patient_contrasts")


def patient_safety_labor():
    rep = pd.read_csv(OUT / "individual_replication_results.csv")
    summary = pd.read_csv(OUT / "individual_arm_replication_summary.csv").set_index("arm")
    order = [ARM_CONFIGS[k].name for k in ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]]
    labels = ["Usual care", "Screen", "Robot", "Robot plus gate"]
    metrics = [
        ("false_alerts_per_100", "Per 100 participants", "False alerts"),
        ("missed_crises_per_100_crisis_weeks", "Per 100 high-risk weeks", "Missed high-risk weeks"),
        ("mean_clinician_review_minutes", "Minutes per participant", "Clinician review"),
        ("physical_near_misses_per_100", "Per 100 participants", "Physical near-misses"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 8.0), constrained_layout=True)
    for ax, (metric, ylabel, title) in zip(axes.flat, metrics, strict=True):
        datasets = [rep.loc[rep["arm"] == arm, metric].to_numpy() for arm in order]
        means = [summary.loc[arm, f"{metric}_mean"] for arm in order]
        lows = [summary.loc[arm, f"{metric}_ci_low"] for arm in order]
        highs = [summary.loc[arm, f"{metric}_ci_high"] for arm in order]
        _box_with_mean_ci(ax, datasets, labels, means, lows, highs, ylabel, title)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.02))
    save_figure(fig, FIG, "figure_4_patient_safety_labor")


def service_wait():
    rep = pd.read_csv(OUT / "system_replication_results.csv")
    summary = pd.read_csv(OUT / "system_scenario_summary.csv").set_index("scenario")
    order = [CONFIGS[k].name for k in ["manual", "screen", "robot", "robot_hitl"]]
    labels = ["Manual", "Screen", "Robot", "Robot plus gate"]
    datasets = [rep.loc[rep["scenario"] == s, "mean_wait_minutes"].to_numpy() for s in order]
    means = [summary.loc[s, "mean_wait_minutes_mean"] for s in order]
    lows = [summary.loc[s, "mean_wait_minutes_ci_low"] for s in order]
    highs = [summary.loc[s, "mean_wait_minutes_ci_high"] for s in order]
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    _box_with_mean_ci(ax, datasets, labels, means, lows, highs, "Mean wait per replication in working minutes", "Service waiting-time distributions")
    ax.legend(frameon=False)
    fig.tight_layout()
    save_figure(fig, FIG, "figure_5_service_wait")


def service_safety_access():
    rep = pd.read_csv(OUT / "system_replication_results.csv")
    summary = pd.read_csv(OUT / "system_scenario_summary.csv").set_index("scenario")
    order = [CONFIGS[k].name for k in ["manual", "screen", "robot", "robot_hitl"]]
    labels = ["Manual", "Screen", "Robot", "Robot plus gate"]
    metrics = [
        ("false_alerts_per_100_arrivals", "Per 100 arrivals", "False alerts"),
        ("missed_high_acuity_percent", "Percentage points", "Missed high-acuity cases"),
        ("abandonment_percent", "Percentage points", "Abandonment"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11.2, 4.6), constrained_layout=True)
    for ax, (metric, ylabel, title) in zip(axes, metrics, strict=True):
        datasets = [rep.loc[rep["scenario"] == s, metric].to_numpy() for s in order]
        means = [summary.loc[s, f"{metric}_mean"] for s in order]
        lows = [summary.loc[s, f"{metric}_ci_low"] for s in order]
        highs = [summary.loc[s, f"{metric}_ci_high"] for s in order]
        _box_with_mean_ci(ax, datasets, labels, means, lows, highs, ylabel, title)
    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, legend_labels, loc="upper center", frameon=False, bbox_to_anchor=(0.5, 1.04))
    save_figure(fig, FIG, "figure_6_service_safety_access")


def supplementary_figures():
    # Retain the existing colorblind-safe heatmaps and diagnostics as reproducible copies.
    import shutil
    copies = {
        "individual_sensitivity_heatmap": "figure_s1_response_sensitivity",
        "system_sensitivity_heatmap": "figure_s5_service_break_even",
        "system_contrast_intervals": "figure_s4_service_contrasts",
        "system_warmup_diagnostic": "figure_s6_warmup_diagnostic",
    }
    for source, target in copies.items():
        for ext in ["png", "svg"]:
            src = ROOT / "figures" / ext / f"{source}.{ext}"
            dest_dir = FIG / ext
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / f"{target}.{ext}")

    # Nested parameter scenarios replace the single-run scenario scatter.
    pu = pd.read_csv(REVIEW / "individual_parameter_uncertainty_nested.csv")
    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    ax.scatter(pu["response_difference_percentage_points"], pu["completion_difference_percentage_points"], s=22, alpha=0.45, color="black")
    ax.axvline(0, linestyle="--", linewidth=1, color="black")
    ax.axhline(0, linestyle="--", linewidth=1, color="black")
    ax.set_xlabel("Robot plus human gate minus screen response percentage points")
    ax.set_ylabel("Robot plus human gate minus screen completion percentage points")
    ax.set_title("Nested scenario uncertainty across broad input ranges")
    ax.grid(alpha=0.20)
    fig.tight_layout()
    save_figure(fig, FIG, "figure_s2_nested_parameter_uncertainty")

    rep = pd.read_csv(OUT / "system_replication_results.csv")
    summary = pd.read_csv(OUT / "system_scenario_summary.csv").set_index("scenario")
    order = [CONFIGS[k].name for k in ["manual", "screen", "robot", "robot_hitl"]]
    labels = ["Manual", "Screen", "Robot", "Robot plus gate"]
    datasets = [rep.loc[rep["scenario"] == s, "throughput_per_day"].to_numpy() for s in order]
    means = [summary.loc[s, "throughput_per_day_mean"] for s in order]
    lows = [summary.loc[s, "throughput_per_day_ci_low"] for s in order]
    highs = [summary.loc[s, "throughput_per_day_ci_high"] for s in order]
    fig, ax = plt.subplots(figsize=(8.3, 5.0))
    _box_with_mean_ci(ax, datasets, labels, means, lows, highs, "Completed assessments per working day", "Service throughput distributions")
    ax.legend(frameon=False)
    fig.tight_layout()
    save_figure(fig, FIG, "figure_s3_service_throughput")

    # Copy reviewer reanalysis figures.
    mapping = {
        "individual_estimand_sensitivity": "figure_s7_estimand_sensitivity",
        "service_capacity_sensitivity": "figure_s8_capacity_sensitivity",
        "patient_pathway_bundle_ablation": "figure_s9_pathway_bundle_ablation",
    }
    for source, target in mapping.items():
        for ext in ["png", "svg"]:
            src = ROOT / "figures" / "reviewer_reanalysis" / ext / f"{source}.{ext}"
            dest_dir = FIG / ext
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / f"{target}.{ext}")


def main():
    patient_trajectory()
    patient_endpoints()
    patient_contrasts()
    patient_safety_labor()
    service_wait()
    service_safety_access()
    supplementary_figures()
    print(f"Journal figure set written to {FIG}")


if __name__ == "__main__":
    main()
