"""Build exhaustive parameter dictionaries and validation/elicitation documentation."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import csv
import json

import pandas as pd

from individual_microsimulation import ARM_CONFIGS
from service_queue_simulation import CONFIGS
from global_sensitivity import INDIVIDUAL_PARAMETERS, SERVICE_PARAMETERS
from scenario_analysis_v4_3 import individual_configs, service_configs

ROOT = Path(__file__).resolve().parent
CONFIG_DIR = ROOT / "config"
DOCS_DIR = ROOT / "docs"
CONFIG_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

REFS = {
    "PHQ": "Kroenke et al. 2001; Lowe et al. 2004",
    "DIGITAL_ATTRITION": "van Ballegooijen et al. 2014; Torous et al. 2020; Linardon and Fuller-Tyszkiewicz 2020",
    "DIGITAL_IMPLEMENTATION": "Torous et al. 2021; Greenhalgh et al. 2017",
    "ROBOT_EVIDENCE": "Guemghar et al. 2022; Kling et al. 2025; Huang et al. 2023",
    "MODEL_UNCERTAINTY": "Briggs et al. 2012; Eddy et al. 2012",
    "EXPERT_ELICITATION": "Bojke et al. 2021; Soares et al. 2024",
    "SIM_VALIDATION": "Sargent 2013; Monks et al. 2019",
    "SENSITIVITY": "Sobol 2001; Saltelli et al. 2010; Pianosi et al. 2016",
}

GLOBAL_INDIVIDUAL = {p.name: p for p in INDIVIDUAL_PARAMETERS}
GLOBAL_SERVICE = {p.name: p for p in SERVICE_PARAMETERS}


def arm_values(name: str) -> str:
    return "; ".join(f"{key}={getattr(cfg, name)}" for key, cfg in ARM_CONFIGS.items())


def queue_values(name: str) -> str:
    return "; ".join(f"{key}={getattr(cfg, name)}" for key, cfg in CONFIGS.items())


def range_text(mapping, key: str, default: str = "Not varied in v4.3 global analysis") -> str:
    p = mapping.get(key)
    return f"{p.low:g} to {p.high:g} {p.unit}" if p else default


def individual_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    def add(parameter, symbol, unit, base, neutral, skeptical, role, rationale, ordering, evidence, refs, status="Illustrative; requires empirical calibration"):
        rows.append({
            "parameter": parameter, "symbol": symbol, "unit_or_scale": unit,
            "base_case_value_or_distribution": base, "neutral_assumption": neutral,
            "skeptical_assumption": skeptical, "global_range": range_text(GLOBAL_INDIVIDUAL, parameter),
            "functional_role": role, "selection_and_range_rationale": rationale,
            "ordering_rationale": ordering, "evidence_class": evidence,
            "supporting_references": refs, "calibration_status": status,
        })

    add("weeks", "T", "weeks", "12", "12", "12", "Simulation horizon and completion endpoint.",
        "A 12-week horizon is common enough to represent an acute digital intervention while remaining short enough for weekly engagement dynamics. It is a structural design choice rather than an estimate.",
        "Held constant across pathways to isolate pathway differences.", "Structural assumption", REFS["DIGITAL_ATTRITION"])
    add("baseline_phq9", "Y_i0", "PHQ-9 points (0-27)", "truncated Normal(15.5, 3.2), clipped 10-24", "same", "same",
        "Initial symptom severity and driver of subsequent improvement and crisis risk.",
        "Centers the synthetic cohort in the moderate-to-moderately severe range and avoids floor/ceiling extremes. The scale and thresholds are empirically established; the distribution is not calibrated to a specific clinic.",
        "Shared exactly between pathways within replication.", "Empirical scale anchor; illustrative distribution", REFS["PHQ"])
    add("technology_acceptance", "A_i", "unit interval", "Beta(2.4, 1.9)", "same", "same",
        "Patient heterogeneity entering engagement and initial trust.",
        "A right-of-center beta distribution creates heterogeneous but generally permissive acceptance. Shape parameters were selected for face validity and should be replaced with survey data.",
        "Shared between pathways; pathway intercepts and refusal probabilities express interface differences.", "Face-validity assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("privacy_concern", "P_i", "unit interval", "Beta(2.1, 2.4)", "same", "same",
        "Patient heterogeneity entering engagement, trust, and dropout.",
        "A broad, mildly left-of-center beta distribution represents mixed privacy concern. It is intentionally not tied to a single instrument.",
        "Higher pathway privacy coefficients penalize physical systems more strongly because sensors and copresence can increase salience of privacy concerns.", "Face-validity assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("social_support", "S_i", "standardized latent score", "Normal(0, 1)", "same", "same",
        "Heterogeneity term in weekly engagement.", "Standard normal scaling makes the coefficient interpretable per SD and avoids claiming use of a specific instrument.",
        "Shared across pathways.", "Structural latent-variable assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("treatment_responsiveness", "R_i", "PHQ-9 points/week", "Normal(0, 0.13)", "same", "same",
        "Persistent individual deviation in weekly symptom response.", "Small mean-zero heterogeneity prevents identical trajectories without dominating pathway effects; not empirically calibrated.",
        "Shared across pathways within the cohort.", "Face-validity assumption", REFS["MODEL_UNCERTAINTY"])
    add("engagement_intercept", "alpha_a", "logit units", arm_values("engagement_intercept"),
        f"robot={ARM_CONFIGS['screen_agent'].engagement_intercept}", f"robot={ARM_CONFIGS['screen_agent'].engagement_intercept - 0.10}",
        "Pathway-specific baseline log-odds of engaging in an available weekly session.",
        "Base ordering encodes the hypothesis that copresence can increase salience; the global range spans a skeptical disadvantage (-0.10) to a modest advantage (+0.35) relative to screen.",
        "Robot > screen > usual in the base case; neutral sets robot equal to screen and skeptical reverses the ordering.", "Literature-informed direction; illustrative magnitude", REFS["ROBOT_EVIDENCE"])
    add("content_effect", "beta_content", "PHQ-9 points per engaged week", arm_values("content_effect"), "robot=screen=0.32", "robot=screen=0.32",
        "Incremental symptom improvement from functionally matched digital content.",
        "0.32 per engaged week yields a maximum 3.84-point 12-week content contribution before dropout/noise, below a 5-point PHQ-9 response benchmark and within the scale's observed treatment-change range. It is not a treatment-effect estimate.",
        "Identical for screen and robot by design so the primary comparator is content matched.", "Scale-anchored but uncalibrated", REFS["PHQ"])
    add("embodiment_effect", "beta_emb", "PHQ-9 points per engaged embodied week", arm_values("embodiment_effect"), "robot=0", "robot=0",
        "Additional symptom increment assigned only to an engaged, non-fallback embodied session.",
        "The base value 0.08 implies at most 0.96 points over 12 fully engaged weeks. The global range 0-0.12 includes no embodiment effect and a modest upper stress bound; evidence does not justify a larger clinical increment.",
        "Zero for nonembodied pathways; neutral and skeptical scenarios set it to zero.", "Hypothesis-generating assumption", REFS["ROBOT_EVIDENCE"])
    add("weekly_decay", "delta_a", "logit units/week", arm_values("weekly_decay"), "robot=screen=0.025", "robot=0.035",
        "Linear loss of engagement log-odds with elapsed week (novelty/effort decay).",
        "Values generate gradual rather than abrupt decline over 12 weeks and are directionally consistent with digital attrition. They are not fitted survival parameters.",
        "Base robot decay is lower than screen to encode slower novelty loss; neutral equalizes it; skeptical makes robot decay faster.", "Literature-informed direction; illustrative magnitude", REFS["DIGITAL_ATTRITION"])
    add("downtime", "d_a", "probability/session", arm_values("downtime"), "robot=0.05", "robot=0.20",
        "Probability that the pathway is unavailable in a weekly session; fallback may preserve content delivery.",
        "Base values distinguish software availability from physical-device maintenance. The 0.02-0.20 global range spans high reliability through one-in-five session disruption, appropriate for stress testing rather than forecasting.",
        "Robot > screen in the base case because physical systems add hardware, mobility, and environmental failure modes.", "Implementation-informed stress range", REFS["ROBOT_EVIDENCE"])
    add("initial_refusal", "rho_a", "probability before first use", arm_values("initial_refusal"), "robot=0.05", "robot=0.15",
        "Immediate noninitiation and therefore noncompletion.",
        "The 2.5%-15% range separates ordinary digital noninitiation from additional physical/privacy discomfort; digital intervention attrition literature supports treating uptake and completion as material uncertainties, not these exact values.",
        "Robot > screen because a physical device may be more salient or intrusive; human gating slightly reduces base robot refusal.", "Literature-informed range class; uncalibrated values", REFS["DIGITAL_ATTRITION"])
    add("privacy_penalty", "gamma_P,a", "engagement-logit coefficient", arm_values("privacy_penalty"), "robot=0.25", "robot=0.55",
        "Modifies engagement according to centered privacy concern.",
        "The 0.20-0.55 range keeps the maximum effect modest on the logit scale while permitting meaningful heterogeneity. It is a behavioral coefficient, not a measured odds ratio.",
        "Base robot > screen because embodied sensing/coproximity may increase privacy salience; neutral equalizes them.", "Face-validity assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("discomfort_dropout", "kappa_a", "absolute weekly dropout probability", arm_values("discomfort_dropout"), "robot=0.005", "robot=0.020",
        "Embodiment-specific additive dropout risk.",
        "The 0-0.02 range adds up to two percentage points per active week, large enough to challenge retention but bounded below the model's 12% weekly cap. Digital attrition reviews motivate the scale of concern, not a robot-specific estimate.",
        "Zero for nonembodied pathways; higher in skeptical scenario.", "Literature-informed stress range; not robot-calibrated", REFS["DIGITAL_ATTRITION"])
    add("crisis_sensitivity", "Se_a", "probability", arm_values("crisis_sensitivity"), "robot=0.82", "robot=0.78",
        "Probability of an alert in a simulated crisis week.",
        "The 0.70-0.95 global range represents poor-to-strong detection while excluding impossible perfection. No specific device has been validated against this synthetic endpoint.",
        "Base robot pathways exceed screen to encode richer sensing; skeptical reduces this to the screen-like region.", "Diagnostic stress assumption", REFS["MODEL_UNCERTAINTY"])
    add("false_alert_probability", "FPR_a", "probability per active noncrisis week", arm_values("false_alert_probability"), "robot=0.030", "robot=0.060",
        "Generates alerts in weeks without a crisis and therefore workload/trust burden.",
        "The 0.015-0.06 range spans approximately 0.18-0.72 expected raw false alerts per fully active participant-year before dropout; it is a workload stress range, not empirical specificity.",
        "Robot > screen because higher sensitivity and additional sensors can create more alerts; human review changes escalation, not raw-alert generation.", "Safety-workflow stress assumption", REFS["ROBOT_EVIDENCE"])
    add("review_minutes_per_alert", "m_alert,a", "minutes/alert", arm_values("review_minutes_per_alert"), "robot=9", "robot=12",
        "Adds clinician verification work for every alert.",
        "The 4-15 minute global range spans rapid disposition through documentation-intensive review and directly supports break-even analysis.",
        "Human-gated robot is highest in the base case because mandatory verification is more intensive than routine screen review.", "Operational face-validity range", REFS["SIM_VALIDATION"])
    add("routine_audit_minutes", "m_audit,a", "minutes/participant", arm_values("routine_audit_minutes"), "robot=4", "robot=6",
        "Fixed per-participant oversight burden independent of alerts.",
        "0-6 minutes brackets no audit through a short documented check; base values preserve an explicit hidden-labor gradient.",
        "Human gate > ungated robot > screen > usual.", "Operational face-validity range", REFS["SIM_VALIDATION"])
    add("physical_near_miss_per_active_week", "h_a", "probability per active nonfallback week", arm_values("physical_near_miss_per_active_week"), "robot=0.0006", "robot=0.0012",
        "Generates noninjury physical near-miss counts only when the robot is physically active.",
        "0-0.0015 is deliberately rare (up to 1.8 per 100 fully active participants over 12 weeks) but nonzero. It is a placeholder requiring incident data and safety-case elicitation.",
        "Exactly zero for nonembodied pathways; slightly lower with human gating in the base case.", "Explicit placeholder", REFS["ROBOT_EVIDENCE"])
    add("human_verification", "H_a", "Boolean", arm_values("human_verification"), "robot=True", "robot=True",
        "Changes false-escalation probability, alert review, and initial trust.",
        "Represents a categorical workflow design, not a probability. It is retained in neutral and skeptical cases because the target pathway is human gated.",
        "True for usual, screen, and gated robot; false only for ungated robot.", "Structural workflow assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("fallback_screen_probability", "f_a", "probability conditional on downtime", arm_values("fallback_screen_probability"), "robot=0.60", "robot=0.30",
        "Preserves content, but not embodiment increment, when the physical system is down.",
        "The 0-0.90 global range spans no contingency through highly reliable fallback and allows interaction with downtime to be estimated.",
        "Highest for the human-gated robot because the workflow explicitly includes supervised fallback.", "Operational stress range", REFS["SIM_VALIDATION"])

    # Shared weekly equations and coefficients.
    shared = [
        ("trust_verification_bonus", "0.08", "trust score", "Initial trust increment when human verification is visible.", "Small positive offset selected to encode transparency; uncalibrated."),
        ("trust_acceptance_coefficient", "0.12", "trust per acceptance unit", "Initial trust effect of technology acceptance.", "Keeps patient-level trust heterogeneity bounded."),
        ("trust_privacy_coefficient", "-0.10", "trust per privacy unit", "Initial trust effect of privacy concern.", "Direction follows implementation theory; magnitude is illustrative."),
        ("engagement_acceptance_coefficient", "1.05", "logit per acceptance unit", "Largest patient-level engagement covariate.", "Makes acceptance materially influential without determining engagement alone."),
        ("engagement_prior_use_coefficient", "0.34", "logit", "State dependence after prior engagement.", "Encodes habit/persistence; uncalibrated."),
        ("engagement_social_support_coefficient", "0.13", "logit per SD", "Social-support contribution to engagement.", "Small positive contextual effect."),
        ("engagement_symptom_penalty", "-0.025", "logit per PHQ-9 point above 15", "Reduces engagement at higher symptom burden.", "Modest burden effect; avoids deterministic disengagement."),
        ("base_weekly_improvement_intercept", "0.24", "PHQ-9 points/week", "Usual-care/regression-to-mean component.", "Generates clinically plausible declining trajectories; not calibrated."),
        ("base_weekly_improvement_severity_slope", "0.022", "PHQ-9 points/week per baseline point above 14", "Allows greater absolute improvement at higher baseline severity.", "Avoids identical changes across baseline severity."),
        ("symptom_noise_sd", "0.62", "PHQ-9 points/week", "Independent weekly symptom noise.", "Selected to produce overlap across finite synthetic trials while retaining stable mean contrasts."),
        ("crisis_logit_intercept", "-10.2", "logit", "Sets rare baseline crisis-week probability.", "Explicit stylization; requires clinical event-rate calibration."),
        ("crisis_current_phq_coefficient", "0.27", "logit per PHQ-9 point", "Raises crisis risk with current severity.", "Direction clinically plausible; magnitude uncalibrated."),
        ("crisis_worsening_coefficient", "0.42", "logit per worsening point", "Raises crisis risk after symptom worsening.", "Direction clinically plausible; magnitude uncalibrated."),
        ("verified_false_escalation_probability", "0.12", "probability/false alert", "False alerts escalated despite verification.", "Represents substantial suppression by human review; uncalibrated."),
        ("unverified_false_escalation_probability", "0.72", "probability/false alert", "False alerts escalated without verification.", "Creates a strong gating contrast for stress testing."),
        ("trust_true_alert_increment", "+0.025", "trust units/event", "Trust update after true alert.", "Small positive update."),
        ("trust_false_escalation_decrement", "-0.040", "trust units/event", "Trust update after false escalation.", "Negative reliability penalty."),
        ("trust_missed_crisis_decrement", "-0.075", "trust units/event", "Trust update after missed crisis.", "Largest trust penalty because it is the most consequential failure."),
        ("dropout_intercept", "0.010", "weekly probability", "Baseline dropout risk.", "Combined with other terms to yield attrition in the range observed in digital interventions."),
        ("dropout_nonengagement_increment", "0.030", "weekly probability", "Penalty after nonengagement.", "Largest modifiable weekly dropout increment."),
        ("dropout_privacy_coefficient", "0.016", "weekly probability per privacy unit", "Privacy-related attrition.", "Small patient-level effect."),
        ("dropout_worsening_increment", "0.010", "weekly probability", "Penalty when PHQ-9 worsens by >1.5.", "Small symptom-frustration effect."),
        ("dropout_engagement_decrement", "-0.008", "weekly probability", "Protective effect of engagement.", "Offsets part of the baseline/nonengagement risk."),
        ("dropout_probability_bounds", "0.002-0.12", "weekly probability", "Prevents zero or implausibly extreme weekly dropout.", "Numerical/face-validity constraint."),
        ("response_threshold", ">=50% reduction", "binary endpoint", "Defines response.", "Established depression-response convention."),
        ("remission_threshold", "PHQ-9 <=4", "binary endpoint", "Defines remission.", "Established PHQ-9 convention."),
    ]
    for parameter, value, unit, role, rationale in shared:
        add(parameter, "-", unit, value, "same", "same", role, rationale,
            "Shared across pathways unless the role explicitly depends on a pathway parameter.", "Structural or scale-anchored assumption", REFS["PHQ"] + "; " + REFS["DIGITAL_ATTRITION"])
    return rows


def service_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    def add(parameter, symbol, unit, base, neutral, skeptical, role, rationale, ordering, evidence, refs, status="Illustrative; requires local operational calibration"):
        rows.append({
            "parameter": parameter, "symbol": symbol, "unit_or_scale": unit,
            "base_case_value_or_distribution": base, "neutral_assumption": neutral,
            "skeptical_assumption": skeptical, "global_range": range_text(GLOBAL_SERVICE, parameter),
            "functional_role": role, "selection_and_range_rationale": rationale,
            "ordering_rationale": ordering, "evidence_class": evidence,
            "supporting_references": refs, "calibration_status": status,
        })

    add("arrivals_per_day", "lambda", "arrivals/working day", queue_values("arrivals_per_day"), "35", "35",
        "Poisson demand intensity shared across pathways in each paired replication.",
        "Base demand of 35/day places the clinic near capacity so nonlinear queues can emerge; the 25-45 global range spans underload through overload. It must be replaced with site-specific arrival data.",
        "Shared across pathways; varied globally because load interacts with capacity parameters.", "Operational stress range", REFS["SIM_VALIDATION"])
    add("days", "D", "observed working days", queue_values("days"), "35", "35", "Length of observed service simulation.",
        "Thirty-five observed days balances computational precision and a multiweek operational horizon.", "Shared across pathways.", "Structural assumption", REFS["SIM_VALIDATION"])
    add("warmup_days", "W", "working days", queue_values("warmup_days"), "5", "5", "Removes initial empty-system transient.",
        "Five days was prespecified and tested against 0, 2, and 10 days; ordering was unchanged.", "Shared across pathways.", "Validated structural assumption", REFS["SIM_VALIDATION"], "Warm-up sensitivity completed; local validation still required")
    add("workday_minutes", "L", "minutes/day", "420", "420", "420", "Defines productive daily capacity.",
        "Represents seven productive hours after breaks/administrative time. It is a transparent operational convention, not measured at a site.", "Shared across pathways.", "Operational convention", REFS["SIM_VALIDATION"])
    add("intake_servers", "c_intake,a", "parallel servers", queue_values("intake_servers"), "robot=4", "robot=2",
        "Number of simultaneous intake resources.",
        "Base counts instantiate plausible staffing/device configurations; the robot global range 2-5 tests whether adding devices resolves congestion.",
        "Screen has more parallel kiosks than robots in the base case because software terminals are assumed easier to provision.", "Operational stress assumption", REFS["SIM_VALIDATION"])
    add("intake_minutes_mean", "mu_intake,a", "minutes", queue_values("intake_minutes_mean"), "robot=14", "robot=16",
        "Mean primary intake duration before reset/rework.",
        "The robot range 10-18 minutes brackets faster structured capture through slower physical interaction; manual is longer at 24 minutes. Local time-and-motion data are required.",
        "Automation is assumed faster than manual; neutral makes robot equal to screen.", "Operational face-validity range", REFS["SIM_VALIDATION"])
    add("intake_minutes_sd", "sigma_intake,a", "minutes", queue_values("intake_minutes_sd"), "robot=4", "robot=5",
        "Normal service-time dispersion, truncated at 4 minutes.",
        "4-5 minutes provides moderate heterogeneity without creating negative durations; not fitted to observations.",
        "Manual has slightly greater dispersion than automated pathways.", "Operational face-validity assumption", REFS["SIM_VALIDATION"])
    add("human_fallback_servers", "c_fb,a", "servers", queue_values("human_fallback_servers"), "robot=1", "robot=1",
        "Capacity for downtime fallback and incomplete-assessment rework.", "One server makes fallback finite and potentially congestible.",
        "Zero for manual because manual is itself the baseline; one for digital pathways.", "Structural workflow assumption", REFS["SIM_VALIDATION"])
    add("human_fallback_minutes_mean", "mu_fb,a", "minutes", queue_values("human_fallback_minutes_mean"), "robot=20", "robot=20",
        "Mean duration of fallback intake, with SD fixed at 4 minutes and 4-minute minimum.",
        "Intermediate between automated and manual intake; requires local time-and-motion data.", "Shared by digital pathways.", "Operational face-validity assumption", REFS["SIM_VALIDATION"])
    add("downtime_day_probability", "d_a", "probability/day", queue_values("downtime_day_probability"), "robot=0.02", "robot=0.15",
        "Probability that an entire pathway uses fallback on a given day.",
        "The 0-0.20 global range spans highly reliable operation through one day in five disrupted; it is intentionally broader than the base case for stress testing.",
        "Robot > screen in the base case because physical hardware/environment adds failure modes; neutral equalizes them.", "Implementation-informed stress range", REFS["ROBOT_EVIDENCE"])
    add("incomplete_probability", "q_a", "probability/arrival", queue_values("incomplete_probability"), "robot=0.12", "robot=0.15",
        "Triggers fallback rework after incomplete digital intake.",
        "3%-15% brackets low rework through substantial input failure. Values are not observed rates.",
        "Base robot < screen because multimodal sensing is hypothesized to improve completion; neutral equalizes and skeptical reverses advantage.", "Workflow stress assumption", REFS["ROBOT_EVIDENCE"])
    add("incomplete_rework_minutes", "m_rework,a", "minutes/case", queue_values("incomplete_rework_minutes"), "robot=12", "robot=15",
        "Additional fallback-service time for incomplete assessments.", "8-15 minutes represents a partial repeat rather than a full new intake.",
        "Higher under skeptical assumptions.", "Operational face-validity assumption", REFS["SIM_VALIDATION"])
    add("clinician_servers", "c_clin", "parallel clinicians", queue_values("clinician_servers"), "5", "5",
        "Capacity of the downstream clinician stage.",
        "Five clinicians creates near-capacity behavior at 35 arrivals/day; the global range 4-7 tests interaction with demand and review burden.",
        "Shared across pathways within a parameter vector.", "Operational stress range", REFS["SIM_VALIDATION"])
    add("clinician_summary_saving_minutes", "s_a", "minutes/arrival", queue_values("clinician_summary_saving_minutes"), "robot=5", "robot=3",
        "Reduces acuity-specific base clinician time before the 25-minute floor.",
        "2-10 minutes spans weak through substantial documentation support. It is not an observed productivity estimate.",
        "Base gated robot > screen because richer structured capture is hypothesized; neutral equalizes and skeptical reduces saving.", "Productivity stress assumption", REFS["DIGITAL_IMPLEMENTATION"])
    add("clinician_review_minutes", "r_a", "minutes/arrival", queue_values("clinician_review_minutes"), "robot=6", "robot=12",
        "Mandatory review added for every digital intake.",
        "4-15 minutes spans brief verification through detailed review and directly affects queue break-even.",
        "Base human-gated robot > screen because verification obligations are greater; neutral equalizes them.", "Operational face-validity range", REFS["SIM_VALIDATION"])
    add("false_alert_probability", "FPR_a", "probability/non-high-acuity arrival", queue_values("false_alert_probability"), "robot=0.045", "robot=0.10",
        "Generates non-high-acuity alerts and alert-handling time.",
        "3%-12% global range is a broad burden stress test. It should be calibrated from prospective confusion matrices and workflow logs.",
        "Base robot > screen to reflect more sensitive multimodal detection.", "Diagnostic stress assumption", REFS["MODEL_UNCERTAINTY"])
    add("high_acuity_detection_sensitivity", "Se_a", "probability/high-acuity arrival", queue_values("high_acuity_detection_sensitivity"), "robot=0.78", "robot=0.80",
        "Probability of detecting a high-acuity case.",
        "70%-95% global range spans weak through strong discrimination without assuming perfection; no specific device is represented.",
        "Base gated robot > ungated robot > screen > manual; neutral equalizes robot and screen.", "Diagnostic stress assumption", REFS["MODEL_UNCERTAINTY"])
    add("physical_reset_minutes", "m_reset,a", "minutes/nonfallback intake", queue_values("physical_reset_minutes"), "robot=1", "robot=5",
        "Adds routine physical reset/sanitation work and occupies intake capacity.",
        "0-6 minutes spans no physical overhead through substantial reset work. This is routine work, not an adverse-event rate.",
        "Exactly zero for manual/screen and positive only for embodied pathways.", "Physical-workflow stress range", REFS["ROBOT_EVIDENCE"])
    add("robot_or_kiosk", "K_a", "Boolean", queue_values("robot_or_kiosk"), "robot=True", "robot=True",
        "Activates incomplete assessments, reset work, and routine review.", "Structural pathway flag.", "False only for manual.", "Structural assumption", REFS["SIM_VALIDATION"])
    add("human_verification", "H_a", "Boolean", queue_values("human_verification"), "robot=True", "robot=True",
        "Determines whether an alert adds 6 or 10 clinician minutes.", "Categorical workflow design.", "False only for ungated robot.", "Structural workflow assumption", REFS["DIGITAL_IMPLEMENTATION"])

    shared = [
        ("arrival_process", "Poisson(lambda) counts; Uniform(0,420) ordered arrival times", "stochastic process", "Generates daily arrivals and within-day timing.", "Standard transparent arrival-process approximation; requires goodness-of-fit against local data."),
        ("acuity_mix", "60% low, 30% medium, 10% high", "categorical probabilities", "Determines clinician service time and high-acuity detection denominator.", "Illustrative outpatient mix; requires local triage data."),
        ("base_clinician_minutes", "low=38; medium=52; high=72", "minutes/arrival", "Acuity-specific clinician work before summary savings/review.", "Ordered durations preserve clinical complexity; values require time-and-motion calibration."),
        ("minimum_clinician_minutes", "25", "minutes/arrival", "Lower bound after summary savings.", "Prevents implausibly short clinician encounters."),
        ("alert_minutes_with_verification", "6", "minutes/alert", "Additional handling after an alert in verified pathways.", "Short documented escalation assumption."),
        ("alert_minutes_without_verification", "10", "minutes/alert", "Additional handling after an alert without a gate.", "Higher because unfiltered escalation is assumed less efficient."),
        ("service_time_minimum", "4", "minutes", "Lower bound for primary/fallback service draws.", "Numerical and face-validity constraint."),
        ("fallback_service_sd", "4", "minutes", "Dispersion of fallback duration.", "Moderate uncalibrated heterogeneity."),
        ("abandonment_logit_intercept", "-5.2", "logit", "Sets low baseline abandonment.", "Chosen so abandonment rises mainly after long waits; requires empirical waiting/abandonment data."),
        ("abandonment_wait_slope", "0.010", "logit per minute above 120", "Raises abandonment with predicted wait beyond 120 minutes.", "Stylized monotonic relationship, not a fitted hazard."),
        ("abandonment_wait_threshold", "120", "minutes", "Delay before wait-sensitive abandonment increases.", "Face-validity threshold for severe delay."),
        ("abandonment_probability_cap", "0.25", "probability/arrival", "Bounds abandonment.", "Prevents extreme extrapolation under unstable queues."),
        ("queue_discipline", "FIFO at intake, fallback, and clinician resources", "operational rule", "Schedules starts at max(arrival, next server availability).", "Transparent default; priority triage is omitted and should be tested for local use."),
    ]
    for parameter, value, unit, role, rationale in shared:
        add(parameter, "-", unit, value, "same", "same", role, rationale,
            "Shared across pathways.", "Structural or face-validity assumption", REFS["SIM_VALIDATION"])
    return rows


def write_csvs() -> tuple[pd.DataFrame, pd.DataFrame]:
    ind = pd.DataFrame(individual_rows())
    svc = pd.DataFrame(service_rows())
    ind.to_csv(CONFIG_DIR / "individual_parameter_dictionary_v4.3.csv", index=False)
    svc.to_csv(CONFIG_DIR / "service_parameter_dictionary_v4.3.csv", index=False)
    return ind, svc


def write_model_specification() -> None:
    text = r'''# Complete mathematical and operational model specification (v4.3)

## Status and scope

The models are transparent, assumption-driven stress tests. They are not fitted digital twins, causal estimators, clinical prediction models, or validated safety models. All parameters, units, pathway values, ranges, rationales, and calibration status are listed in `config/individual_parameter_dictionary_v4.3.csv` and `config/service_parameter_dictionary_v4.3.csv`.

## 1. Individual microsimulation

### 1.1 Indices and state

Participant `i = 1,...,N`, pathway `a`, and week `t = 1,...,12`. The state comprises PHQ-9 `Y_iat`, active status `Z_iat`, previous engagement `E_ia,t-1`, trust `U_iat`, cumulative alerts, crisis weeks, review minutes, downtime, fallback, and physical near-misses. Baseline covariates are shared across pathways in paired replications.

### 1.2 Baseline draws

- `Y_i0 = clip(Normal(15.5, 3.2), 10, 24)`.
- Technology acceptance `A_i ~ Beta(2.4,1.9)`.
- Privacy concern `P_i ~ Beta(2.1,2.4)`.
- Social support `S_i ~ Normal(0,1)`.
- Treatment responsiveness `R_i ~ Normal(0,0.13)` PHQ-9 points/week.
- Initial trust: `U_ia0 = 0.08 H_a + 0.12 A_i - 0.10 P_i`, where `H_a` is the human-verification indicator.
- Initial refusal: `F_ia ~ Bernoulli(rho_a)`; active status is `Z_ia0 = 1-F_ia`.

### 1.3 Availability and fallback

For active participants, downtime `D_iat ~ Bernoulli(d_a)`. Conditional on downtime, screen fallback `B_iat ~ Bernoulli(f_a)`. Availability is `V_iat = (1-D_iat) OR B_iat`. Fallback preserves the content effect but removes the embodiment-specific symptom increment and physical near-miss exposure.

### 1.4 Engagement equation

`logit Pr(E_iat=1 | Z_i,a,t-1=1) = alpha_a + 1.05(A_i-0.5) - gamma_P,a(P_i-0.5) + 0.34 E_i,a,t-1 + 0.13 S_i + U_i,a,t-1 - delta_a(t-1) - 0.025 max(Y_i,a,t-1-15,0)`.

The realized session is engaged only if the Bernoulli engagement draw is positive and the pathway is available.

### 1.5 Symptom equation

`b_i = 0.24 + 0.022 max(Y_i0-14,0)`.

`Q_iat = E_iat [beta_content,a + beta_emb,a (1-B_iat)]`.

`Y_iat = clip(Y_i,a,t-1 - [b_i + Q_iat + R_i] + epsilon_iat, 0, 27)`, with `epsilon_iat ~ Normal(0,0.62)` for active participants. After dropout, the primary analysis uses last observation carried forward.

### 1.6 Crisis, alert, and verification equations

Let worsening `W_iat = Y_iat-Y_i,a,t-1`.

`logit Pr(C_iat=1) = -10.2 + 0.27 Y_iat + 0.42 max(W_iat,0)`.

`Pr(L_iat=1 | C_iat=1)=Se_a`; `Pr(L_iat=1 | C_iat=0)=FPR_a`.

A false alert is escalated with probability 0.12 under human verification and 0.72 without verification. Review burden is initialized at `m_audit,a` and increases by `m_alert,a` for every alert.

Trust updates are: `+0.025` after a true alert, `-0.040` after an escalated false alert, and `-0.075` after a missed crisis; trust is clipped to `[-0.5,0.5]`.

### 1.7 Physical exposure and dropout

A near-miss can occur only during an available, nonfallback embodied session: `N_iat ~ Bernoulli(h_a)`.

Weekly dropout probability is

`p_drop = clip[0.010 + 0.030(1-E_iat) + 0.016 P_i + kappa_a + 0.010 I(W_iat>1.5) - 0.008 E_iat, 0.002, 0.12]`.

New dropout is Bernoulli(`p_drop`) among active participants. Completion is active through week 12. Response is at least 50% PHQ-9 reduction; remission is PHQ-9 <=4.

### 1.8 Pairing and estimands

Within each replication, pathways share baseline covariate seeds but use independent pathway event streams. The primary estimand is the expected paired pathway difference versus the content-matched screen. Positive values favor the robot for response/remission/detection; negative values favor the robot for PHQ-9 change and missed-event measures. Burden directions are stated outcome by outcome.

## 2. Service discrete-event simulation

### 2.1 Horizon, arrivals, and acuity

A replication contains `W=5` warm-up and `D=35` observed working days, each `L=420` minutes. Daily counts are `N_d ~ Poisson(lambda)`, arrival times are ordered Uniform(0,L), and acuity is low/medium/high with probabilities 0.60/0.30/0.10. Paired pathways receive the same arrival, acuity, outage-uniform, service-normal, alert, incompleteness, and abandonment latent draws.

### 2.2 Resource scheduling

Each stage is FIFO. For a job arriving at time `a` with duration `s`, the next available server time is `v_min`, start is `max(a,v_min)`, finish is start plus `s`, and the resource's next availability becomes finish. Intake, fallback, and clinician stages have pathway-specific parallel-server counts.

### 2.3 Intake and downtime

Day `d` is down when a shared outage uniform is below pathway downtime probability. A digital pathway uses fallback on a down day. Primary intake duration is `max(4, Normal(mu_intake,a, sigma_intake,a))`; embodied pathways add `m_reset,a`. Fallback duration is `max(4, mu_fallback,a + 4z)`. An incomplete digital assessment occurs when its shared uniform is below `q_a` and adds `m_rework,a` on the fallback resource.

### 2.4 Detection and clinician work

For high-acuity arrivals, an alert occurs with probability `Se_a`; otherwise it occurs with probability `FPR_a`. Base clinician minutes are 38/52/72 for low/medium/high acuity. Clinician duration is

`max(base_acuity - s_a, 25) + I(digital) r_a + I(alert)[6 H_a + 10(1-H_a)]`.

### 2.5 Abandonment

Predicted waiting time is the interval from arrival to the later of intake completion and the earliest clinician availability. Abandonment probability is

`p_abandon = min[0.25, logistic(-5.2 + 0.010 max(predicted_wait-120,0))]`.

Abandoned jobs do not enter clinician service. For completed jobs, final wait is clinician start minus arrival.

### 2.6 Outputs and accounting

Outputs include mean and 90th-percentile wait, throughput, abandonment, false alerts, missed high-acuity cases, failover, incomplete rework, clinician utilization/overtime, intake workload, and routine physical reset events. For every pathway/replication, `arrivals = completed + abandoned` exactly.

## 3. Uncertainty analysis

Primary simulation uncertainty uses intact replication-level paired resampling, BCa intervals, sign-flip randomization tests, Holm adjustment, paired effect sizes, and Monte Carlo standard errors. Neutral and skeptical scenarios are deterministic parameter sets, not probability distributions.

The v4.3 global sensitivity analysis assumes independent Uniform distributions over the declared ranges. Scrambled Sobol A/B designs use 128 base points. First-order (`S1`), total-order (`ST`), and pairwise second-order (`S2`) indices use Saltelli estimators. Each vector averages two stochastic paired evaluations; 200 row-bootstrap samples provide diagnostic intervals. Wide or zero-crossing `S2` intervals are treated as inconclusive rather than as evidence of interaction.

## 4. Verification, calibration, and validation status

Code verification, deterministic reruns, range/impossible-event checks, shared-stream checks, flow accounting, warm-up sensitivity, and output reconciliation are implemented. Empirical calibration, external predictive validation, stakeholder elicitation, and formal face validation have not been completed. The protocol in `docs/STAKEHOLDER_ELICITATION_AND_FACE_VALIDATION_PROTOCOL_v4.3.md` specifies the required next phase.
'''
    (DOCS_DIR / "COMPLETE_MODEL_SPECIFICATION_v4.3.md").write_text(text, encoding="utf-8")


def write_validation_protocol() -> None:
    text = r'''# Structured parameter elicitation and face-validation protocol (v4.3)

## Current status

This protocol is prospective. No empirical calibration exercise, formal expert elicitation, patient/public involvement workshop, or external face-validation panel was conducted for v4.3. The manuscript and parameter dictionaries must not describe these activities as completed.

## Objectives

1. Replace weakly supported parameters with empirical estimates where data exist.
2. Quantify remaining uncertain parameters using a structured, bias-aware elicitation protocol.
3. Test conceptual, operational, and output face validity with independent stakeholders.
4. Define parameter dependencies rather than assuming independence when experts or data support correlation.

## Evidence hierarchy and calibration plan

1. **Local operational data:** timestamped arrivals, acuity, intake/review/service durations, downtime, fallback, incomplete assessments, false alerts, abandonment, staffing, reset/sanitation work.
2. **Prospective pilot data:** uptake/refusal, weekly engagement, dropout, fallback, alert confusion matrix, verification minutes, physical incidents/near-misses, PHQ-9 trajectories.
3. **External empirical literature:** systematic reviews, trials, implementation studies, and device reliability reports.
4. **Structured expert elicitation:** only for quantities that remain weakly identified.
5. **Transparent scenario bounds:** retained where neither data nor elicitation can justify a probability distribution.

For empirical calibration, preregister a target dataset and likelihood or estimating equations; split calibration and validation periods/sites; report goodness-of-fit and posterior/predictive checks; and retain uncalibrated priors/ranges for comparison.

## Stakeholder panel

Recruit at least 18-24 participants across six groups, with at least three independent participants per group:

- people with lived experience of depression and, where appropriate, caregivers;
- psychiatrists/psychologists and psychiatric nurses;
- clinic operations, scheduling, and quality/safety managers;
- human-robot interaction and robotics/reliability engineers;
- digital mental-health, privacy, cybersecurity, and ethics specialists;
- biostatistics, simulation, and health-economics methodologists.

Declare conflicts of interest, device/vendor relationships, and prior exposure to the modeled technology. Patient contributors should be compensated and supported using accessible materials.

## Quantities to elicit

Prioritize high total-order Sobol factors and parameters lacking direct data:

- engagement advantage or disadvantage versus a matched screen;
- embodiment-specific symptom increment;
- initial refusal and weekly discomfort-related dropout;
- session/day downtime and probability of usable screen fallback;
- alert sensitivity, false-alert probability, and verification time;
- routine audit and physical reset time;
- near-miss probability;
- intake duration, incomplete-assessment probability, summary time saving, and clinician review time;
- local demand, acuity mix, clinician capacity, and waiting-dependent abandonment.

For each quantity, define the population, setting, time unit, conditioning events, denominator, and whether the target is a probability, rate, duration, regression coefficient, or pathway difference.

## Elicitation procedure

Use an IDEA/SHELF-compatible sequence consistent with published health-care structured elicitation guidance:

1. **Preparation:** evidence dossier, plain-language model diagram, parameter definitions, training examples, and practice probability questions.
2. **Individual estimates:** independently elicit lower plausible bound, median, upper plausible bound, and confidence; use fixed quantiles (for example 5th, 50th, 95th) rather than vague ranges.
3. **Rationale capture:** record evidence, assumptions, subgroup concerns, and dependencies.
4. **Facilitated discussion:** reveal anonymized distributions, discuss divergent reasoning, and permit revision without requiring consensus.
5. **Aggregation:** prespecify behavioral consensus or mathematical pooling; retain individual distributions for sensitivity analysis.
6. **Calibration questions:** where feasible, include seed questions with known answers to diagnose overconfidence; do not use performance weighting without a prespecified rationale.
7. **Documentation:** archive materials, attendance, conflicts, raw judgments, revisions, aggregation code, and deviations.

## Face-validation workshops

Conduct separate conceptual-model and output-validation sessions with stakeholders who did not write the code.

### Conceptual and operational validation

Review the pathway diagram, state transitions, queue discipline, resource roles, time units, denominators, causal ordering, omitted feedback loops, and whether the screen comparator is genuinely functionally matched. Use structured ratings (1-5) for clarity, plausibility, completeness, and decision relevance plus free-text comments.

### Extreme-condition and trace validation

Walk through deterministic traces and extreme cases: zero downtime, complete downtime, zero/very high review time, no embodiment effect, negative engagement advantage, low/high demand, few/many clinicians, perfect/poor alert sensitivity, and zero/large reset burden. Verify expected monotonic directions and identify nonintuitive interactions.

### Output validation

Compare simulated distributions with local/pilot summaries, not only means. Assess PHQ-9 trajectory, uptake, engagement, completion, alert counts, review minutes, waiting-time distributions, throughput, abandonment, utilization, and incident/near-miss rates. Define acceptance thresholds before viewing final outputs.

## Decision rules and reporting

- Do not call the model calibrated unless a documented estimation procedure used empirical data.
- Do not call it validated solely because experts found outputs plausible.
- Report parameter distributions, correlations, disagreement, and changes from the v4.3 values.
- Rerun all primary, neutral, skeptical, and Sobol analyses after calibration.
- State whether conclusions, break-even thresholds, and parameter rankings changed.

## Deliverables

- completed `config/parameter_elicitation_template_v4.3.csv`;
- evidence dossier and search log;
- anonymized individual and pooled distributions;
- face-validation ratings and action log;
- calibrated configuration file and versioned code;
- internal/external validation report;
- revised manuscript and model card.
'''
    (DOCS_DIR / "STAKEHOLDER_ELICITATION_AND_FACE_VALIDATION_PROTOCOL_v4.3.md").write_text(text, encoding="utf-8")

    fields = ["parameter", "precise_quantity_definition", "population_setting", "unit_denominator", "evidence_summary", "expert_role", "lower_5th", "median_50th", "upper_95th", "distribution_family", "dependencies", "confidence_1_to_5", "rationale", "revised_lower", "revised_median", "revised_upper", "aggregation_method", "conflict_of_interest", "notes"]
    params = [p.name for p in INDIVIDUAL_PARAMETERS] + [p.name for p in SERVICE_PARAMETERS]
    with (CONFIG_DIR / "parameter_elicitation_template_v4.3.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for p in params:
            writer.writerow({"parameter": p})


def write_parameter_summary(ind: pd.DataFrame, svc: pd.DataFrame) -> None:
    status = {
        "individual_parameter_rows": int(len(ind)),
        "service_parameter_rows": int(len(svc)),
        "empirical_calibration_completed": False,
        "structured_multi_stakeholder_elicitation_completed": False,
        "external_face_validation_completed": False,
        "available_protocol": "docs/STAKEHOLDER_ELICITATION_AND_FACE_VALIDATION_PROTOCOL_v4.3.md",
    }
    (CONFIG_DIR / "parameter_documentation_status_v4.3.json").write_text(json.dumps(status, indent=2), encoding="utf-8")


def main() -> None:
    ind, svc = write_csvs()
    write_model_specification()
    write_validation_protocol()
    write_parameter_summary(ind, svc)
    print(f"Wrote {len(ind)} individual and {len(svc)} service parameter rows")


if __name__ == "__main__":
    main()
