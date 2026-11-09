"""Neutral and skeptical assumption scenarios for manuscript v4.3.

The scenarios are deliberately transparent stress tests rather than calibrated
probability distributions. Neutral removes any assumed embodiment-specific
symptom or engagement advantage while retaining the operational consequences
of a physical pathway. Skeptical combines the adverse ends of the declared
plausible ranges. Both are compared with the fixed content-matched screen using
paired synthetic cohorts or paired service-demand streams.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json

import numpy as np
import pandas as pd

from individual_microsimulation import ARM_CONFIGS, simulate_arm, summarize as summarize_individual
from service_queue_simulation import CONFIGS, generate_random_stream, simulate_one_from_stream
from stats_utils import bootstrap_mean_ci

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs" / "assumption_scenarios_v4_3"
SEED = 20260730


def individual_configs():
    screen = ARM_CONFIGS["screen_agent"]
    neutral = replace(
        ARM_CONFIGS["robot_hitl"],
        name="Human-gated robot - neutral assumptions",
        engagement_intercept=screen.engagement_intercept,
        content_effect=screen.content_effect,
        embodiment_effect=0.0,
        weekly_decay=screen.weekly_decay,
        downtime=0.05,
        initial_refusal=0.05,
        privacy_penalty=screen.privacy_penalty,
        discomfort_dropout=0.005,
        crisis_sensitivity=0.82,
        false_alert_probability=0.030,
        review_minutes_per_alert=9.0,
        routine_audit_minutes=4.0,
        physical_near_miss_per_active_week=0.0006,
        human_verification=True,
        fallback_screen_probability=0.60,
    )
    skeptical = replace(
        ARM_CONFIGS["robot_hitl"],
        name="Human-gated robot - skeptical assumptions",
        engagement_intercept=screen.engagement_intercept - 0.10,
        content_effect=screen.content_effect,
        embodiment_effect=0.0,
        weekly_decay=0.035,
        downtime=0.20,
        initial_refusal=0.15,
        privacy_penalty=0.55,
        discomfort_dropout=0.020,
        crisis_sensitivity=0.78,
        false_alert_probability=0.060,
        review_minutes_per_alert=12.0,
        routine_audit_minutes=6.0,
        physical_near_miss_per_active_week=0.0012,
        human_verification=True,
        fallback_screen_probability=0.30,
    )
    return screen, neutral, skeptical


def service_configs():
    screen = CONFIGS["screen"]
    neutral = replace(
        CONFIGS["robot_hitl"],
        name="Human-gated robot - neutral assumptions",
        intake_servers=4,
        intake_minutes_mean=14.0,
        intake_minutes_sd=4.0,
        downtime_day_probability=0.02,
        incomplete_probability=0.12,
        incomplete_rework_minutes=12.0,
        clinician_summary_saving_minutes=5.0,
        clinician_review_minutes=6.0,
        false_alert_probability=0.045,
        high_acuity_detection_sensitivity=0.78,
        physical_reset_minutes=1.0,
        human_verification=True,
    )
    skeptical = replace(
        CONFIGS["robot_hitl"],
        name="Human-gated robot - skeptical assumptions",
        intake_servers=2,
        intake_minutes_mean=16.0,
        intake_minutes_sd=5.0,
        downtime_day_probability=0.15,
        incomplete_probability=0.15,
        incomplete_rework_minutes=15.0,
        clinician_summary_saving_minutes=3.0,
        clinician_review_minutes=12.0,
        false_alert_probability=0.10,
        high_acuity_detection_sensitivity=0.80,
        physical_reset_minutes=5.0,
        human_verification=True,
    )
    return screen, neutral, skeptical


def summarize_differences(values: np.ndarray, label: str) -> dict[str, float | str | int]:
    result = bootstrap_mean_ci(values, n_resamples=10_000, seed=label, method="BCa")
    return {
        "mean_difference": float(result["mean"]),
        "bootstrap_ci_low": float(result["bootstrap_ci_low"]),
        "bootstrap_ci_high": float(result["bootstrap_ci_high"]),
        "replications": int(len(values)),
    }


def run_individual(replications: int = 200, n_per_arm: int = 1200) -> tuple[pd.DataFrame, pd.DataFrame]:
    screen, neutral, skeptical = individual_configs()
    configs = [screen, neutral, skeptical]
    raw = []
    for r in range(replications):
        cohort_seed = SEED + 1_000_000 + r * 1009
        for j, cfg in enumerate(configs):
            patient, _ = simulate_arm(
                cfg, n=n_per_arm, weeks=12, seed=cohort_seed,
                cohort_seed=cohort_seed, event_seed=cohort_seed + 100_003 + j * 97,
            )
            row = summarize_individual(patient); row["replication"] = r; raw.append(row)
    raw_df = pd.DataFrame(raw)
    metrics = {
        "response_percent": "Response difference (percentage points)",
        "remission_percent": "Remission difference (percentage points)",
        "completion_percent": "Completion difference (percentage points)",
        "mean_phq9_change": "Mean PHQ-9 change difference",
        "mean_clinician_review_minutes": "Review-time difference (minutes/participant)",
        "missed_crises_per_100_crisis_weeks": "Missed crisis-weeks difference per 100 crisis-weeks",
        "physical_near_misses_per_100": "Physical near-miss difference per 100 participants",
    }
    ref = raw_df[raw_df.arm == screen.name].set_index("replication")
    rows = []
    for cfg in [neutral, skeptical]:
        cur = raw_df[raw_df.arm == cfg.name].set_index("replication")
        for metric, outcome in metrics.items():
            delta = (cur[metric] - ref[metric]).to_numpy()
            rows.append({"scale": "Patient", "scenario": cfg.name, "metric": metric, "outcome": outcome, **summarize_differences(delta, f"v43:{cfg.name}:{metric}")})
    return raw_df, pd.DataFrame(rows)


def run_service(replications: int = 200) -> tuple[pd.DataFrame, pd.DataFrame]:
    screen, neutral, skeptical = service_configs()
    configs = [screen, neutral, skeptical]
    raw = []
    for r in range(replications):
        seed = SEED + 2_000_000 + r * 1009
        outages, arrivals = generate_random_stream(screen, seed)
        for cfg in configs:
            row = simulate_one_from_stream(cfg, outages, arrivals); row["replication"] = r; raw.append(row)
    raw_df = pd.DataFrame(raw)
    metrics = {
        "mean_wait_minutes": "Mean wait difference (working minutes)",
        "p90_wait_minutes": "P90 wait difference (working minutes)",
        "throughput_per_day": "Throughput difference (assessments/day)",
        "abandonment_percent": "Abandonment difference (percentage points)",
        "false_alerts_per_100_arrivals": "False-alert difference per 100 arrivals",
        "missed_high_acuity_percent": "Missed high-acuity difference (percentage points)",
        "mean_clinician_utilization_percent": "Clinician-utilization difference (percentage points)",
    }
    ref = raw_df[raw_df.scenario == screen.name].set_index("replication")
    rows = []
    for cfg in [neutral, skeptical]:
        cur = raw_df[raw_df.scenario == cfg.name].set_index("replication")
        for metric, outcome in metrics.items():
            delta = (cur[metric] - ref[metric]).to_numpy()
            rows.append({"scale": "Service", "scenario": cfg.name, "metric": metric, "outcome": outcome, **summarize_differences(delta, f"v43:{cfg.name}:{metric}")})
    return raw_df, pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    iraw, isum = run_individual()
    sraw, ssum = run_service()
    iraw.to_csv(OUT / "individual_scenario_replications.csv", index=False)
    sraw.to_csv(OUT / "service_scenario_replications.csv", index=False)
    summary = pd.concat([isum, ssum], ignore_index=True)
    summary.to_csv(OUT / "neutral_skeptical_contrast_summary.csv", index=False)
    parameter_sets = {
        "individual": {cfg.name: cfg.__dict__ for cfg in individual_configs()},
        "service": {cfg.name: cfg.__dict__ for cfg in service_configs()},
        "interpretation": "Neutral and skeptical stress tests; not empirically calibrated probability distributions.",
    }
    (OUT / "scenario_parameter_sets.json").write_text(json.dumps(parameter_sets, indent=2), encoding="utf-8")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
