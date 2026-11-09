"""Reviewer-motivated sensitivity analyses for the physical AI simulation manuscript.

These analyses preserve the v4.0 primary outputs and add four explicitly
exploratory diagnostics requested during scientific review:

1. Endpoint estimand sensitivity under differential attrition.
2. Service capacity sensitivity to the number of embodied intake stations.
3. Nested replication within the broad parameter-scenario ensemble.
4. One-block-at-a-time decomposition of the bundled patient pathway contrast.

No analysis in this file estimates a real clinical effect. All outputs remain
conditional on the model structure and illustrative parameters.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_utils import save_figure
from individual_microsimulation import ARM_CONFIGS, SEED as IND_SEED, simulate_arm
from service_queue_simulation import (
    CONFIGS,
    SEED as SYS_SEED,
    generate_random_stream,
    simulate_one_from_stream,
)
from stats_utils import bootstrap_mean_ci

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "reviewer_reanalysis"
FIG = ROOT / "figures" / "reviewer_reanalysis"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)


def _boot(values: list[float] | np.ndarray, label: str, n_resamples: int = 5000) -> dict[str, float | int | str]:
    return bootstrap_mean_ci(values, n_resamples=n_resamples, seed=label, method="BCa")


def _estimand_metrics(patient: pd.DataFrame) -> dict[str, float]:
    baseline = patient["baseline_phq9"].to_numpy(float)
    locf = patient["week12_phq9_locf"].to_numpy(float)
    completed = patient["completed_12_weeks"].to_numpy(bool)
    bocf = np.where(completed, locf, baseline)

    def response(endpoint: np.ndarray, mask: np.ndarray | None = None) -> float:
        use = np.ones(endpoint.size, dtype=bool) if mask is None else mask
        return float(np.mean((baseline[use] - endpoint[use]) >= (0.50 * baseline[use])) * 100)

    def remission(endpoint: np.ndarray, mask: np.ndarray | None = None) -> float:
        use = np.ones(endpoint.size, dtype=bool) if mask is None else mask
        return float(np.mean(endpoint[use] <= 4.0) * 100)

    if not completed.any():
        completer_response = np.nan
        completer_remission = np.nan
        completer_change = np.nan
    else:
        completer_response = response(locf, completed)
        completer_remission = remission(locf, completed)
        completer_change = float(np.mean(locf[completed] - baseline[completed]))

    return {
        "completion_percent": float(completed.mean() * 100),
        "response_locf_percent": response(locf),
        "response_bocf_percent": response(bocf),
        "response_completers_percent": completer_response,
        "remission_locf_percent": remission(locf),
        "remission_bocf_percent": remission(bocf),
        "remission_completers_percent": completer_remission,
        "mean_change_locf": float(np.mean(locf - baseline)),
        "mean_change_bocf": float(np.mean(bocf - baseline)),
        "mean_change_completers": completer_change,
    }


def run_estimand_sensitivity(replications: int = 200, n_per_arm: int = 1200) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare LOCF, baseline-observation-carried-forward, and completer-only endpoints."""
    arm_rows: list[dict[str, float | int | str]] = []
    delta_rows: list[dict[str, float | int | str]] = []
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_cfg = ARM_CONFIGS["robot_hitl"]
    base_seed = IND_SEED + 240_000

    for replication in range(replications):
        cohort_seed = base_seed + replication * 1009
        screen, _ = simulate_arm(
            screen_cfg,
            n=n_per_arm,
            weeks=12,
            cohort_seed=cohort_seed,
            event_seed=cohort_seed + 1_000_003,
        )
        robot, _ = simulate_arm(
            robot_cfg,
            n=n_per_arm,
            weeks=12,
            cohort_seed=cohort_seed,
            event_seed=cohort_seed + 2_000_003,
        )
        screen_metrics = _estimand_metrics(screen)
        robot_metrics = _estimand_metrics(robot)
        for label, metrics in [("Screen agent", screen_metrics), ("Robot plus human gate", robot_metrics)]:
            arm_rows.append({"replication": replication, "pathway": label, **metrics})
        delta_rows.append({
            "replication": replication,
            **{f"delta_{metric}": robot_metrics[metric] - screen_metrics[metric] for metric in screen_metrics},
        })

    arms = pd.DataFrame(arm_rows)
    deltas = pd.DataFrame(delta_rows)
    arms.to_csv(OUT / "individual_estimand_sensitivity_replications.csv", index=False)
    deltas.to_csv(OUT / "individual_estimand_sensitivity_differences.csv", index=False)

    summary_rows: list[dict[str, float | int | str]] = []
    metrics = [c.removeprefix("delta_") for c in deltas.columns if c.startswith("delta_")]
    for metric in metrics:
        result = _boot(deltas[f"delta_{metric}"].to_numpy(), f"estimand:{metric}")
        summary_rows.append({
            "metric": metric,
            "robot_minus_screen_mean": result["mean"],
            "bootstrap_ci_low": result["bootstrap_ci_low"],
            "bootstrap_ci_high": result["bootstrap_ci_high"],
            "replications": replications,
            "n_per_arm_per_replication": n_per_arm,
            "bootstrap_method": result["bootstrap_method"],
            "bootstrap_resamples": result["bootstrap_resamples"],
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "individual_estimand_sensitivity_summary.csv", index=False)

    display = summary[summary["metric"].isin([
        "response_locf_percent", "response_bocf_percent", "response_completers_percent",
        "remission_locf_percent", "remission_bocf_percent", "remission_completers_percent",
    ])].copy()
    display["label"] = display["metric"].map({
        "response_locf_percent": "Response LOCF",
        "response_bocf_percent": "Response BOCF",
        "response_completers_percent": "Response completers",
        "remission_locf_percent": "Remission LOCF",
        "remission_bocf_percent": "Remission BOCF",
        "remission_completers_percent": "Remission completers",
    })
    display = display.iloc[::-1].reset_index(drop=True)
    means = display["robot_minus_screen_mean"].to_numpy(float)
    low = means - display["bootstrap_ci_low"].to_numpy(float)
    high = display["bootstrap_ci_high"].to_numpy(float) - means
    fig, ax = plt.subplots(figsize=(8.2, 4.8))
    ax.errorbar(means, np.arange(len(display)), xerr=np.vstack([low, high]), fmt="o", capsize=4, linestyle="none")
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.set_yticks(np.arange(len(display)), display["label"])
    ax.set_xlabel("Robot plus human gate minus screen percentage points")
    ax.set_title("Endpoint estimand sensitivity under differential attrition")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, FIG, "individual_estimand_sensitivity")
    return deltas, summary


def run_service_capacity_sensitivity(replications: int = 200) -> pd.DataFrame:
    """Vary embodied intake-station count while preserving all other base-case inputs."""
    screen = CONFIGS["screen"]
    server_counts = [2, 3, 4, 5]
    base_seed = SYS_SEED + 260_000
    rows: list[dict[str, float | int | str]] = []

    for replication in range(replications):
        outage, arrivals = generate_random_stream(screen, base_seed + replication * 1009)
        screen_row = simulate_one_from_stream(screen, outage, arrivals)
        for servers in server_counts:
            cfg = replace(
                CONFIGS["robot_hitl"],
                name=f"Robot plus human gate with {servers} intake stations",
                intake_servers=servers,
            )
            robot_row = simulate_one_from_stream(cfg, outage, arrivals)
            rows.append({
                "replication": replication,
                "robot_intake_servers": servers,
                "mean_wait_difference_minutes": robot_row["mean_wait_minutes"] - screen_row["mean_wait_minutes"],
                "p90_wait_difference_minutes": robot_row["p90_wait_minutes"] - screen_row["p90_wait_minutes"],
                "throughput_difference_per_day": robot_row["throughput_per_day"] - screen_row["throughput_per_day"],
                "abandonment_difference_percentage_points": robot_row["abandonment_percent"] - screen_row["abandonment_percent"],
                "clinician_utilization_difference_percentage_points": robot_row["mean_clinician_utilization_percent"] - screen_row["mean_clinician_utilization_percent"],
            })

    detail = pd.DataFrame(rows)
    detail.to_csv(OUT / "service_capacity_sensitivity_replications.csv", index=False)
    summary_rows: list[dict[str, float | int | str]] = []
    metrics = [c for c in detail.columns if c not in {"replication", "robot_intake_servers"}]
    for servers, group in detail.groupby("robot_intake_servers", sort=True):
        for metric in metrics:
            result = _boot(group[metric].to_numpy(), f"capacity:{servers}:{metric}")
            summary_rows.append({
                "robot_intake_servers": int(servers),
                "metric": metric,
                "robot_minus_screen_mean": result["mean"],
                "bootstrap_ci_low": result["bootstrap_ci_low"],
                "bootstrap_ci_high": result["bootstrap_ci_high"],
                "replications": replications,
                "bootstrap_method": result["bootstrap_method"],
                "bootstrap_resamples": result["bootstrap_resamples"],
            })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "service_capacity_sensitivity_summary.csv", index=False)

    wait = summary[summary["metric"] == "mean_wait_difference_minutes"].sort_values("robot_intake_servers")
    means = wait["robot_minus_screen_mean"].to_numpy(float)
    low = means - wait["bootstrap_ci_low"].to_numpy(float)
    high = wait["bootstrap_ci_high"].to_numpy(float) - means
    fig, ax = plt.subplots(figsize=(7.8, 4.8))
    ax.errorbar(wait["robot_intake_servers"], means, yerr=np.vstack([low, high]), marker="o", capsize=4)
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xticks(server_counts)
    ax.set_xlabel("Embodied intake stations")
    ax.set_ylabel("Mean wait difference versus screen in working minutes")
    ax.set_title("Service capacity sensitivity of the human-gated pathway")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save_figure(fig, FIG, "service_capacity_sensitivity")
    return summary


def run_nested_parameter_scenarios(draws: int = 250, inner_replications: int = 5, n_per_arm: int = 700) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Average each broad input scenario over repeated first-order simulations."""
    rng = np.random.default_rng(IND_SEED + 70_000)
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_base = ARM_CONFIGS["robot_hitl"]
    rows: list[dict[str, float | int]] = []
    base_seed = IND_SEED + 310_000

    for draw in range(draws):
        advantage = float(rng.uniform(0.00, 0.35))
        downtime = float(rng.uniform(0.00, 0.20))
        embodiment_effect = float(rng.uniform(0.00, 0.12))
        initial_refusal = float(rng.uniform(0.03, 0.12))
        discomfort_dropout = float(rng.uniform(0.002, 0.014))
        false_alert_probability = float(rng.uniform(0.018, 0.050))
        crisis_sensitivity = float(rng.uniform(0.78, 0.92))
        review_minutes = float(rng.uniform(6.0, 12.0))
        fallback_probability = float(rng.uniform(0.30, 0.85))
        robot_cfg = replace(
            robot_base,
            engagement_intercept=screen_cfg.engagement_intercept + advantage,
            embodiment_effect=embodiment_effect,
            downtime=downtime,
            initial_refusal=initial_refusal,
            discomfort_dropout=discomfort_dropout,
            false_alert_probability=false_alert_probability,
            crisis_sensitivity=crisis_sensitivity,
            review_minutes_per_alert=review_minutes,
            fallback_screen_probability=fallback_probability,
        )
        replicate_metrics: list[dict[str, float]] = []
        for inner in range(inner_replications):
            cohort_seed = base_seed + draw * 100_003 + inner * 1009
            screen, _ = simulate_arm(
                screen_cfg, n=n_per_arm, weeks=12,
                cohort_seed=cohort_seed, event_seed=cohort_seed + 1_000_003,
            )
            robot, _ = simulate_arm(
                robot_cfg, n=n_per_arm, weeks=12,
                cohort_seed=cohort_seed, event_seed=cohort_seed + 2_000_003,
            )
            replicate_metrics.append({
                "response_difference_percentage_points": (robot["response_50pct"].mean() - screen["response_50pct"].mean()) * 100,
                "completion_difference_percentage_points": (robot["completed_12_weeks"].mean() - screen["completed_12_weeks"].mean()) * 100,
                "mean_change_difference_phq9": robot["phq9_change"].mean() - screen["phq9_change"].mean(),
                "review_minutes_difference": robot["clinician_review_minutes"].mean() - screen["clinician_review_minutes"].mean(),
                "physical_near_miss_difference_per_100": (robot["physical_near_misses"].mean() - screen["physical_near_misses"].mean()) * 100,
            })
        mean_metrics = pd.DataFrame(replicate_metrics).mean().to_dict()
        rows.append({
            "draw": draw,
            "inner_replications": inner_replications,
            "engagement_logit_advantage": advantage,
            "robot_downtime": downtime,
            "embodiment_effect_phq9_per_engaged_week": embodiment_effect,
            "initial_refusal_probability": initial_refusal,
            "discomfort_dropout_increment": discomfort_dropout,
            "false_alert_probability": false_alert_probability,
            "crisis_sensitivity": crisis_sensitivity,
            "review_minutes_per_alert": review_minutes,
            "fallback_screen_probability": fallback_probability,
            **mean_metrics,
        })

    detail = pd.DataFrame(rows)
    detail.to_csv(OUT / "individual_parameter_uncertainty_nested.csv", index=False)
    definitions = {
        "response_positive": detail["response_difference_percentage_points"] > 0,
        "completion_negative": detail["completion_difference_percentage_points"] < 0,
        "phq_change_favorable": detail["mean_change_difference_phq9"] < 0,
        "review_positive": detail["review_minutes_difference"] > 0,
        "near_miss_positive": detail["physical_near_miss_difference_per_100"] > 0,
    }
    summary_rows = []
    for label, indicator in definitions.items():
        result = _boot(indicator.astype(float).to_numpy() * 100, f"nested-scenarios:{label}", n_resamples=10_000)
        summary_rows.append({
            "diagnostic": label,
            "percent_of_scenario_draws": result["mean"],
            "scenario_resampling_ci_low": result["bootstrap_ci_low"],
            "scenario_resampling_ci_high": result["bootstrap_ci_high"],
            "scenario_draws": draws,
            "inner_replications_per_draw": inner_replications,
        })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "individual_parameter_uncertainty_nested_summary.csv", index=False)
    return detail, summary


def run_patient_bundle_ablation(replications: int = 120, n_per_arm: int = 1200) -> pd.DataFrame:
    """One-block-at-a-time diagnostic showing that the pathway contrast is bundled.

    Each variant starts from the screen configuration and substitutes one block
    of human-gated robot parameters. Results are order-independent one-block
    contrasts, not additive component effects or causal mediation estimates.
    """
    screen = ARM_CONFIGS["screen_agent"]
    robot = ARM_CONFIGS["robot_hitl"]
    variants = {
        "Embodiment symptom increment only": replace(screen, name="Embodiment increment only", embodiment_effect=robot.embodiment_effect),
        "Engagement dynamics only": replace(screen, name="Engagement dynamics only", engagement_intercept=robot.engagement_intercept, weekly_decay=robot.weekly_decay),
        "Acceptance friction only": replace(screen, name="Acceptance friction only", initial_refusal=robot.initial_refusal, privacy_penalty=robot.privacy_penalty, discomfort_dropout=robot.discomfort_dropout),
        "Reliability and fallback only": replace(screen, name="Reliability and fallback only", downtime=robot.downtime, fallback_screen_probability=robot.fallback_screen_probability),
        "Safety oversight and physical exposure only": replace(
            screen,
            name="Safety oversight and physical exposure only",
            crisis_sensitivity=robot.crisis_sensitivity,
            false_alert_probability=robot.false_alert_probability,
            review_minutes_per_alert=robot.review_minutes_per_alert,
            routine_audit_minutes=robot.routine_audit_minutes,
            physical_near_miss_per_active_week=robot.physical_near_miss_per_active_week,
            human_verification=robot.human_verification,
        ),
        "Full human-gated pathway bundle": robot,
    }
    metrics = [
        "response_difference_percentage_points",
        "completion_difference_percentage_points",
        "review_minutes_difference",
        "physical_near_miss_difference_per_100",
    ]
    rows: list[dict[str, float | int | str]] = []
    base_seed = IND_SEED + 390_000
    for replication in range(replications):
        cohort_seed = base_seed + replication * 1009
        event_seed = cohort_seed + 7_000_003
        screen_pat, _ = simulate_arm(screen, n=n_per_arm, weeks=12, cohort_seed=cohort_seed, event_seed=event_seed)
        for label, cfg in variants.items():
            variant, _ = simulate_arm(cfg, n=n_per_arm, weeks=12, cohort_seed=cohort_seed, event_seed=event_seed)
            rows.append({
                "replication": replication,
                "parameter_block": label,
                "response_difference_percentage_points": (variant["response_50pct"].mean() - screen_pat["response_50pct"].mean()) * 100,
                "completion_difference_percentage_points": (variant["completed_12_weeks"].mean() - screen_pat["completed_12_weeks"].mean()) * 100,
                "review_minutes_difference": variant["clinician_review_minutes"].mean() - screen_pat["clinician_review_minutes"].mean(),
                "physical_near_miss_difference_per_100": (variant["physical_near_misses"].mean() - screen_pat["physical_near_misses"].mean()) * 100,
            })
    detail = pd.DataFrame(rows)
    detail.to_csv(OUT / "patient_pathway_bundle_ablation_replications.csv", index=False)
    summary_rows: list[dict[str, float | int | str]] = []
    for block, group in detail.groupby("parameter_block", sort=False):
        for metric in metrics:
            result = _boot(group[metric].to_numpy(), f"ablation:{block}:{metric}")
            summary_rows.append({
                "parameter_block": block,
                "metric": metric,
                "mean_difference_vs_screen": result["mean"],
                "bootstrap_ci_low": result["bootstrap_ci_low"],
                "bootstrap_ci_high": result["bootstrap_ci_high"],
                "replications": replications,
                "n_per_arm_per_replication": n_per_arm,
            })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(OUT / "patient_pathway_bundle_ablation_summary.csv", index=False)

    response = summary[summary["metric"] == "response_difference_percentage_points"].copy()
    completion = summary[summary["metric"] == "completion_difference_percentage_points"].copy()
    merged = response.merge(completion, on="parameter_block", suffixes=("_response", "_completion"))
    fig, ax = plt.subplots(figsize=(8.2, 5.3))
    ax.scatter(merged["mean_difference_vs_screen_response"], merged["mean_difference_vs_screen_completion"], s=45)
    for _, row in merged.iterrows():
        ax.annotate(row["parameter_block"].replace(" only", ""),
                    (row["mean_difference_vs_screen_response"], row["mean_difference_vs_screen_completion"]),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.axvline(0, linestyle="--", linewidth=1)
    ax.axhline(0, linestyle="--", linewidth=1)
    ax.set_xlabel("Response difference versus screen in percentage points")
    ax.set_ylabel("Completion difference versus screen in percentage points")
    ax.set_title("One-block-at-a-time decomposition of the bundled pathway")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save_figure(fig, FIG, "patient_pathway_bundle_ablation")
    return summary


def write_summary_json() -> None:
    paths = {
        "estimand": OUT / "individual_estimand_sensitivity_summary.csv",
        "capacity": OUT / "service_capacity_sensitivity_summary.csv",
        "nested": OUT / "individual_parameter_uncertainty_nested_summary.csv",
        "ablation": OUT / "patient_pathway_bundle_ablation_summary.csv",
    }
    payload = {name: pd.read_csv(path).to_dict(orient="records") for name, path in paths.items()}
    with open(OUT / "reviewer_reanalysis_summary.json", "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def main() -> None:
    print("Running endpoint estimand sensitivity...", flush=True)
    run_estimand_sensitivity()
    print("Running service capacity sensitivity...", flush=True)
    run_service_capacity_sensitivity()
    print("Running nested parameter scenarios...", flush=True)
    run_nested_parameter_scenarios()
    print("Running pathway bundle ablation...", flush=True)
    run_patient_bundle_ablation()
    write_summary_json()
    print(f"Reviewer reanalysis outputs written to {OUT}", flush=True)


if __name__ == "__main__":
    main()
