"""Synthetic individual-level microsimulation for physical AI in psychiatry.

This model is an assumption-driven research sandbox. It does not estimate the
clinical efficacy or safety of any product and must not be used for patient care.

The experiment compares usual measurement-based care, a screen-based digital
agent, an embodied social robot delivering functionally matched content, and an
embodied robot with mandatory human review for risk-relevant alerts.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Dict, Tuple
import json
import gc
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from figure_utils import save_figure
from stats_utils import (
    BOOTSTRAP_RESAMPLES,
    bootstrap_group_summary,
    bootstrap_mean_ci,
    paired_contrast_statistics,
    add_holm_columns,
)

SEED = 20260726


@dataclass(frozen=True)
class ArmConfig:
    name: str
    engagement_intercept: float
    content_effect: float
    embodiment_effect: float
    weekly_decay: float
    downtime: float
    initial_refusal: float
    privacy_penalty: float
    discomfort_dropout: float
    crisis_sensitivity: float
    false_alert_probability: float
    review_minutes_per_alert: float
    routine_audit_minutes: float
    physical_near_miss_per_active_week: float
    human_verification: bool
    fallback_screen_probability: float = 0.0


ARM_CONFIGS: Dict[str, ArmConfig] = {
    "usual_care": ArmConfig(
        name="Usual measurement-based care",
        engagement_intercept=-0.05,
        content_effect=0.00,
        embodiment_effect=0.00,
        weekly_decay=0.035,
        downtime=0.00,
        initial_refusal=0.00,
        privacy_penalty=0.10,
        discomfort_dropout=0.00,
        crisis_sensitivity=0.55,
        false_alert_probability=0.010,
        review_minutes_per_alert=8.0,
        routine_audit_minutes=0.0,
        physical_near_miss_per_active_week=0.0,
        human_verification=True,
    ),
    "screen_agent": ArmConfig(
        name="Screen-based agent",
        engagement_intercept=0.42,
        content_effect=0.32,
        embodiment_effect=0.00,
        weekly_decay=0.025,
        downtime=0.025,
        initial_refusal=0.025,
        privacy_penalty=0.25,
        discomfort_dropout=0.00,
        crisis_sensitivity=0.76,
        false_alert_probability=0.018,
        review_minutes_per_alert=6.0,
        routine_audit_minutes=1.0,
        physical_near_miss_per_active_week=0.0,
        human_verification=True,
        fallback_screen_probability=0.0,
    ),
    "embodied_robot": ArmConfig(
        name="Embodied social robot",
        engagement_intercept=0.63,
        content_effect=0.32,
        embodiment_effect=0.080,
        weekly_decay=0.018,
        downtime=0.10,
        initial_refusal=0.080,
        privacy_penalty=0.42,
        discomfort_dropout=0.008,
        crisis_sensitivity=0.84,
        false_alert_probability=0.030,
        review_minutes_per_alert=7.0,
        routine_audit_minutes=2.0,
        physical_near_miss_per_active_week=0.0007,
        human_verification=False,
        fallback_screen_probability=0.15,
    ),
    "robot_hitl": ArmConfig(
        name="Embodied robot + human safety gate",
        engagement_intercept=0.68,
        content_effect=0.32,
        embodiment_effect=0.080,
        weekly_decay=0.016,
        downtime=0.10,
        initial_refusal=0.065,
        privacy_penalty=0.34,
        discomfort_dropout=0.005,
        crisis_sensitivity=0.86,
        false_alert_probability=0.028,
        review_minutes_per_alert=9.0,
        routine_audit_minutes=4.0,
        physical_near_miss_per_active_week=0.0006,
        human_verification=True,
        fallback_screen_probability=0.60,
    ),
}


def sigmoid(x: np.ndarray | float) -> np.ndarray | float:
    return 1.0 / (1.0 + np.exp(-x))


def _clip_normal(rng: np.random.Generator, mean: float, sd: float, low: float, high: float, n: int) -> np.ndarray:
    x = rng.normal(mean, sd, n)
    return np.clip(x, low, high)


def simulate_arm(
    config: ArmConfig,
    n: int = 5000,
    weeks: int = 12,
    seed: int = SEED,
    engagement_intercept_override: float | None = None,
    downtime_override: float | None = None,
    cohort_seed: int | None = None,
    event_seed: int | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Run one arm and return patient-level and weekly aggregate outputs.

    The synthetic cohort and arm-specific event process use separate random
    streams. Reusing ``cohort_seed`` across arms implements common random
    numbers for baseline covariates, reducing Monte Carlo noise in contrasts
    without implying that the simulated values are empirical estimates.
    """
    arm_hash = sum(ord(c) for c in config.name)
    cohort_rng = np.random.default_rng(seed if cohort_seed is None else cohort_seed)
    rng = np.random.default_rng(seed + arm_hash if event_seed is None else event_seed)

    intercept = config.engagement_intercept if engagement_intercept_override is None else engagement_intercept_override
    downtime = config.downtime if downtime_override is None else downtime_override

    baseline = _clip_normal(cohort_rng, 15.5, 3.2, 10.0, 24.0, n)
    phq = baseline.copy()
    previous_phq = phq.copy()
    tech_acceptance = cohort_rng.beta(2.4, 1.9, n)
    privacy_concern = cohort_rng.beta(2.1, 2.4, n)
    social_support = cohort_rng.normal(0, 1, n)
    treatment_responsiveness = cohort_rng.normal(0, 0.13, n)

    refused = rng.random(n) < config.initial_refusal
    active = ~refused
    dropped = refused.copy()
    prior_engagement = np.zeros(n)
    trust = np.where(config.human_verification, 0.08, 0.0) + 0.12 * tech_acceptance - 0.10 * privacy_concern

    engaged_sessions = np.zeros(n, dtype=int)
    alerts = np.zeros(n, dtype=int)
    false_alerts = np.zeros(n, dtype=int)
    confirmed_false_escalations = np.zeros(n, dtype=int)
    crises = np.zeros(n, dtype=int)
    missed_crises = np.zeros(n, dtype=int)
    review_minutes = np.full(n, config.routine_audit_minutes)
    near_misses = np.zeros(n, dtype=int)
    downtime_sessions = np.zeros(n, dtype=int)
    fallback_sessions = np.zeros(n, dtype=int)
    dropout_week = np.full(n, np.nan)

    weekly_rows = [{
        "arm": config.name,
        "week": 0,
        "mean_phq9_locf": float(phq.mean()),
        "engagement_rate_active": 0.0,
        "active_fraction": float(active.mean()),
        "cumulative_alerts_per_100": 0.0,
    }]

    for week in range(1, weeks + 1):
        idx = np.where(active)[0]
        if idx.size == 0:
            break

        # Availability: a down robot can sometimes fall back to the matched screen interface.
        system_down = rng.random(idx.size) < downtime
        fallback = system_down & (rng.random(idx.size) < config.fallback_screen_probability)
        available = (~system_down) | fallback
        downtime_sessions[idx[system_down]] += 1
        fallback_sessions[idx[fallback]] += 1

        # Dynamic engagement: acceptance, privacy concern, symptom burden, trust,
        # prior use, and gradual novelty decay all contribute.
        logits = (
            intercept
            + 1.05 * (tech_acceptance[idx] - 0.5)
            - config.privacy_penalty * (privacy_concern[idx] - 0.5)
            + 0.34 * prior_engagement[idx]
            + 0.13 * social_support[idx]
            + trust[idx]
            - config.weekly_decay * (week - 1)
            - 0.025 * np.maximum(phq[idx] - 15.0, 0)
        )
        engagement_probability = sigmoid(logits)
        engaged_local = (rng.random(idx.size) < engagement_probability) & available
        engaged = np.zeros(n, dtype=bool)
        engaged[idx] = engaged_local
        engaged_sessions[engaged] += 1

        # Symptom evolution. All arms receive usual clinical care and regression-to-mean;
        # agent effects are incremental and intentionally modest.
        base_weekly_improvement = 0.24 + 0.022 * np.maximum(baseline - 14.0, 0)
        dose_effect = engaged.astype(float) * (config.content_effect + config.embodiment_effect)
        # Fallback sessions preserve the content effect but not the embodiment increment.
        fallback_global = np.zeros(n, dtype=bool)
        fallback_global[idx] = fallback
        dose_effect[fallback_global & engaged] -= config.embodiment_effect
        symptom_noise = rng.normal(0, 0.62, n)
        change = -(base_weekly_improvement + dose_effect + treatment_responsiveness) + symptom_noise
        # Nonparticipants do not receive agent dose, but continue usual care; after dropout use LOCF.
        phq[active] = np.clip(phq[active] + change[active], 0.0, 27.0)

        # Rare, synthetic high-risk episodes become more likely with high/worsening symptoms.
        worsening = phq - previous_phq
        crisis_probability = sigmoid(-10.2 + 0.27 * phq + 0.42 * np.maximum(worsening, 0))
        crisis = active & (rng.random(n) < crisis_probability)
        crises[crisis] += 1

        alert_probability = np.where(crisis, config.crisis_sensitivity, config.false_alert_probability)
        alert = active & (rng.random(n) < alert_probability)
        alerts[alert] += 1
        false = alert & (~crisis)
        false_alerts[false] += 1
        missed_crises[crisis & (~alert)] += 1

        # Human verification suppresses unnecessary escalations but consumes review time.
        if config.human_verification:
            confirmed_false = false & (rng.random(n) < 0.12)
        else:
            confirmed_false = false & (rng.random(n) < 0.72)
        confirmed_false_escalations[confirmed_false] += 1
        review_minutes[alert] += config.review_minutes_per_alert

        # Trust is updated by reliability and transparency. Missed crises and false escalations
        # reduce later engagement; verified benign alerts have a smaller effect.
        trust += np.where(alert & crisis, 0.025, 0.0)
        trust -= np.where(confirmed_false, 0.040, 0.0)
        trust -= np.where(crisis & (~alert), 0.075, 0.0)
        trust = np.clip(trust, -0.5, 0.5)

        # Physical near-misses are only possible in embodied arms and are counted even
        # when they cause no clinical injury.
        if config.physical_near_miss_per_active_week > 0:
            robot_active = np.zeros(n, dtype=bool)
            robot_active[idx] = available & (~fallback)
            near = robot_active & (rng.random(n) < config.physical_near_miss_per_active_week)
            near_misses[near] += 1

        # Dropout is higher after nonengagement, privacy friction, discomfort, and worsening.
        dropout_probability = (
            0.010
            + 0.030 * (~engaged).astype(float)
            + 0.016 * privacy_concern
            + config.discomfort_dropout
            + 0.010 * (worsening > 1.5)
            - 0.008 * engaged.astype(float)
        )
        dropout_probability = np.clip(dropout_probability, 0.002, 0.12)
        new_dropout = active & (rng.random(n) < dropout_probability)
        dropout_week[new_dropout] = week
        active[new_dropout] = False
        dropped |= new_dropout

        prior_engagement = engaged.astype(float)
        previous_phq = phq.copy()

        weekly_rows.append({
            "arm": config.name,
            "week": week,
            "mean_phq9_locf": float(phq.mean()),
            "engagement_rate_active": float(engaged.sum() / max(idx.size, 1)),
            "active_fraction": float(active.mean()),
            "cumulative_alerts_per_100": float(alerts.sum() / n * 100),
        })

    patient = pd.DataFrame({
        "arm": config.name,
        "baseline_phq9": baseline,
        "week12_phq9_locf": phq,
        "phq9_change": phq - baseline,
        "response_50pct": (baseline - phq) >= (0.50 * baseline),
        "remission_phq9_le_4": phq <= 4,
        "completed_12_weeks": ~dropped,
        "initial_refusal": refused,
        "dropout_week": dropout_week,
        "engaged_sessions": engaged_sessions,
        "alerts": alerts,
        "false_alerts": false_alerts,
        "confirmed_false_escalations": confirmed_false_escalations,
        "crisis_weeks": crises,
        "missed_crises": missed_crises,
        "clinician_review_minutes": review_minutes,
        "physical_near_misses": near_misses,
        "downtime_sessions": downtime_sessions,
        "fallback_sessions": fallback_sessions,
    })
    weekly = pd.DataFrame(weekly_rows)
    return patient, weekly


def summarize(patient: pd.DataFrame) -> Dict[str, float | str]:
    n = len(patient)
    crisis_total = int(patient["crisis_weeks"].sum())
    return {
        "arm": str(patient["arm"].iloc[0]),
        "n": n,
        "mean_baseline_phq9": patient["baseline_phq9"].mean(),
        "mean_week12_phq9_locf": patient["week12_phq9_locf"].mean(),
        "mean_phq9_change": patient["phq9_change"].mean(),
        "response_percent": patient["response_50pct"].mean() * 100,
        "remission_percent": patient["remission_phq9_le_4"].mean() * 100,
        "completion_percent": patient["completed_12_weeks"].mean() * 100,
        "initial_refusal_percent": patient["initial_refusal"].mean() * 100,
        "mean_engaged_sessions": patient["engaged_sessions"].mean(),
        "raw_alerts_per_100": patient["alerts"].sum() / n * 100,
        "false_alerts_per_100": patient["false_alerts"].sum() / n * 100,
        "confirmed_false_escalations_per_100": patient["confirmed_false_escalations"].sum() / n * 100,
        "crisis_weeks_per_100": crisis_total / n * 100,
        "missed_crises_per_100_crisis_weeks": (patient["missed_crises"].sum() / crisis_total * 100) if crisis_total else 0.0,
        "mean_clinician_review_minutes": patient["clinician_review_minutes"].mean(),
        "physical_near_misses_per_100": patient["physical_near_misses"].sum() / n * 100,
        "mean_downtime_sessions": patient["downtime_sessions"].mean(),
    }




def run_sensitivity(
    output_dir: Path,
    base_seed: int = SEED + 9000,
    replications: int = 20,
    n_per_arm: int = 600,
) -> pd.DataFrame:
    """Two-way sensitivity analysis with replicated, paired cells.

    Each cell reuses a synthetic baseline cohort between the screen and robot
    arms. BCa bootstrap CIs resample replication-level paired contrasts.
    """
    engagement_advantages = np.linspace(0.00, 0.35, 8)
    downtimes = np.linspace(0.00, 0.30, 7)
    rows = []
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_cfg = ARM_CONFIGS["robot_hitl"]

    for i, adv in enumerate(engagement_advantages):
        for j, downtime in enumerate(downtimes):
            response_deltas: list[float] = []
            change_deltas: list[float] = []
            completion_deltas: list[float] = []
            for replication in range(replications):
                cohort_seed = base_seed + i * 100_000 + j * 10_000 + replication * 101
                screen, _ = simulate_arm(
                    screen_cfg,
                    n=n_per_arm,
                    weeks=12,
                    seed=cohort_seed,
                    cohort_seed=cohort_seed,
                    event_seed=cohort_seed + 1_000_003,
                )
                robot, _ = simulate_arm(
                    robot_cfg,
                    n=n_per_arm,
                    weeks=12,
                    seed=cohort_seed,
                    cohort_seed=cohort_seed,
                    event_seed=cohort_seed + 2_000_003,
                    engagement_intercept_override=screen_cfg.engagement_intercept + adv,
                    downtime_override=float(downtime),
                )
                response_deltas.append((robot["response_50pct"].mean() - screen["response_50pct"].mean()) * 100)
                change_deltas.append(robot["phq9_change"].mean() - screen["phq9_change"].mean())
                completion_deltas.append((robot["completed_12_weeks"].mean() - screen["completed_12_weeks"].mean()) * 100)

            response = bootstrap_mean_ci(
                response_deltas, n_resamples=3_000,
                seed=f"individual-sensitivity-response:{i}:{j}", method="BCa"
            )
            change = bootstrap_mean_ci(
                change_deltas, n_resamples=3_000,
                seed=f"individual-sensitivity-change:{i}:{j}", method="BCa"
            )
            completion = bootstrap_mean_ci(
                completion_deltas, n_resamples=3_000,
                seed=f"individual-sensitivity-completion:{i}:{j}", method="BCa"
            )
            rows.append({
                "engagement_logit_advantage": float(adv),
                "robot_downtime": float(downtime),
                "response_difference_percentage_points": float(response["mean"]),
                "response_difference_ci_low": float(response["bootstrap_ci_low"]),
                "response_difference_ci_high": float(response["bootstrap_ci_high"]),
                "response_difference_p025": float(response["bootstrap_ci_low"]),
                "response_difference_p975": float(response["bootstrap_ci_high"]),
                "mean_change_difference_phq9": float(change["mean"]),
                "mean_change_difference_ci_low": float(change["bootstrap_ci_low"]),
                "mean_change_difference_ci_high": float(change["bootstrap_ci_high"]),
                "mean_change_difference_p025": float(change["bootstrap_ci_low"]),
                "mean_change_difference_p975": float(change["bootstrap_ci_high"]),
                "completion_difference_percentage_points": float(completion["mean"]),
                "completion_difference_ci_low": float(completion["bootstrap_ci_low"]),
                "completion_difference_ci_high": float(completion["bootstrap_ci_high"]),
                "completion_difference_p025": float(completion["bootstrap_ci_low"]),
                "completion_difference_p975": float(completion["bootstrap_ci_high"]),
                "bootstrap_method": str(response["bootstrap_method"]),
                "bootstrap_resamples": 3_000,
                "replications": replications,
                "n_per_arm_per_replication": n_per_arm,
            })
    sensitivity = pd.DataFrame(rows)
    sensitivity.to_csv(output_dir / "individual_sensitivity_grid.csv", index=False)
    summarize_break_even(sensitivity, output_dir)
    return sensitivity


def summarize_break_even(sensitivity: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Report mean and bootstrap-robust break-even thresholds by downtime."""
    rows = []
    for downtime, group in sensitivity.groupby("robot_downtime", sort=True):
        group = group.sort_values("engagement_logit_advantage")
        mean_positive = group.loc[group["response_difference_percentage_points"] > 0, "engagement_logit_advantage"]
        robust_positive = group.loc[group["response_difference_ci_low"] > 0, "engagement_logit_advantage"]
        completion_positive = group.loc[group["completion_difference_percentage_points"] > 0, "engagement_logit_advantage"]
        rows.append({
            "robot_downtime": float(downtime),
            "minimum_engagement_advantage_for_mean_response_gain": float(mean_positive.min()) if not mean_positive.empty else np.nan,
            "minimum_engagement_advantage_for_bootstrap_ci_response_gain": float(robust_positive.min()) if not robust_positive.empty else np.nan,
            "minimum_engagement_advantage_for_robust_response_gain": float(robust_positive.min()) if not robust_positive.empty else np.nan,
            "minimum_engagement_advantage_for_mean_completion_gain": float(completion_positive.min()) if not completion_positive.empty else np.nan,
        })
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "individual_break_even_summary.csv", index=False)
    return result


def run_parameter_uncertainty(
    output_dir: Path,
    draws: int = 250,
    n_per_arm: int = 700,
    base_seed: int = SEED + 70000,
) -> pd.DataFrame:
    """Illustrative second-order uncertainty analysis across broad input ranges.

    The distributions are deliberately scenario-based rather than empirical.
    Their purpose is to identify which assumptions control the sign of the
    findings, not to assign posterior probabilities to clinical effects.
    """
    rng = np.random.default_rng(base_seed)
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_base = ARM_CONFIGS["robot_hitl"]
    rows = []

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
        cohort_seed = base_seed + draw * 1031
        screen, _ = simulate_arm(
            screen_cfg,
            n=n_per_arm,
            weeks=12,
            seed=cohort_seed,
            cohort_seed=cohort_seed,
            event_seed=cohort_seed + 1_000_003,
        )
        robot, _ = simulate_arm(
            robot_cfg,
            n=n_per_arm,
            weeks=12,
            seed=cohort_seed,
            cohort_seed=cohort_seed,
            event_seed=cohort_seed + 2_000_003,
        )
        rows.append({
            "draw": draw,
            "engagement_logit_advantage": advantage,
            "robot_downtime": downtime,
            "embodiment_effect_phq9_per_engaged_week": embodiment_effect,
            "initial_refusal_probability": initial_refusal,
            "discomfort_dropout_increment": discomfort_dropout,
            "false_alert_probability": false_alert_probability,
            "crisis_sensitivity": crisis_sensitivity,
            "review_minutes_per_alert": review_minutes,
            "fallback_screen_probability": fallback_probability,
            "response_difference_percentage_points": (robot["response_50pct"].mean() - screen["response_50pct"].mean()) * 100,
            "completion_difference_percentage_points": (robot["completed_12_weeks"].mean() - screen["completed_12_weeks"].mean()) * 100,
            "mean_change_difference_phq9": robot["phq9_change"].mean() - screen["phq9_change"].mean(),
            "review_minutes_difference": robot["clinician_review_minutes"].mean() - screen["clinician_review_minutes"].mean(),
            "physical_near_miss_difference_per_100": (robot["physical_near_misses"].mean() - screen["physical_near_misses"].mean()) * 100,
        })

    uncertainty = pd.DataFrame(rows)
    uncertainty.to_csv(output_dir / "individual_parameter_uncertainty.csv", index=False)
    summarize_parameter_uncertainty(uncertainty, output_dir)
    return uncertainty


def summarize_parameter_uncertainty(uncertainty: pd.DataFrame, output_dir: Path) -> pd.DataFrame:
    """Bootstrap stability intervals for proportions across the chosen scenario ensemble."""
    definitions = {
        "response_positive": uncertainty["response_difference_percentage_points"] > 0,
        "completion_negative": uncertainty["completion_difference_percentage_points"] < 0,
        "phq_change_favorable": uncertainty["mean_change_difference_phq9"] < 0,
        "review_positive": uncertainty["review_minutes_difference"] > 0,
        "near_miss_positive": uncertainty["physical_near_miss_difference_per_100"] > 0,
    }
    rows = []
    for label, indicator in definitions.items():
        result = bootstrap_mean_ci(
            indicator.astype(float).to_numpy() * 100,
            n_resamples=10_000,
            seed=f"parameter-uncertainty:{label}",
            method="BCa",
        )
        rows.append({
            "diagnostic": label,
            "percent_of_scenario_draws": float(result["mean"]),
            "scenario_resampling_ci_low": float(result["bootstrap_ci_low"]),
            "scenario_resampling_ci_high": float(result["bootstrap_ci_high"]),
            "scenario_draws": int(len(indicator)),
            "interpretation": "Resampling stability over the selected illustrative scenario ensemble; not a posterior or clinical CI",
        })
    result = pd.DataFrame(rows)
    result.to_csv(output_dir / "individual_parameter_uncertainty_summary.csv", index=False)
    return result


def run_trial_replications(
    output_dir: Path,
    replications: int = 200,
    n_per_arm: int = 1200,
    weeks: int = 12,
    base_seed: int = SEED + 40000,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Repeat the individual experiment and summarize arm means and contrasts.

    Independent replication identifiers are the resampling unit. Paired
    pathway contrasts preserve the shared synthetic cohort within each
    replication. BCa bootstrap intervals quantify uncertainty in the expected
    model output under fixed inputs, not uncertainty in a clinical effect.
    """
    arm_keys = ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]
    rows: list[dict[str, float | str]] = []
    weekly_rows: list[pd.DataFrame] = []
    for replication in range(replications):
        cohort_seed = base_seed + replication * 1009
        for arm_index, key in enumerate(arm_keys):
            event_seed = base_seed + 1_000_000 + replication * 1009 + arm_index * 97
            patient, weekly = simulate_arm(
                ARM_CONFIGS[key],
                n=n_per_arm,
                weeks=weeks,
                seed=cohort_seed,
                cohort_seed=cohort_seed,
                event_seed=event_seed,
            )
            row = summarize(patient)
            row["replication"] = replication
            rows.append(row)
            weekly = weekly.copy()
            weekly["replication"] = replication
            weekly_rows.append(weekly)

    replications_df = pd.DataFrame(rows)
    weekly_replications = pd.concat(weekly_rows, ignore_index=True)
    replications_df.to_csv(output_dir / "individual_replication_results.csv", index=False)
    weekly_replications.to_csv(output_dir / "individual_weekly_replication_results.csv", index=False)

    arm_metrics = [
        "mean_baseline_phq9", "mean_week12_phq9_locf", "mean_phq9_change",
        "response_percent", "remission_percent", "completion_percent",
        "initial_refusal_percent", "mean_engaged_sessions", "raw_alerts_per_100",
        "false_alerts_per_100", "confirmed_false_escalations_per_100",
        "crisis_weeks_per_100", "missed_crises_per_100_crisis_weeks",
        "mean_clinician_review_minutes", "physical_near_misses_per_100",
        "mean_downtime_sessions",
    ]
    arm_summary = bootstrap_group_summary(
        replications_df,
        group_column="arm",
        metrics=arm_metrics,
        label_prefix="individual-arm",
        n_resamples=5_000,
    )
    arm_summary["n_per_arm_per_replication"] = n_per_arm
    arm_summary.to_csv(output_dir / "individual_arm_replication_summary.csv", index=False)

    weekly_summary_rows: list[dict[str, float | int | str]] = []
    for (arm, week), group in weekly_replications.groupby(["arm", "week"], sort=False):
        row: dict[str, float | int | str] = {"arm": arm, "week": int(week), "replications": int(len(group))}
        for metric in ["mean_phq9_locf", "engagement_rate_active", "active_fraction", "cumulative_alerts_per_100"]:
            result = bootstrap_mean_ci(
                group[metric].to_numpy(),
                n_resamples=3_000,
                seed=f"individual-weekly:{arm}:{week}:{metric}",
                method="BCa",
            )
            row[f"{metric}_mean"] = float(result["mean"])
            row[f"{metric}_ci_low"] = float(result["bootstrap_ci_low"])
            row[f"{metric}_ci_high"] = float(result["bootstrap_ci_high"])
        weekly_summary_rows.append(row)
    weekly_summary = pd.DataFrame(weekly_summary_rows)
    weekly_summary.to_csv(output_dir / "individual_weekly_bootstrap_summary.csv", index=False)

    metrics = {
        "response_percent": "Response difference (percentage points)",
        "remission_percent": "Remission difference (percentage points)",
        "completion_percent": "Completion difference (percentage points)",
        "mean_phq9_change": "Mean PHQ-9 change difference",
        "missed_crises_per_100_crisis_weeks": "Missed crisis-weeks difference per 100 crisis-weeks",
        "mean_clinician_review_minutes": "Clinician review difference (minutes per participant)",
        "physical_near_misses_per_100": "Physical near-miss difference per 100 participants",
    }
    screen_name = ARM_CONFIGS["screen_agent"].name
    comparator_names = [ARM_CONFIGS["embodied_robot"].name, ARM_CONFIGS["robot_hitl"].name]
    contrast_rows: list[dict[str, float | int | str]] = []
    for comparator in comparator_names:
        left = replications_df.loc[replications_df["arm"] == comparator].set_index("replication")
        right = replications_df.loc[replications_df["arm"] == screen_name].set_index("replication")
        for metric, label in metrics.items():
            delta = (left[metric] - right[metric]).sort_index()
            stats_row = paired_contrast_statistics(delta.to_numpy(), label=f"individual:{comparator}:{metric}")
            contrast_rows.append({
                "comparator": comparator,
                "reference": screen_name,
                "metric": metric,
                "metric_label": label,
                "outcome_family": "individual-primary",
                **stats_row,
                "n_per_arm_per_replication": n_per_arm,
            })
    contrast_summary = add_holm_columns(
        pd.DataFrame(contrast_rows), group_columns=["comparator"]
    )
    contrast_summary.to_csv(output_dir / "individual_contrast_summary.csv", index=False)
    return replications_df, contrast_summary, weekly_replications, arm_summary, weekly_summary


def create_replication_figure(contrast_summary: pd.DataFrame, figure_dir: Path) -> None:
    """Create a bootstrap confidence-interval plot for primary contrasts."""
    subset = contrast_summary[contrast_summary["metric"].isin(["response_percent", "completion_percent"])].copy()
    subset["display"] = subset["comparator"].replace({
        ARM_CONFIGS["embodied_robot"].name: "Robot",
        ARM_CONFIGS["robot_hitl"].name: "Robot + human gate",
    }) + " - " + subset["metric"].replace({
        "response_percent": "response",
        "completion_percent": "completion",
    })
    subset = subset.reset_index(drop=True)
    y = np.arange(len(subset))
    means = subset["mean_difference"].to_numpy()
    lower = means - subset["bootstrap_ci_low"].to_numpy()
    upper = subset["bootstrap_ci_high"].to_numpy() - means
    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.errorbar(means, y, xerr=np.vstack([lower, upper]), fmt="o", capsize=4, linestyle="none")
    ax.axvline(0, linewidth=1, linestyle="--")
    ax.set_yticks(y, subset["display"])
    ax.set_xlabel("Difference versus screen agent (percentage points)")
    ax.set_title("Paired mean contrasts with 95% BCa bootstrap CIs")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "individual_contrast_intervals")


def _metric_arrays(summary: pd.DataFrame, metric: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = summary[f"{metric}_mean"].to_numpy(dtype=float)
    low = summary[f"{metric}_ci_low"].to_numpy(dtype=float)
    high = summary[f"{metric}_ci_high"].to_numpy(dtype=float)
    return means, means - low, high - means


def create_figures(
    weekly_summary: pd.DataFrame,
    arm_summary: pd.DataFrame,
    sensitivity: pd.DataFrame,
    parameter_uncertainty: pd.DataFrame,
    figure_dir: Path,
) -> None:
    figure_dir.mkdir(parents=True, exist_ok=True)
    order = [ARM_CONFIGS[k].name for k in ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]]
    labels = ["Usual care", "Screen agent", "Robot", "Robot +\nhuman gate"]
    endpoint = arm_summary.set_index("arm").loc[order].reset_index()

    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for arm in order:
        group = weekly_summary.loc[weekly_summary["arm"] == arm].sort_values("week")
        ax.plot(group["week"], group["mean_phq9_locf_mean"], marker="o", label=arm)
        ax.fill_between(
            group["week"], group["mean_phq9_locf_ci_low"], group["mean_phq9_locf_ci_high"], alpha=0.14
        )
    ax.set_xlabel("Week")
    ax.set_ylabel("Mean PHQ-9 (last observation carried forward)")
    ax.set_title("Synthetic symptom trajectories with 95% bootstrap CIs")
    ax.legend(frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "individual_phq9_trajectories")

    x = np.arange(len(endpoint))
    width = 0.25
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    for offset, metric, label in [
        (-width, "response_percent", "Response"),
        (0.0, "remission_percent", "Remission"),
        (width, "completion_percent", "Completed 12 weeks"),
    ]:
        means, lower, upper = _metric_arrays(endpoint, metric)
        ax.bar(x + offset, means, width=width, yerr=np.vstack([lower, upper]), label=label, capsize=3)
    ax.set_xticks(x, labels)
    ax.set_ylabel("Participants (%)")
    ax.set_title("Clinical and engagement endpoints with 95% bootstrap CIs")
    ax.legend(frameon=False, ncol=3)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    save_figure(fig, figure_dir, "individual_endpoints")

    pivot = sensitivity.pivot(index="robot_downtime", columns="engagement_logit_advantage", values="response_difference_percentage_points")
    robust = sensitivity.pivot(index="robot_downtime", columns="engagement_logit_advantage", values="response_difference_ci_low") > 0
    fig, ax = plt.subplots(figsize=(8.3, 5.4))
    x_edges = np.arange(len(pivot.columns) + 1)
    y_edges = np.arange(len(pivot.index) + 1)
    mesh = ax.pcolormesh(x_edges, y_edges, pivot.values, shading="flat")
    cbar = fig.colorbar(mesh, ax=ax, label="Robot minus screen response (percentage points)")
    cbar.solids.set_rasterized(False)
    yy, xx = np.where(robust.to_numpy())
    if len(xx):
        ax.scatter(xx + 0.5, yy + 0.5, marker="o", facecolors="none", edgecolors="black", label="95% CI excludes 0")
        ax.legend(frameon=False, loc="upper left")
    ax.set_xticks(np.arange(len(pivot.columns)) + 0.5, [f"{v:.2f}" for v in pivot.columns])
    ax.set_yticks(np.arange(len(pivot.index)) + 0.5, [f"{v:.0%}" for v in pivot.index])
    ax.set_xlim(0, len(pivot.columns))
    ax.set_ylim(0, len(pivot.index))
    ax.set_xlabel("Engagement advantage over screen (logit scale)")
    ax.set_ylabel("Robot downtime")
    ax.set_title("Response sensitivity and bootstrap-supported cells")
    fig.tight_layout()
    save_figure(fig, figure_dir, "individual_sensitivity_heatmap")

    safety_metrics = [
        ("false_alerts_per_100", "False alerts per 100 participants"),
        ("missed_crises_per_100_crisis_weeks", "Missed high-risk weeks per 100"),
        ("mean_clinician_review_minutes", "Review minutes per participant"),
        ("physical_near_misses_per_100", "Physical near-misses per 100"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(9.0, 7.2), constrained_layout=True)
    for ax, (metric, title) in zip(axes.flat, safety_metrics, strict=True):
        means, lower, upper = _metric_arrays(endpoint, metric)
        ax.bar(x, means, yerr=np.vstack([lower, upper]), capsize=3)
        ax.set_xticks(x, ["Usual", "Screen", "Robot", "Robot +\ngate"])
        ax.set_title(title, fontsize=10.5)
        ax.grid(axis="y", alpha=0.25)
    fig.suptitle("Patient-level safety and hidden labor (95% bootstrap CIs)")
    save_figure(fig, figure_dir, "individual_safety_tradeoffs")

    fig, ax = plt.subplots(figsize=(8.0, 5.4))
    ax.scatter(
        parameter_uncertainty["response_difference_percentage_points"],
        parameter_uncertainty["completion_difference_percentage_points"],
        alpha=0.55,
        s=24,
    )
    ax.axvline(0, linewidth=1, linestyle="--")
    ax.axhline(0, linewidth=1, linestyle="--")
    ax.set_xlabel("Robot + human gate minus screen response (percentage points)")
    ax.set_ylabel("Robot + human gate minus screen completion (percentage points)")
    ax.set_title("Scenario uncertainty: symptom gains versus retention losses")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    save_figure(fig, figure_dir, "individual_parameter_uncertainty_tradeoff")


def main() -> None:
    root = Path(__file__).resolve().parent
    output_dir = root / "outputs"
    figure_dir = root / "figures"
    output_dir.mkdir(exist_ok=True)
    figure_dir.mkdir(exist_ok=True)

    patients = []
    weekly_frames = []
    summaries = []
    for key in ["usual_care", "screen_agent", "embodied_robot", "robot_hitl"]:
        patient, weekly = simulate_arm(ARM_CONFIGS[key])
        patients.append(patient)
        weekly_frames.append(weekly)
        summaries.append(summarize(patient))

    patient_all = pd.concat(patients, ignore_index=True)
    weekly_all = pd.concat(weekly_frames, ignore_index=True)
    base_summary = pd.DataFrame(summaries)
    sensitivity = run_sensitivity(output_dir)
    print("  individual sensitivity grid complete", flush=True)
    parameter_uncertainty = run_parameter_uncertainty(output_dir)
    print("  individual parameter uncertainty complete", flush=True)
    _, contrast_summary, _, arm_summary, weekly_summary = run_trial_replications(output_dir)
    print("  individual repeated trials and bootstrap statistics complete", flush=True)

    patient_all.to_csv(output_dir / "individual_patient_level_synthetic.csv", index=False)
    weekly_all.to_csv(output_dir / "individual_weekly_trajectories.csv", index=False)
    base_summary.to_csv(output_dir / "individual_arm_summary.csv", index=False)
    with open(output_dir / "individual_model_parameters.json", "w", encoding="utf-8") as f:
        json.dump({k: asdict(v) for k, v in ARM_CONFIGS.items()}, f, indent=2)

    # Release large simulation objects before rendering high-resolution figures.
    del patients, weekly_frames, summaries, patient_all, weekly_all
    gc.collect()
    plt.close("all")
    create_figures(weekly_summary, arm_summary, sensitivity, parameter_uncertainty, figure_dir)
    create_replication_figure(contrast_summary, figure_dir)
    print(arm_summary[["arm", "response_percent_mean", "response_percent_ci_low", "response_percent_ci_high", "completion_percent_mean", "completion_percent_ci_low", "completion_percent_ci_high"]].to_string(index=False, float_format=lambda x: f"{x:.3f}"))


if __name__ == "__main__":
    main()
