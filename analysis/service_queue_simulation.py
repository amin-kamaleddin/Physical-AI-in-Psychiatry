"""Synthetic service-level discrete-event simulation for physical AI in psychiatry.

The model represents an outpatient psychiatric intake pathway. It is an
assumption-driven research sandbox, not an estimate for any specific clinic.
It compares manual intake, a functionally matched screen kiosk, a realistic
embodied robot pathway, and an embodied robot pathway with a mandatory human
safety gate.

Version 2.0 uses common random numbers across pathways: each replication sees
an identical arrival, acuity, and latent random-draw stream. This improves the
precision and interpretability of paired pathway contrasts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Dict, List, NamedTuple
import heapq
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from figure_utils import save_figure
from stats_utils import (
    BOOTSTRAP_RESAMPLES,
    bootstrap_group_summary,
    bootstrap_mean_ci,
    paired_contrast_statistics,
    add_holm_columns,
)

SEED = 20260726
WORKDAY_MIN = 420.0


@dataclass(frozen=True)
class QueueConfig:
    name: str
    arrivals_per_day: float
    days: int
    warmup_days: int
    intake_servers: int
    intake_minutes_mean: float
    intake_minutes_sd: float
    human_fallback_servers: int
    human_fallback_minutes_mean: float
    downtime_day_probability: float
    incomplete_probability: float
    incomplete_rework_minutes: float
    clinician_servers: int
    clinician_summary_saving_minutes: float
    clinician_review_minutes: float
    false_alert_probability: float
    high_acuity_detection_sensitivity: float
    physical_reset_minutes: float
    robot_or_kiosk: bool
    human_verification: bool


CONFIGS: Dict[str, QueueConfig] = {
    "manual": QueueConfig(
        name="Manual intake",
        arrivals_per_day=35.0,
        days=35,
        warmup_days=5,
        intake_servers=2,
        intake_minutes_mean=24.0,
        intake_minutes_sd=5.0,
        human_fallback_servers=0,
        human_fallback_minutes_mean=0.0,
        downtime_day_probability=0.0,
        incomplete_probability=0.03,
        incomplete_rework_minutes=8.0,
        clinician_servers=5,
        clinician_summary_saving_minutes=0.0,
        clinician_review_minutes=0.0,
        false_alert_probability=0.01,
        high_acuity_detection_sensitivity=0.68,
        physical_reset_minutes=0.0,
        robot_or_kiosk=False,
        human_verification=True,
    ),
    "screen": QueueConfig(
        name="Screen kiosk + clinician review",
        arrivals_per_day=35.0,
        days=35,
        warmup_days=5,
        intake_servers=4,
        intake_minutes_mean=14.0,
        intake_minutes_sd=4.0,
        human_fallback_servers=1,
        human_fallback_minutes_mean=20.0,
        downtime_day_probability=0.02,
        incomplete_probability=0.12,
        incomplete_rework_minutes=12.0,
        clinician_servers=5,
        clinician_summary_saving_minutes=5.0,
        clinician_review_minutes=6.0,
        false_alert_probability=0.045,
        high_acuity_detection_sensitivity=0.78,
        physical_reset_minutes=0.0,
        robot_or_kiosk=True,
        human_verification=True,
    ),
    "robot": QueueConfig(
        name="Embodied robot (realistic faults)",
        arrivals_per_day=35.0,
        days=35,
        warmup_days=5,
        intake_servers=2,
        intake_minutes_mean=13.0,
        intake_minutes_sd=4.0,
        human_fallback_servers=1,
        human_fallback_minutes_mean=20.0,
        downtime_day_probability=0.10,
        incomplete_probability=0.08,
        incomplete_rework_minutes=10.0,
        clinician_servers=5,
        clinician_summary_saving_minutes=6.0,
        clinician_review_minutes=7.0,
        false_alert_probability=0.075,
        high_acuity_detection_sensitivity=0.84,
        physical_reset_minutes=3.0,
        robot_or_kiosk=True,
        human_verification=False,
    ),
    "robot_hitl": QueueConfig(
        name="Embodied robot + human safety gate",
        arrivals_per_day=35.0,
        days=35,
        warmup_days=5,
        intake_servers=3,
        intake_minutes_mean=13.0,
        intake_minutes_sd=4.0,
        human_fallback_servers=1,
        human_fallback_minutes_mean=20.0,
        downtime_day_probability=0.07,
        incomplete_probability=0.07,
        incomplete_rework_minutes=10.0,
        clinician_servers=5,
        clinician_summary_saving_minutes=7.0,
        clinician_review_minutes=9.0,
        false_alert_probability=0.070,
        high_acuity_detection_sensitivity=0.89,
        physical_reset_minutes=3.0,
        robot_or_kiosk=True,
        human_verification=True,
    ),
}


class ArrivalDraw(NamedTuple):
    day: int
    arrival: float
    acuity: int
    z_primary_service: float
    z_fallback_service: float
    u_incomplete: float
    u_detection: float
    u_false_alert: float
    u_abandonment: float


def sigmoid(x: float | np.ndarray) -> float | np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def schedule_service(arrival: float, duration: float, availability: list[float]) -> tuple[float, float]:
    available_at = heapq.heappop(availability)
    start = max(arrival, available_at)
    finish = start + duration
    heapq.heappush(availability, finish)
    return start, finish


def generate_random_stream(config: QueueConfig, seed: int) -> tuple[np.ndarray, list[ArrivalDraw]]:
    """Generate shared demand and latent random draws for one replication."""
    rng = np.random.default_rng(seed)
    total_days = config.warmup_days + config.days
    outage_uniforms = rng.random(total_days)
    arrivals: list[ArrivalDraw] = []
    for day in range(total_days):
        n_arrivals = int(rng.poisson(config.arrivals_per_day))
        arrival_times = day * WORKDAY_MIN + np.sort(rng.uniform(0, WORKDAY_MIN, n_arrivals))
        acuities = rng.choice([0, 1, 2], size=n_arrivals, p=[0.60, 0.30, 0.10])
        for arrival, acuity in zip(arrival_times, acuities, strict=True):
            arrivals.append(ArrivalDraw(
                day=day,
                arrival=float(arrival),
                acuity=int(acuity),
                z_primary_service=float(rng.normal()),
                z_fallback_service=float(rng.normal()),
                u_incomplete=float(rng.random()),
                u_detection=float(rng.random()),
                u_false_alert=float(rng.random()),
                u_abandonment=float(rng.random()),
            ))
    return outage_uniforms, arrivals


def simulate_one_from_stream(
    config: QueueConfig,
    outage_uniforms: np.ndarray,
    arrival_stream: list[ArrivalDraw],
) -> Dict[str, float | str]:
    intake_avail = [0.0] * max(config.intake_servers, 1)
    fallback_avail = [0.0] * max(config.human_fallback_servers, 1)
    clinician_avail = [0.0] * config.clinician_servers
    heapq.heapify(intake_avail)
    heapq.heapify(fallback_avail)
    heapq.heapify(clinician_avail)

    waits: List[float] = []
    high_acuity_waits: List[float] = []
    completed = 0
    abandoned = 0
    total_arrivals = 0
    false_alerts = 0
    missed_high_acuity = 0
    high_acuity_total = 0
    failover_cases = 0
    incomplete_cases = 0
    physical_resets = 0
    clinician_minutes_by_day = np.zeros(config.days)
    intake_minutes_by_day = np.zeros(config.days)
    day_outage = outage_uniforms < config.downtime_day_probability

    for draw in arrival_stream:
        observed = draw.day >= config.warmup_days
        observed_day = draw.day - config.warmup_days
        if observed:
            total_arrivals += 1

        high_acuity = draw.acuity == 2
        if high_acuity and observed:
            high_acuity_total += 1

        if config.name == "Manual intake":
            use_fallback = False
        else:
            use_fallback = bool(day_outage[draw.day])

        incomplete = config.robot_or_kiosk and (draw.u_incomplete < config.incomplete_probability)
        if incomplete and observed:
            incomplete_cases += 1

        if use_fallback:
            if observed:
                failover_cases += 1
            intake_duration = max(4.0, config.human_fallback_minutes_mean + 4.0 * draw.z_fallback_service)
            _, intake_finish = schedule_service(draw.arrival, intake_duration, fallback_avail)
            if observed:
                intake_minutes_by_day[observed_day] += intake_duration
        else:
            intake_duration = max(4.0, config.intake_minutes_mean + config.intake_minutes_sd * draw.z_primary_service)
            if config.robot_or_kiosk:
                intake_duration += config.physical_reset_minutes
                if config.physical_reset_minutes > 0 and observed:
                    physical_resets += 1
            _, intake_finish = schedule_service(draw.arrival, intake_duration, intake_avail)
            if observed:
                intake_minutes_by_day[observed_day] += intake_duration

        if incomplete:
            _, intake_finish = schedule_service(intake_finish, config.incomplete_rework_minutes, fallback_avail)
            if observed:
                intake_minutes_by_day[observed_day] += config.incomplete_rework_minutes

        if high_acuity:
            alert = draw.u_detection < config.high_acuity_detection_sensitivity
            if not alert and observed:
                missed_high_acuity += 1
        else:
            alert = draw.u_false_alert < config.false_alert_probability
            if alert and observed:
                false_alerts += 1

        base_clinician = {0: 38.0, 1: 52.0, 2: 72.0}[draw.acuity]
        clinician_duration = max(base_clinician - config.clinician_summary_saving_minutes, 25.0)
        if config.robot_or_kiosk:
            clinician_duration += config.clinician_review_minutes
        if alert:
            clinician_duration += 6.0 if config.human_verification else 10.0

        predicted_start = max(intake_finish, float(clinician_avail[0]))
        predicted_wait = predicted_start - draw.arrival
        abandonment_probability = min(0.25, float(sigmoid(-5.2 + 0.010 * max(predicted_wait - 120.0, 0.0))))
        if draw.u_abandonment < abandonment_probability:
            if observed:
                abandoned += 1
            continue

        clinician_start, _ = schedule_service(intake_finish, clinician_duration, clinician_avail)
        final_wait = clinician_start - draw.arrival
        if observed:
            waits.append(final_wait)
            if high_acuity:
                high_acuity_waits.append(final_wait)
            completed += 1
            clinician_minutes_by_day[observed_day] += clinician_duration

    waits_arr = np.asarray(waits, dtype=float)
    high_arr = np.asarray(high_acuity_waits, dtype=float)
    daily_capacity = config.clinician_servers * WORKDAY_MIN
    overtime = np.maximum(clinician_minutes_by_day - daily_capacity, 0.0)

    return {
        "scenario": config.name,
        "warmup_days": config.warmup_days,
        "observation_days": config.days,
        "arrivals": total_arrivals,
        "completed": completed,
        "abandoned": abandoned,
        "throughput_per_day": completed / config.days,
        "mean_wait_minutes": float(waits_arr.mean()) if waits_arr.size else np.nan,
        "p90_wait_minutes": float(np.quantile(waits_arr, 0.90)) if waits_arr.size else np.nan,
        "mean_high_acuity_wait_minutes": float(high_arr.mean()) if high_arr.size else np.nan,
        "abandonment_percent": abandoned / max(total_arrivals, 1) * 100,
        "false_alerts_per_100_arrivals": false_alerts / max(total_arrivals, 1) * 100,
        "missed_high_acuity_percent": missed_high_acuity / max(high_acuity_total, 1) * 100,
        "failover_percent": failover_cases / max(total_arrivals, 1) * 100,
        "incomplete_rework_percent": incomplete_cases / max(total_arrivals, 1) * 100,
        "mean_clinician_overtime_minutes_per_day": float(overtime.mean()),
        "mean_clinician_utilization_percent": float(clinician_minutes_by_day.mean() / daily_capacity * 100),
        "mean_intake_minutes_per_day": float(intake_minutes_by_day.mean()),
        # This counts routine reset work after each non-fallback embodied intake;
        # it is not a stochastic incident or injury rate. The legacy key is
        # retained for backward compatibility with current output schemas.
        "routine_physical_reset_work_events_per_day": physical_resets / config.days,
        "physical_resets_per_day": physical_resets / config.days,
    }


def simulate_one(config: QueueConfig, seed: int) -> Dict[str, float | str]:
    """Simulate one pathway from a deterministic seed."""
    outage_uniforms, arrival_stream = generate_random_stream(config, seed)
    return simulate_one_from_stream(config, outage_uniforms, arrival_stream)


def run_paired_replications(
    configs: list[QueueConfig],
    replications: int,
    seed: int,
) -> pd.DataFrame:
    """Run multiple pathways on one generated demand stream per replication."""
    if not configs:
        return pd.DataFrame()
    reference = configs[0]
    rows = []
    for replication in range(replications):
        stream_seed = seed + replication * 1009
        outage_uniforms, arrival_stream = generate_random_stream(reference, stream_seed)
        for config in configs:
            if (config.days, config.warmup_days, config.arrivals_per_day) != (
                reference.days, reference.warmup_days, reference.arrivals_per_day
            ):
                raise ValueError("Paired configurations must share horizon and arrival rate")
            row = simulate_one_from_stream(config, outage_uniforms, arrival_stream)
            row["replication"] = replication
            rows.append(row)
    return pd.DataFrame(rows)


def run_replications(config: QueueConfig, replications: int, seed: int) -> pd.DataFrame:
    rows = []
    for replication in range(replications):
        row = simulate_one(config, seed + replication * 1009)
        row["replication"] = replication
        rows.append(row)
    return pd.DataFrame(rows)



def summarize_replications(df: pd.DataFrame) -> pd.DataFrame:
    """Bootstrap scenario means across independent queue replications."""
    excluded = {"scenario", "warmup_days", "observation_days", "replication"}
    metrics = [c for c in df.columns if c not in excluded]
    summary = bootstrap_group_summary(
        df,
        group_column="scenario",
        metrics=metrics,
        label_prefix="service-scenario",
        n_resamples=5_000,
    )
    metadata = (
        df.groupby("scenario", sort=False)[["warmup_days", "observation_days"]]
        .first()
        .reset_index()
    )
    return metadata.merge(summary, on="scenario", how="left")


def summarize_paired_contrasts(replications: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    metrics = {
        "mean_wait_minutes": "Mean wait difference (working minutes)",
        "p90_wait_minutes": "P90 wait difference (working minutes)",
        "throughput_per_day": "Throughput difference (assessments/day)",
        "abandonment_percent": "Abandonment difference (percentage points)",
        "false_alerts_per_100_arrivals": "False-alert difference per 100 arrivals",
        "missed_high_acuity_percent": "Missed high-acuity difference (percentage points)",
        "mean_clinician_utilization_percent": "Clinician-utilization difference (percentage points)",
    }
    screen_name = CONFIGS["screen"].name
    comparators = [CONFIGS["robot"].name, CONFIGS["robot_hitl"].name]
    rows: list[dict[str, float | int | str]] = []
    reference = replications.loc[replications["scenario"] == screen_name].set_index("replication")
    for comparator in comparators:
        left = replications.loc[replications["scenario"] == comparator].set_index("replication")
        for metric, label in metrics.items():
            delta = (left[metric] - reference[metric]).sort_index()
            stats_row = paired_contrast_statistics(delta.to_numpy(), label=f"service:{comparator}:{metric}")
            rows.append({
                "comparator": comparator,
                "reference": screen_name,
                "metric": metric,
                "metric_label": label,
                "outcome_family": "service-primary",
                **stats_row,
            })
    result = add_holm_columns(pd.DataFrame(rows), group_columns=["comparator"])
    result.to_csv(output_dir / "system_contrast_summary.csv", index=False)
    return result


def run_sensitivity(output_dir: Path, replications: int = 30) -> pd.DataFrame:
    """Paired downtime-by-review grid with bootstrap CIs for mean contrasts."""
    downtimes = np.linspace(0.0, 0.30, 6)
    review_times = np.arange(4.0, 25.0, 4.0)
    screen_short = replace(CONFIGS["screen"], days=18)
    streams = [
        generate_random_stream(screen_short, SEED + 20000 + replication * 1009)
        for replication in range(replications)
    ]
    screen_rows = []
    for replication, (outages, arrivals) in enumerate(streams):
        row = simulate_one_from_stream(screen_short, outages, arrivals)
        row["replication"] = replication
        screen_rows.append(row)
    screen_df = pd.DataFrame(screen_rows).set_index("replication")
    rows = []

    for i, downtime in enumerate(downtimes):
        for j, review in enumerate(review_times):
            cfg = replace(
                CONFIGS["robot_hitl"],
                days=18,
                downtime_day_probability=float(downtime),
                clinician_review_minutes=float(review),
            )
            robot_rows = []
            for replication, (outages, arrivals) in enumerate(streams):
                row = simulate_one_from_stream(cfg, outages, arrivals)
                row["replication"] = replication
                robot_rows.append(row)
            robot_df = pd.DataFrame(robot_rows).set_index("replication")
            wait_delta = robot_df["mean_wait_minutes"] - screen_df["mean_wait_minutes"]
            throughput_delta = robot_df["throughput_per_day"] - screen_df["throughput_per_day"]
            wait = bootstrap_mean_ci(
                wait_delta.to_numpy(), n_resamples=3_000,
                seed=f"service-sensitivity-wait:{i}:{j}", method="BCa"
            )
            throughput = bootstrap_mean_ci(
                throughput_delta.to_numpy(), n_resamples=3_000,
                seed=f"service-sensitivity-throughput:{i}:{j}", method="BCa"
            )
            rows.append({
                "robot_downtime": float(downtime),
                "clinician_review_minutes": float(review),
                "robot_mean_wait_minutes": float(robot_df["mean_wait_minutes"].mean()),
                "robot_throughput_per_day": float(robot_df["throughput_per_day"].mean()),
                "wait_difference_vs_screen_minutes": float(wait["mean"]),
                "wait_difference_ci_low": float(wait["bootstrap_ci_low"]),
                "wait_difference_ci_high": float(wait["bootstrap_ci_high"]),
                "wait_difference_p025": float(wait["bootstrap_ci_low"]),
                "wait_difference_p975": float(wait["bootstrap_ci_high"]),
                "throughput_difference_vs_screen_per_day": float(throughput["mean"]),
                "throughput_difference_ci_low": float(throughput["bootstrap_ci_low"]),
                "throughput_difference_ci_high": float(throughput["bootstrap_ci_high"]),
                "throughput_difference_p025": float(throughput["bootstrap_ci_low"]),
                "throughput_difference_p975": float(throughput["bootstrap_ci_high"]),
                "bootstrap_method": str(wait["bootstrap_method"]),
                "bootstrap_resamples": 3_000,
                "replications": replications,
            })
    sensitivity = pd.DataFrame(rows)
    sensitivity.to_csv(output_dir / "system_sensitivity_grid.csv", index=False)
    summarize_break_even(sensitivity, output_dir)
    return sensitivity


def summarize_break_even(sensitivity: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    rows = []
    for downtime, group in sensitivity.groupby("robot_downtime", sort=True):
        group = group.sort_values("clinician_review_minutes")
        mean_faster = group.loc[group["wait_difference_vs_screen_minutes"] <= 0, "clinician_review_minutes"]
        robust_faster = group.loc[group["wait_difference_ci_high"] <= 0, "clinician_review_minutes"]
        rows.append({
            "robot_downtime": float(downtime),
            "maximum_review_minutes_for_mean_wait_noninferiority": float(mean_faster.max()) if not mean_faster.empty else np.nan,
            "maximum_review_minutes_for_bootstrap_ci_wait_noninferiority": float(robust_faster.max()) if not robust_faster.empty else np.nan,
            "maximum_review_minutes_for_robust_wait_noninferiority": float(robust_faster.max()) if not robust_faster.empty else np.nan,
        })
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "system_break_even_summary.csv", index=False)
    return result


def run_warmup_diagnostic(output_dir: Path, replications: int = 40) -> pd.DataFrame:
    rows = []
    for warmup in [0, 2, 5, 10]:
        screen_cfg = replace(CONFIGS["screen"], warmup_days=warmup)
        gate_cfg = replace(CONFIGS["robot_hitl"], warmup_days=warmup)
        paired = run_paired_replications(
            [screen_cfg, gate_cfg], replications=replications, seed=SEED + 90000
        )
        for scenario, df in paired.groupby("scenario", sort=False):
            result = bootstrap_mean_ci(
                df["mean_wait_minutes"].to_numpy(),
                n_resamples=5_000,
                seed=f"warmup:{scenario}:{warmup}",
                method="BCa",
            )
            rows.append({
                "scenario": scenario,
                "warmup_days": warmup,
                "mean_wait_minutes": float(result["mean"]),
                "bootstrap_ci_low_wait_minutes": float(result["bootstrap_ci_low"]),
                "bootstrap_ci_high_wait_minutes": float(result["bootstrap_ci_high"]),
                "p025_wait_minutes": float(result["bootstrap_ci_low"]),
                "p975_wait_minutes": float(result["bootstrap_ci_high"]),
                "bootstrap_method": str(result["bootstrap_method"]),
                "bootstrap_resamples": 5_000,
                "replications": replications,
            })
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "system_warmup_diagnostic.csv", index=False)
    return result


def _metric_arrays(summary: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = summary[f"{metric}_mean"].to_numpy(dtype=float)
    low = summary[f"{metric}_ci_low"].to_numpy(dtype=float)
    high = summary[f"{metric}_ci_high"].to_numpy(dtype=float)
    return means, means - low, high - means


def create_figures(
    replications: pd.DataFrame,
    summary: pd.DataFrame,
    contrasts: pd.DataFrame,
    sensitivity: pd.DataFrame,
    warmup: pd.DataFrame,
    figure_dir: Path,
) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    order = [CONFIGS[k].name for k in ["manual", "screen", "robot", "robot_hitl"]]
    labels = ["Manual", "Screen", "Robot", "Robot +\nhuman gate"]
    endpoint = summary.set_index("scenario").loc[order].reset_index()

    data = [replications.loc[replications["scenario"] == s, "mean_wait_minutes"].values for s in order]
    fig, ax = plt.subplots(figsize=(8.7, 5.3))
    ax.boxplot(data, tick_labels=labels, showfliers=False)
    means, lower, upper = _metric_arrays(endpoint, "mean_wait_minutes")
    ax.errorbar(np.arange(1, len(order) + 1), means, yerr=np.vstack([lower, upper]), fmt="D", linestyle="none", label="Mean and 95% bootstrap CI")
    ax.set_ylabel("Mean wait per replication (working minutes)")
    ax.set_title("Outpatient waiting-time distributions and mean uncertainty")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "system_wait_boxplot")

    x = np.arange(len(order))
    means, lower, upper = _metric_arrays(endpoint, "throughput_per_day")
    fig, ax = plt.subplots(figsize=(8.7, 5.2))
    ax.bar(x, means, yerr=np.vstack([lower, upper]), capsize=3)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Completed assessments per day")
    ax.set_title("Service throughput with 95% bootstrap CIs")
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "system_throughput")

    pivot = sensitivity.pivot(index="robot_downtime", columns="clinician_review_minutes", values="wait_difference_vs_screen_minutes")
    robust = sensitivity.pivot(index="robot_downtime", columns="clinician_review_minutes", values="wait_difference_ci_high") <= 0
    fig, ax = plt.subplots(figsize=(8.3, 5.4))
    x_edges = np.arange(len(pivot.columns) + 1)
    y_edges = np.arange(len(pivot.index) + 1)
    mesh = ax.pcolormesh(x_edges, y_edges, pivot.values, shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, label="Robot minus screen mean wait (minutes)")
    cbar.solids.set_rasterized(False)
    yy, xx = np.where(robust.to_numpy())
    if len(xx):
        ax.scatter(xx + 0.5, yy + 0.5, marker="o", facecolors="none", edgecolors="black", label="Upper 95% CI <= 0")
        ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(np.arange(len(pivot.columns)) + 0.5, [f"{v:.0f}" for v in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)) + 0.5, [f"{v:.0%}" for v in pivot.index])
    ax.set_xlim(0, len(pivot.columns))
    ax.set_ylim(0, len(pivot.index))
    ax.set_xlabel("Clinician review minutes per robot intake")
    ax.set_ylabel("Robot day-level downtime")
    ax.set_title("Wait sensitivity and bootstrap-supported noninferiority")
    fig.tight_layout()
    save_figure(fig, figure_dir, "system_sensitivity_heatmap")

    safety_metrics = [
        ("false_alerts_per_100_arrivals", "False alerts per 100 arrivals"),
        ("missed_high_acuity_percent", "Missed high-acuity cases (%)"),
        ("abandonment_percent", "Abandonment (%)"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.4), constrained_layout=True)
    for ax, (metric, title) in zip(axes, safety_metrics, strict=True):
        means, lower, upper = _metric_arrays(endpoint, metric)
        ax.bar(x, means, yerr=np.vstack([lower, upper]), capsize=3)
        ax.set_xticks(x, ["Manual", "Screen", "Robot", "Robot +\ngate"], rotation=20, ha="right")
        ax.set_title(title, fontsize=10.5)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Service safety and access outcomes (95% bootstrap CIs)")
    save_figure(fig, figure_dir, "system_safety_access")

    subset = contrasts[contrasts["metric"].isin(["mean_wait_minutes", "throughput_per_day"])].copy()
    subset["display"] = subset["comparator"].replace({
        CONFIGS["robot"].name: "Robot",
        CONFIGS["robot_hitl"].name: "Robot + human gate",
    }) + " - " + subset["metric"].replace({
        "mean_wait_minutes": "mean wait",
        "throughput_per_day": "throughput",
    })
    subset = subset.reset_index(drop=True)
    y = np.arange(len(subset))
    means = subset["mean_difference"].to_numpy()
    lower = means - subset["bootstrap_ci_low"].to_numpy()
    upper = subset["bootstrap_ci_high"].to_numpy() - means
    fig, ax = plt.subplots(figsize=(8.7, 4.9))
    ax.errorbar(means, y, xerr=np.vstack([lower, upper]), fmt="o", capsize=4, linestyle="none")
    ax.axvline(0, linewidth=1, linestyle="--")
    ax.set_yticks(y, subset["display"])
    ax.set_xlabel("Paired difference versus screen (native metric units)")
    ax.set_title("Paired service mean contrasts with 95% BCa bootstrap CIs")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "system_contrast_intervals")

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    for scenario, group in warmup.groupby("scenario", sort=False):
        group = group.sort_values("warmup_days")
        means = group["mean_wait_minutes"].to_numpy()
        low = group["bootstrap_ci_low_wait_minutes"].to_numpy()
        high = group["bootstrap_ci_high_wait_minutes"].to_numpy()
        ax.errorbar(group["warmup_days"], means, yerr=np.vstack([means-low, high-means]), marker="o", capsize=3, label=scenario)
    ax.set_xlabel("Warm-up days")
    ax.set_ylabel("Mean wait (working minutes)")
    ax.set_title("Warm-up diagnostic with 95% bootstrap CIs")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "system_warmup_diagnostic")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    output_dir = root / "results"
    figure_dir = root / "figures"
    output_dir.mkdir(exist_ok=True)
    figure_dir.mkdir(exist_ok=True)

    replications = run_paired_replications(
        [CONFIGS[key] for key in ["manual", "screen", "robot", "robot_hitl"]],
        replications=200,
        seed=SEED + 5000,
    )
    print("  base replications complete", flush=True)
    summary = summarize_replications(replications)
    contrasts = summarize_paired_contrasts(replications, output_dir)
    print("  paired bootstrap contrast summary complete", flush=True)
    sensitivity = run_sensitivity(output_dir)
    print("  sensitivity grid complete", flush=True)
    warmup = run_warmup_diagnostic(output_dir)
    print("  warm-up diagnostic complete", flush=True)

    replications.to_csv(output_dir / "system_replication_results.csv", index=False)
    summary.to_csv(output_dir / "system_scenario_summary.csv", index=False)
    with open(output_dir / "system_model_parameters.json", "w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in CONFIGS.items()}, f, indent=2)

    create_figures(replications, summary, contrasts, sensitivity, warmup, figure_dir)
    print("  figure export complete", flush=True)
    cols = [
        "scenario",
        "mean_wait_minutes_mean", "mean_wait_minutes_ci_low", "mean_wait_minutes_ci_high",
        "throughput_per_day_mean", "throughput_per_day_ci_low", "throughput_per_day_ci_high",
    ]
    print(summary[cols].to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
