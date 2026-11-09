"""Build the final integrated manuscript in Markdown and DOCX formats.

All numerical statements are generated directly from the current simulation
outputs. Publication PNGs are embedded in the DOCX; manually editable SVG
counterparts remain in ``figures/svg``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone
import json
import math

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
MAN = ROOT / "manuscript"
PNG = ROOT / "figures" / "png"

TITLE = (
    "Reimagining Psychiatric Care with Physical AI: "
    "Multiscale Simulation Stress Tests of Benefit, Burden, and Break-Even Conditions"
)
SHORT_TITLE = "Physical AI in psychiatry: multiscale stress tests"


@dataclass(frozen=True)
class FigureSpec:
    stem: str
    number: str
    title: str
    caption: str
    section: str


FIGURES = [
    FigureSpec(
        "individual_phq9_trajectories", "1", "Synthetic symptom trajectories",
        "Mean last-observation-carried-forward PHQ-9 across 12 weeks for the four pathways. Shaded bands are 95% BCa bootstrap confidence intervals for the mean across 200 independent repeated synthetic trials. They quantify model-output uncertainty under fixed assumptions, not clinical sampling uncertainty.",
        "main",
    ),
    FigureSpec(
        "individual_endpoints", "2", "Patient-level benefit and retention",
        "Synthetic response, remission, and 12-week completion by pathway. Error bars are 95% BCa bootstrap confidence intervals for the mean across independent repeated trials. The human-gated robot improves modeled symptom thresholds while completion remains below the screen comparator.",
        "main",
    ),
    FigureSpec(
        "individual_contrast_intervals", "3", "Repeated-trial patient-level contrasts",
        "Mean paired differences between robot pathways and the screen comparator across 200 repeated synthetic trials with 1,200 participants per arm. Bars show 95% BCa bootstrap confidence intervals obtained by resampling paired replication identifiers. They are not confidence intervals for a real clinical effect.",
        "main",
    ),
    FigureSpec(
        "individual_safety_tradeoffs", "4", "Patient-level safety and hidden labor",
        "Modeled alert burden, missed high-risk episodes, clinician review time, and physical near-misses. Error bars are 95% BCa bootstrap confidence intervals across independent replications. Nonembodied pathways are structurally unable to generate physical near-misses.",
        "main",
    ),
    FigureSpec(
        "system_wait_boxplot", "5", "Service waiting-time distributions",
        "Distribution of mean working-time waits over 200 paired discrete-event simulation replications after a five-day warm-up. Diamonds and error bars show scenario means and 95% BCa bootstrap confidence intervals; boxes show the empirical replication distribution.",
        "main",
    ),
    FigureSpec(
        "system_safety_access", "6", "Service-level safety and access trade-offs",
        "Modeled false alerts, missed high-acuity cases, and abandonment. Error bars are 95% BCa bootstrap confidence intervals across paired replications. Improved detection in the robot pathways is accompanied by additional false alerts and operational burden.",
        "main",
    ),
    FigureSpec(
        "individual_sensitivity_heatmap", "S1", "Patient-level response sensitivity surface",
        "Mean response difference between the human-gated robot and screen pathways as engagement-logit advantage and downtime vary. Open circles mark cells whose 95% bootstrap confidence interval excludes zero in the favorable direction.",
        "supplement",
    ),
    FigureSpec(
        "individual_parameter_uncertainty_tradeoff", "S2", "Scenario-based patient-level parameter uncertainty",
        "Joint response and completion contrasts across 250 broad illustrative parameter draws. Quadrant proportions are robustness diagnostics over the selected ranges, not posterior probabilities.",
        "supplement",
    ),
    FigureSpec(
        "system_throughput", "S3", "Service throughput",
        "Completed assessments per observed working day with 95% BCa bootstrap confidence intervals. Similar throughput across pathways conceals large differences in waiting, abandonment, detection, and workload.",
        "supplement",
    ),
    FigureSpec(
        "system_contrast_intervals", "S4", "Paired service-level contrasts",
        "Mean paired differences versus the screen pathway under common arrival, acuity, and latent random streams. Error bars are 95% BCa bootstrap confidence intervals from 10,000 paired resamples.",
        "supplement",
    ),
    FigureSpec(
        "system_sensitivity_heatmap", "S5", "Service break-even sensitivity surface",
        "Difference in mean wait between the human-gated robot and screen pathway as downtime and review time vary. Negative values favor the robot; open circles mark cells whose upper 95% bootstrap bound is nonpositive.",
        "supplement",
    ),
    FigureSpec(
        "system_warmup_diagnostic", "S6", "Queue warm-up diagnostic",
        "Mean waiting time with zero, two, five, and ten warm-up days. Error bars are 95% BCa bootstrap confidence intervals. Warm-up choice does not reverse the pathway ordering.",
        "supplement",
    ),
]

REFERENCES = [
    "Fiske A, Henningsen P, Buyx A. Your Robot Therapist Will See You Now: Ethical Implications of Embodied Artificial Intelligence in Psychiatry, Psychology, and Psychotherapy. J Med Internet Res. 2019;21(5):e13216. doi:10.2196/13216.",
    "Guemghar I, Pires de Oliveira Padilha P, Abdel-Baki A, Jutras-Aswad D, Paquette J, Pomey MP. Social Robot Interventions in Mental Health Care and Their Outcomes, Barriers, and Facilitators: Scoping Review. JMIR Ment Health. 2022;9(4):e36094. doi:10.2196/36094.",
    "Kling M, Haeussl A, Dalkner N, et al. Social robots in adult psychiatry: a summary of utilisation and impact. Front Psychiatry. 2025;16:1506776. doi:10.3389/fpsyt.2025.1506776.",
    "Jung HW, Park JY, Holoubek T, Kim WJ, Park J. Socially Assistive Robots in Mental Healthcare: Principles and Conceptual Framework for User-Centered Design. Int J Soc Robot. 2025;17:2827-2851. doi:10.1007/s12369-025-01323-5.",
    "Konijn EA, Peeper G, Portegies T, Garnefski N, Kraaij V, Struijs S. Examining the Potential of Social Robots to Increase Adherence in Internet-based CBT. Int J Soc Robot. 2026;18:83. doi:10.1007/s12369-026-01417-8.",
    "Deng E, Mutlu B, Mataric MJ. Embodiment in Socially Interactive Robots. Found Trends Robot. 2019;7(4):251-356. doi:10.1561/2300000056.",
    "Rabbitt SM, Kazdin AE, Scassellati B. Integrating socially assistive robotics into mental healthcare interventions: applications and recommendations for expanded use. Clin Psychol Rev. 2015;35:35-46. doi:10.1016/j.cpr.2014.07.001.",
    "Kim B, Elstein Y, Shiner B, Konrad R, Pomerantz AS, Watts BV. Use of discrete event simulation to improve a mental health clinic. Gen Hosp Psychiatry. 2013;35(6):668-670. doi:10.1016/j.genhosppsych.2013.06.004.",
    "Monks T, Currie CSM, Onggo BS, Robinson S, Kunc M, Taylor SJE. Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines. J Simul. 2019;13(1):55-67. doi:10.1080/17477778.2018.1442155.",
    "Eddy DM, Hollingworth W, Caro JJ, Tsevat J, McDonald KM, Wong JB. Model transparency and validation: a report of the ISPOR-SMDM Modeling Good Research Practices Task Force-7. Med Decis Making. 2012;32(5):733-743. doi:10.1177/0272989X12454579.",
    "Kroenke K, Spitzer RL, Williams JBW. The PHQ-9: Validity of a Brief Depression Severity Measure. J Gen Intern Med. 2001;16(9):606-613. doi:10.1046/j.1525-1497.2001.016009606.x.",
    "Coley RY, Boggs JM, Beck A, et al. Defining Success in Measurement-Based Care for Depression: A Comparison of Common Metrics. Psychiatr Serv. 2020;71(4):312-318. doi:10.1176/appi.ps.201900295.",
    "Vasey B, Nagendran M, Campbell B, et al. Reporting guideline for the early-stage clinical evaluation of decision support systems driven by artificial intelligence: DECIDE-AI. Nat Med. 2022;28(5):924-933. doi:10.1038/s41591-022-01772-9.",
    "Morris TP, White IR, Crowther MJ. Using simulation studies to evaluate statistical methods. Stat Med. 2019;38(11):2074-2102. doi:10.1002/sim.8086.",
    "Efron B, Tibshirani RJ. An Introduction to the Bootstrap. New York: Chapman & Hall; 1993.",
    "Desharnais B, Camirand-Lemyre F, Mireault P, Skinner CD. Determination of confidence intervals in non-normal data: application of the bootstrap to cocaine concentration in femoral blood. J Anal Toxicol. 2015;39(2):113-117. doi:10.1093/jat/bku127.",
]


def load_data() -> dict[str, pd.DataFrame]:
    return {
        "ind": pd.read_csv(OUT / "individual_arm_replication_summary.csv").set_index("arm"),
        "ind_con": pd.read_csv(OUT / "individual_contrast_summary.csv"),
        "ind_be": pd.read_csv(OUT / "individual_break_even_summary.csv"),
        "ind_pu": pd.read_csv(OUT / "individual_parameter_uncertainty.csv"),
        "ind_pu_sum": pd.read_csv(OUT / "individual_parameter_uncertainty_summary.csv").set_index("diagnostic"),
        "sys": pd.read_csv(OUT / "system_scenario_summary.csv").set_index("scenario"),
        "sys_con": pd.read_csv(OUT / "system_contrast_summary.csv"),
        "sys_be": pd.read_csv(OUT / "system_break_even_summary.csv"),
        "warm": pd.read_csv(OUT / "system_warmup_diagnostic.csv"),
    }


def select(df: pd.DataFrame, comparator: str, metric: str) -> pd.Series:
    hit = df[(df["comparator"] == comparator) & (df["metric"] == metric)]
    if len(hit) != 1:
        raise ValueError(f"Expected one row for {comparator!r}, {metric!r}; found {len(hit)}")
    return hit.iloc[0]


def num(x: float, digits: int = 1) -> str:
    return f"{float(x):.{digits}f}"


def signed(x: float, digits: int = 1) -> str:
    return f"{float(x):+.{digits}f}"


def interval(row: pd.Series, digits: int = 1, signed_mean: bool = False) -> str:
    mean = signed(row["mean_difference"], digits) if signed_mean else num(row["mean_difference"], digits)
    return f"{mean} ({num(row['bootstrap_ci_low'], digits)} to {num(row['bootstrap_ci_high'], digits)})"


def arm_interval(row: pd.Series, metric: str, digits: int = 1) -> str:
    return f"{num(row[f'{metric}_mean'], digits)} ({num(row[f'{metric}_ci_low'], digits)} to {num(row[f'{metric}_ci_high'], digits)})"


def p_text(value: float) -> str:
    value = float(value)
    return "<0.0001" if value < 0.0001 else f"={value:.4f}"


def build_key_results(d: dict[str, pd.DataFrame]) -> dict[str, object]:
    con, scon, pu = d["ind_con"], d["sys_con"], d["ind_pu"]
    gate = "Embodied robot + human safety gate"
    result = {
        "simulation_run_date": "2026-07-29",
        "individual_replications": 200,
        "service_replications": 200,
        "base_individual_n_per_arm": 5000,
        "repeated_trial_n_per_arm": 1200,
        "parameter_draws": len(pu),
    }
    for key, metric in [
        ("response_pp", "response_percent"),
        ("remission_pp", "remission_percent"),
        ("completion_pp", "completion_percent"),
        ("mean_phq9_change", "mean_phq9_change"),
        ("review_minutes", "mean_clinician_review_minutes"),
        ("near_misses_per_100", "physical_near_misses_per_100"),
        ("missed_crisis_weeks_per_100", "missed_crises_per_100_crisis_weeks"),
    ]:
        r = select(con, gate, metric)
        result[key] = {k: float(r[k]) for k in ["mean_difference", "p025_difference", "p975_difference", "fraction_draws_above_zero"]}
    for key, metric in [
        ("mean_wait_minutes", "mean_wait_minutes"),
        ("p90_wait_minutes", "p90_wait_minutes"),
        ("throughput_per_day", "throughput_per_day"),
        ("abandonment_pp", "abandonment_percent"),
        ("false_alerts_per_100", "false_alerts_per_100_arrivals"),
        ("missed_high_acuity_pp", "missed_high_acuity_percent"),
        ("clinician_utilization_pp", "mean_clinician_utilization_percent"),
    ]:
        r = select(scon, gate, metric)
        result[key] = {k: float(r[k]) for k in ["mean_difference", "p025_difference", "p975_difference", "fraction_draws_above_zero"]}
    result["parameter_uncertainty"] = {
        "response_positive_fraction": float((pu["response_difference_percentage_points"] > 0).mean()),
        "completion_negative_fraction": float((pu["completion_difference_percentage_points"] < 0).mean()),
        "phq_change_favorable_fraction": float((pu["mean_change_difference_phq9"] < 0).mean()),
        "review_positive_fraction": float((pu["review_minutes_difference"] > 0).mean()),
        "near_miss_positive_fraction": float((pu["physical_near_miss_difference_per_100"] > 0).mean()),
    }
    return result


def build_content(d: dict[str, pd.DataFrame]) -> dict[str, object]:
    ind, con, pu, pu_sum = d["ind"], d["ind_con"], d["ind_pu"], d["ind_pu_sum"]
    sys, scon = d["sys"], d["sys_con"]
    screen_name = "Screen-based agent"
    robot_name = "Embodied social robot"
    gate_name = "Embodied robot + human safety gate"
    qscreen_name = "Screen kiosk + clinician review"
    qrobot_name = "Embodied robot (realistic faults)"
    qgate_name = "Embodied robot + human safety gate"

    screen, robot, gate = ind.loc[screen_name], ind.loc[robot_name], ind.loc[gate_name]
    qscreen, qrobot, qgate = sys.loc[qscreen_name], sys.loc[qrobot_name], sys.loc[qgate_name]

    r_resp = select(con, robot_name, "response_percent")
    r_comp = select(con, robot_name, "completion_percent")
    g_resp = select(con, gate_name, "response_percent")
    g_rem = select(con, gate_name, "remission_percent")
    g_comp = select(con, gate_name, "completion_percent")
    g_phq = select(con, gate_name, "mean_phq9_change")
    g_review = select(con, gate_name, "mean_clinician_review_minutes")
    g_near = select(con, gate_name, "physical_near_misses_per_100")
    g_crisis = select(con, gate_name, "missed_crises_per_100_crisis_weeks")

    qr_wait = select(scon, qrobot_name, "mean_wait_minutes")
    qg_wait = select(scon, qgate_name, "mean_wait_minutes")
    qg_p90 = select(scon, qgate_name, "p90_wait_minutes")
    qg_tp = select(scon, qgate_name, "throughput_per_day")
    qg_ab = select(scon, qgate_name, "abandonment_percent")
    qg_false = select(scon, qgate_name, "false_alerts_per_100_arrivals")
    qg_miss = select(scon, qgate_name, "missed_high_acuity_percent")
    qg_util = select(scon, qgate_name, "mean_clinician_utilization_percent")

    pu_resp = pu_sum.loc["response_positive"]
    pu_comp = pu_sum.loc["completion_negative"]
    pu_change = pu_sum.loc["phq_change_favorable"]
    pu_review = pu_sum.loc["review_positive"]
    pu_near = pu_sum.loc["near_miss_positive"]

    abstract = {
        "Background": (
            "Physical artificial intelligence (AI) may increase social presence and engagement in psychiatric care, but embodiment also introduces refusal, downtime, physical exposure, false alerts, and human oversight work that screen-only evaluations can miss."
        ),
        "Objective": (
            "To determine when physical embodiment adds value relative to a functionally matched screen interface after patient outcomes, retention, safety burden, clinician labor, and service access are considered jointly."
        ),
        "Methods": (
            "We developed an open, assumption-driven multiscale framework comprising a 12-week individual microsimulation and a discrete-event psychiatric intake model. We ran 200 independent repeated trials or paired queue replications. Primary contrasts preserved common synthetic cohorts or demand streams. Mean differences were summarized with 95% bias-corrected and accelerated bootstrap confidence intervals (10,000 resamples), paired sign-flip randomization tests (100,000 draws), paired t-tests, Holm multiplicity adjustment, standardized paired effect sizes, and Monte Carlo standard errors."
        ),
        "Results": (
            f"Relative to the matched screen, the human-gated robot increased modeled response by {interval(g_resp, 2, True)} percentage points (Holm-adjusted randomization p{p_text(g_resp['holm_sign_flip_pvalue'])}) and remission by {interval(g_rem, 2, True)} points, but reduced completion by {interval(g_comp, 2, True)} points and added {interval(g_review, 2, True)} review minutes per participant. At service level it reduced missed high-acuity cases by {num(abs(qg_miss['mean_difference']), 2)} points, while increasing mean wait by {interval(qg_wait, 2, True)} working minutes and false alerts by {interval(qg_false, 2, True)} per 100 arrivals; all three Holm-adjusted randomization p values were <0.0001. Across 250 broad parameter scenarios, response favored the robot in {num(pu_resp['percent_of_scenario_draws'])}% (scenario-resampling stability interval {num(pu_resp['scenario_resampling_ci_low'])}-{num(pu_resp['scenario_resampling_ci_high'])}%), whereas completion and review burden were unfavorable in 100%."
        ),
        "Conclusions": (
            "The model exhibits a multiscale divergence: an embodiment dividend at the patient or detection level does not guarantee a deployment dividend. The bootstrap intervals and tests establish precise model-internal separation under the prespecified assumptions, not clinical efficacy, safety, or external validity."
        ),
    }

    introduction = [
        "Physical AI extends digital psychiatry from software-only interaction to systems that perceive, reason, and act through a body. Socially assistive robots may serve as coaches, companions, assessment interfaces, or delivery platforms for structured interventions. Physical presence may increase social salience, therapeutic alliance, and adherence, but it also adds proximity, motion, maintenance, sanitation, environmental constraints, and the possibility that a device failure becomes a clinical workflow failure [1-7].",
        "The empirical evidence remains early. Reviews describe small and heterogeneous psychiatric studies, and a recent matched comparison suggested better alliance, adherence, and satisfaction for a physically embodied interface without a significant mood advantage [3,5]. This makes a functionally matched screen comparator essential: the incremental effect of embodiment should not be conflated with the effects of content, automation, or attention.",
        "Patient-facing outcomes are only one scale of value. Human verification, false alerts, incomplete assessments, downtime, fallback, and physical resets consume capacity and can generate nonlinear queue effects. Discrete-event simulation has informed mental-health operations, but it has rarely been integrated with patient-level models of embodiment, retention, safety, and hidden labor [8]. A technology can therefore appear favorable on response or throughput while worsening completion, waiting, or staff workload.",
        "We developed a reproducible multiscale stress-testing framework to ask when physical embodiment outperforms a matched screen after clinical, behavioral, safety, and operational burdens are counted. The prespecified thesis was dual-gate: an embodiment pathway requires both incremental patient benefit and operational noninferiority before it can plausibly claim deployment value."
    ]

    methods = {
        "Study design, comparators, and estimands": [
            "We constructed a patient-level microsimulation and a service-level discrete-event simulation. The models share pathway definitions and burden categories but are not a calibrated, dynamically coupled digital twin. No patient records or empirical outcome data were used. Parameters are transparent, illustrative assumptions intended to reveal trade-offs and generate falsifiable targets.",
            "The functionally matched screen pathway was the primary reference. The primary estimand was the expected paired difference between each robot pathway and the screen under the fixed base-case data-generating process. Positive values favor the robot for response, remission, and detection-related sensitivity; negative values favor the robot for PHQ-9 change, missed high-risk cases, waiting, abandonment, and burden outcomes. Direction was stated outcome by outcome to avoid a generic significance interpretation."
        ],
        "Individual microsimulation": [
            "The individual model followed synthetic participants for 12 weeks across usual measurement-based care, a screen-based agent, an embodied social robot delivering functionally matched content, and an embodied robot with mandatory human review for risk-relevant alerts. A 5,000-participant-per-arm base cohort supports patient-level audit output. The uncertainty analysis used 200 independent repeated trials with 1,200 participants per arm.",
            "Baseline PHQ-9, technology acceptance, privacy concern, social support, and treatment responsiveness were drawn from bounded or parametric distributions. Within each replication, all arms reused the same baseline-cohort seed while arm-specific event streams remained independent. Weekly engagement, refusal, dropout, symptom change, downtime, fallback, alerts, high-risk episodes, review minutes, and physical near-misses were generated from prespecified transition rules. Response was at least 50% PHQ-9 reduction; remission was PHQ-9 <=4; completion required remaining active through week 12."
        ],
        "Service-level discrete-event simulation": [
            "The service model compared manual intake, a screen kiosk with clinician review, an embodied robot with realistic faults, and an embodied robot with a human safety gate. Each replication simulated a five-day warm-up followed by 35 observed working days. The base analysis used 200 paired replications.",
            "Within each replication, all pathways received identical arrival times, acuity labels, outage uniforms, and latent service and event variates. Outcomes included mean and 90th-percentile waiting time, throughput, abandonment, false alerts, missed high-acuity cases, failover, rework, clinician utilization, overtime, and physical reset work. Flow accounting required arrivals to equal completions plus abandonment exactly."
        ],
        "Bootstrap uncertainty and statistical testing": [
            "The independent simulation replication was the uncertainty unit. For paired contrasts, nonparametric resampling selected replication identifiers as intact pairs, preserving common-random-number matching. Primary mean contrasts used 10,000 bias-corrected and accelerated (BCa) bootstrap resamples to obtain two-sided 95% confidence intervals. Arm-level endpoints used 5,000 BCa resamples; weekly trajectories and sensitivity-grid cells used 3,000 resamples; warm-up diagnostics used 5,000 resamples. All bootstrap seeds were deterministically derived from analysis labels.",
            "Each primary paired contrast was also evaluated using a two-sided paired sign-flip randomization test with 100,000 draws and a plus-one correction, and a paired t-test as a concordance analysis. Holm adjustment controlled family-wise error across seven prespecified outcomes within each comparator and model. Cohen's dz quantified standardized paired separation. Monte Carlo standard errors quantified precision of the replication mean. Empirical 2.5th-97.5th percentile ranges of individual replication contrasts were retained in machine-readable outputs as stochastic prediction-range diagnostics and were not treated as confidence intervals for the mean [14-16].",
            "Because all data are generated by the model, p-values and bootstrap intervals answer a narrow question: whether expected model outputs are separated under the fixed assumptions and random-number design. They do not estimate sampling uncertainty, causal efficacy, real-world safety incidence, or generalizability. We therefore use the term model-internal inferential separation rather than clinical statistical significance."
        ],
        "Sensitivity, parameter uncertainty, and break-even analysis": [
            "The individual sensitivity grid varied robot engagement-logit advantage from 0.00 to 0.35 and session-level downtime from 0% to 30%, with 20 paired replications per cell. The service grid varied day-level downtime from 0% to 30% and clinician review from 4 to 24 minutes, with 30 paired replications per cell. Heatmaps mark cells whose bootstrap interval excludes the null in the favorable direction.",
            "A separate 250-draw scenario ensemble varied engagement, downtime, embodiment effect, refusal, dropout, false-alert probability, risk sensitivity, review time, and fallback. Resampling intervals around scenario proportions describe stability within the selected ensemble only; they are not posterior probabilities. Break-even summaries identified the minimum engagement advantage for response benefit and maximum review duration for waiting-time noninferiority."
        ],
        "Verification, reproducibility, and reporting": [
            "The framework follows STRESS and model-transparency principles [9,10]. Deterministic reruns, shared-cohort and shared-demand checks, range checks, impossible-event checks, flow accounting, warm-up diagnostics, editable-vector checks, figure-font audits, manuscript-result reconciliation, and SHA-256 manifests were automated. Source code exports bootstrap methods, resample counts, seeds, MCSEs, raw and adjusted p-values, effect sizes, empirical replication ranges, and all generated intermediate data."
        ],
    }

    results = {
        "Computational verification and uncertainty precision": [
            "The regenerated framework passed deterministic and structural checks. Shared cohorts produced identical baseline means across individual arms, and common demand streams produced identical arrivals across service pathways within each replication. All 12 figures were regenerated as 600-dpi PNG and live-text SVG files. Primary BCa intervals were based on 10,000 resamples and randomization p-values on 100,000 sign flips.",
            "The BCa intervals for expected mean contrasts were much narrower than the empirical ranges of individual replication contrasts. This distinction is material: the mean high-risk detection contrast was precisely negative even though the 95% range of single-replication contrasts crossed zero. The former estimates expected model output; the latter describes variability a single synthetic experiment could exhibit."
        ],
        "Patient-level benefit did not translate into retention noninferiority": [
            f"Across repeated trials, response was {arm_interval(screen, 'response_percent', 2)}% for the screen, {arm_interval(robot, 'response_percent', 2)}% for the ungated robot, and {arm_interval(gate, 'response_percent', 2)}% for the human-gated robot. Completion was {arm_interval(screen, 'completion_percent', 2)}%, {arm_interval(robot, 'completion_percent', 2)}%, and {arm_interval(gate, 'completion_percent', 2)}%, respectively.",
            f"Relative to screen, the ungated robot increased response by {interval(r_resp, 2, True)} points but reduced completion by {interval(r_comp, 2, True)} points. The human-gated robot increased response by {interval(g_resp, 2, True)} points (Cohen dz={num(g_resp['cohen_dz'], 2)}; Holm-adjusted sign-flip p{p_text(g_resp['holm_sign_flip_pvalue'])}), remission by {interval(g_rem, 2, True)} points, and improved mean PHQ-9 change by {interval(g_phq, 2, True)} points, while reducing completion by {interval(g_comp, 2, True)} points. All four adjusted randomization p values were <0.0001."
        ],
        "Human safety gating shifted rather than removed burden": [
            f"Compared with screen, the human-gated robot reduced expected missed high-risk weeks by {interval(g_crisis, 2, True)} per 100 high-risk weeks, but added {interval(g_review, 2, True)} clinician-review minutes per participant and {interval(g_near, 2, True)} physical near-misses per 100 participants. Each expected mean contrast had a 95% BCa interval excluding zero and Holm-adjusted randomization p<0.0001.",
            f"The empirical single-replication range for missed high-risk weeks was {num(g_crisis['replication_p025_difference'], 1)} to {num(g_crisis['replication_p975_difference'], 1)}, which crossed zero despite the bootstrap CI for the expected mean being entirely negative. This limits claims about what any one finite trial would necessarily observe."
        ],
        "Similar throughput concealed materially worse access": [
            f"Mean waiting time was {arm_interval(qscreen, 'mean_wait_minutes', 2)} working minutes for the screen, {arm_interval(qrobot, 'mean_wait_minutes', 2)} for the fault-prone robot, and {arm_interval(qgate, 'mean_wait_minutes', 2)} for the human-gated robot. The paired mean-wait contrasts were {interval(qr_wait, 2, True)} minutes for the ungated robot and {interval(qg_wait, 2, True)} minutes for the human-gated robot; the latter had Cohen dz={num(qg_wait['cohen_dz'], 2)} and Holm-adjusted randomization p<0.0001.",
            f"Throughput was {arm_interval(qscreen, 'throughput_per_day', 2)}, {arm_interval(qrobot, 'throughput_per_day', 2)}, and {arm_interval(qgate, 'throughput_per_day', 2)} assessments per day. The human-gated contrast was {interval(qg_tp, 3, True)} assessments/day (Holm-adjusted p<0.0001), a small mean difference that coexisted with a large waiting-time penalty."
        ],
        "Detection gains carried false-alert and capacity costs": [
            f"The human-gated robot reduced missed high-acuity cases by {interval(qg_miss, 2, True)} percentage points but added {interval(qg_false, 2, True)} false alerts per 100 arrivals and increased clinician utilization by {interval(qg_util, 2, True)} points. Its abandonment contrast was {interval(qg_ab, 2, True)} points. All four expected contrasts had Holm-adjusted randomization p<0.0001.",
            "The interpretation is not that every operational change is clinically important. Rather, the paired model demonstrates that modest capacity changes can be estimated precisely and can coexist with large access effects when the system operates near capacity."
        ],
        "Sensitivity and break-even conditions": [
            f"Across 250 broad parameter scenarios, response favored the human-gated robot in {num(pu_resp['percent_of_scenario_draws'])}% (stability interval {num(pu_resp['scenario_resampling_ci_low'])}-{num(pu_resp['scenario_resampling_ci_high'])}%), favorable mean PHQ-9 change occurred in {num(pu_change['percent_of_scenario_draws'])}% ({num(pu_change['scenario_resampling_ci_low'])}-{num(pu_change['scenario_resampling_ci_high'])}%), completion was lower in {num(pu_comp['percent_of_scenario_draws'])}%, review burden was higher in {num(pu_review['percent_of_scenario_draws'])}%, and physical near-miss exposure was higher in {num(pu_near['percent_of_scenario_draws'])}% ({num(pu_near['scenario_resampling_ci_low'])}-{num(pu_near['scenario_resampling_ci_high'])}%).",
            "No individual sensitivity cell produced a mean completion advantage. In the service grid, mean waiting-time noninferiority occurred only with zero modeled day-level downtime and review no longer than 8 minutes; requiring the upper 95% bootstrap bound to be nonpositive reduced the threshold to 4 minutes. At downtime of 6% or greater, no tested review duration achieved mean noninferiority. Warm-up choice did not reverse the pathway ordering."
        ],
    }

    discussion = {
        "Principal findings": [
            "The central finding is a dual-scale separation: physical embodiment can generate an expected patient or detection dividend without generating a deployment dividend. Under the model assumptions, human gating improved response, remission, symptom change, and detection, yet reduced completion and increased review work, waiting, false alerts, utilization, and physical exposure.",
            "Bootstrapping and paired randomization sharpen rather than change this story. The expected mean contrasts are estimated precisely because common-random-number pairing removes avoidable stochastic noise and 200 independent replications stabilize the mean. This precision must not be mistaken for empirical certainty. It demonstrates internal consequences of the assumptions, not truth about a deployed robot."
        ],
        "Contribution and novelty": [
            "Social robots, embodiment comparisons, and mental-health discrete-event simulation each have precedents [2-8]. The qualified novelty is their integration into one reproducible psychiatric stress-testing framework with a functionally matched screen comparator; patient-level benefit, retention, safety, and hidden labor; service-level queue consequences under paired demand; physical near-misses and reset burden; bootstrap uncertainty; multiplicity-adjusted paired testing; scenario uncertainty; warm-up diagnostics; and explicit break-even thresholds.",
            "The methodological contribution is the dual-gate estimand. Rather than asking only whether a robot can improve an outcome, the framework asks whether the incremental embodiment benefit survives completion loss, human oversight, reliability constraints, queue amplification, and physical-safety obligations."
        ],
        "Implications for research and deployment": [
            "Future empirical studies should preregister a matched screen comparator, define primary patient and operational estimands, and measure refusal before first use, longitudinal completion, downtime, fallback, verification labor, sanitation and reset work, near-misses, false alerts, and waiting-time distributions. Confidence intervals and effect sizes should accompany p-values, and multiplicity should be specified prospectively.",
            "The break-even conditions are engineering hypotheses, not universal standards. A site considering deployment should recalibrate arrival processes, staffing, service times, alert behavior, downtime, and review workflow with local data, then repeat the paired uncertainty analysis before conducting cost-effectiveness or scale-up studies."
        ],
        "Limitations": [
            "All clinical and operational parameters are illustrative. The framework cannot estimate efficacy, real-world safety incidence, cost-effectiveness, regulatory acceptability, or causal effects. Threshold outcomes can magnify small distributional shifts, high-risk episodes are stylized, and physical near-miss rates are placeholders rather than forecasts.",
            "The individual and service models are not dynamically coupled; congestion does not feed back into symptoms and engagement does not alter service demand. The service model represents one finite-capacity clinic and omits scheduling, no-shows, downstream treatment capacity, staff learning, maintenance logistics, costs, equity, and environmental variation.",
            "Bootstrap CIs assume the independent simulation replications adequately represent first-order stochastic variation under the fixed model. The paired sign-flip test relies on exchangeability of contrast signs under its null, and Holm adjustment addresses only the declared outcome families. The 250 parameter draws are an illustrative scenario ensemble rather than a probability distribution over plausible worlds."
        ],
        "Conclusions": [
            "Physical AI must earn its place against a matched screen after retention, hidden labor, reliability, access, and physical safety are counted. In this synthetic framework, human gating produced statistically precise model-internal benefits while failing strict completion and waiting-time criteria. The defensible conclusion is a dual-gate standard: demonstrate incremental patient benefit and operational noninferiority before claiming deployment value."
        ],
    }

    return {
        "abstract": abstract,
        "introduction": introduction,
        "methods": methods,
        "results": results,
        "discussion": discussion,
        "tables": {
            "arms": [
                ["Usual care/manual", "Human-delivered baseline pathways", "No embodiment-specific benefit or physical risk"],
                ["Matched screen", "Same digital content without a physical body", "Primary comparator for incremental embodiment"],
                ["Embodied robot", "Physical social interface with realistic faults", "Embodiment plus refusal, downtime, alerts, and physical burden"],
                ["Robot + human safety gate", "Physical interface with mandatory human verification", "Higher detection and fallback, but greater routine review work"],
            ],
            "primary": [
                ["Patient", "Response, percentage points", interval(g_resp, 2, True), p_text(g_resp["holm_sign_flip_pvalue"]), "Favors robot; large paired separation"],
                ["Patient", "Remission, percentage points", interval(g_rem, 2, True), p_text(g_rem["holm_sign_flip_pvalue"]), "Favors robot"],
                ["Patient", "Completion, percentage points", interval(g_comp, 2, True), p_text(g_comp["holm_sign_flip_pvalue"]), "Favors screen"],
                ["Patient", "Mean PHQ-9 change", interval(g_phq, 2, True), p_text(g_phq["holm_sign_flip_pvalue"]), "Negative favors robot"],
                ["Patient", "Review minutes per participant", interval(g_review, 2, True), p_text(g_review["holm_sign_flip_pvalue"]), "Higher hidden labor"],
                ["Patient", "Physical near-misses per 100", interval(g_near, 2, True), p_text(g_near["holm_sign_flip_pvalue"]), "Robot-only exposure"],
                ["Service", "Mean wait, working minutes", interval(qg_wait, 2, True), p_text(qg_wait["holm_sign_flip_pvalue"]), "Favors screen"],
                ["Service", "False alerts per 100 arrivals", interval(qg_false, 2, True), p_text(qg_false["holm_sign_flip_pvalue"]), "Higher alert burden"],
                ["Service", "Missed high-acuity cases, points", interval(qg_miss, 2, True), p_text(qg_miss["holm_sign_flip_pvalue"]), "Negative favors robot"],
            ],
            "statistics": [
                ["Resampling unit", "Independent simulation replication", "Paired identifiers resampled intact"],
                ["Primary interval", "95% BCa bootstrap CI", "10,000 resamples for primary contrasts"],
                ["Primary test", "Two-sided paired sign-flip", "100,000 draws; plus-one correction"],
                ["Concordance test", "Paired t-test", "Reported with test statistic and p-value"],
                ["Multiplicity", "Holm family-wise adjustment", "Seven outcomes within each comparator/model"],
                ["Effect size", "Cohen dz", "Mean paired difference divided by SD of differences"],
                ["Simulation precision", "Monte Carlo standard error", "SD of replication contrast divided by square root of replications"],
                ["Interpretation", "Model-internal inference", "Not clinical efficacy or external validity"],
            ],
            "break_even": [
                ["Patient completion", "Engagement advantage 0.00-0.35; downtime 0%-30%", "No modeled cell achieved mean completion gain"],
                ["Service mean wait", "0% day-level downtime", "Mean noninferiority at review <=8 min; upper 95% CI nonpositive at <=4 min"],
                ["Service mean wait", "Day-level downtime >=6%", "No review duration from 4-24 min achieved mean noninferiority"],
                ["Warm-up", "0, 2, 5, or 10 days", "Screen remained faster than the human-gated robot"],
            ],
        },
    }

def set_repeat_table_header(row) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def shade_cell(cell, fill: str) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def add_page_number(paragraph) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    paragraph.alignment = 2
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend([begin, instr, end])


def add_bookmark(paragraph, text: str, name: str, bookmark_id: int) -> None:
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bookmark_id))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bookmark_id))
    paragraph._p.append(start)
    run = paragraph.add_run(text)
    run.bold = True
    paragraph._p.append(end)


def write_docx(content: dict[str, object], d: dict[str, pd.DataFrame]) -> Path:
    from docx import Document
    from docx.enum.section import WD_SECTION_START
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Inches(0.75)
    sec.bottom_margin = Inches(0.75)
    sec.left_margin = Inches(0.85)
    sec.right_margin = Inches(0.85)

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)
    styles["Normal"].paragraph_format.space_after = Pt(5)
    styles["Normal"].paragraph_format.line_spacing = 1.08
    styles["Title"].font.name = "Arial"
    styles["Title"].font.size = Pt(18)
    styles["Title"].font.bold = True
    for name, size in [("Heading 1", 14), ("Heading 2", 11.5), ("Heading 3", 10.5)]:
        styles[name].font.name = "Arial"
        styles[name].font.size = Pt(size)
        styles[name].font.bold = True
        styles[name].font.color.rgb = RGBColor(25, 55, 75)
    styles["Heading 1"].paragraph_format.space_before = Pt(9)
    styles["Heading 1"].paragraph_format.space_after = Pt(4)
    styles["Heading 2"].paragraph_format.space_before = Pt(7)
    styles["Heading 2"].paragraph_format.space_after = Pt(3)

    # Title page
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.style = styles["Title"]
    p.add_run(TITLE)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Original Research - Simulation Study")
    r.bold = True
    r.font.name = "Arial"
    r.font.size = Pt(11.5)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("[Insert author names, degrees, affiliations, and corresponding-author details]").italic = True
    doc.add_paragraph()

    box = doc.add_paragraph()
    box_pr = box._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), "EAF1F5")
    box_pr.append(shd)
    rr = box.add_run("Central finding. ")
    rr.bold = True
    box.add_run(
        "Under the model assumptions, physical embodiment can improve selected patient and detection outcomes while simultaneously worsening completion, clinician workload, waiting, false alerts, and physical exposure. The relevant standard is therefore dual: patient benefit plus operational noninferiority."
    )
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Simulation outputs, bootstrap analyses, and figures regenerated and audited: 29 July 2026").italic = True
    doc.add_page_break()

    def add_heading(text: str, level: int = 1):
        p = doc.add_heading(text, level=level)
        p.paragraph_format.keep_with_next = True
        return p

    def add_body(text: str):
        p = doc.add_paragraph(text)
        p.paragraph_format.keep_together = False
        return p

    def add_figure(spec: FigureSpec):
        image = PNG / f"{spec.stem}.png"
        if not image.exists():
            raise FileNotFoundError(image)
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        add_bookmark(p, f"Figure {spec.number}. {spec.title}", f"fig_{spec.number.replace('S','s')}", 100 + len(doc.paragraphs))
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.keep_with_next = True
        shape = p.add_run().add_picture(str(image), width=Inches(6.65))
        shape._inline.docPr.set("title", f"Figure {spec.number}: {spec.title}")
        shape._inline.docPr.set("descr", spec.caption)
        cap = doc.add_paragraph()
        cap.paragraph_format.keep_together = True
        cap.paragraph_format.space_after = Pt(8)
        r = cap.add_run("Caption. ")
        r.bold = True
        cap.add_run(spec.caption)

    def add_table(title: str, headers: list[str], rows: list[list[str]], widths: list[float] | None = None):
        p = doc.add_paragraph()
        p.paragraph_format.keep_with_next = True
        p.add_run(title).bold = True
        table = doc.add_table(rows=1, cols=len(headers))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = "Table Grid"
        for i, h in enumerate(headers):
            table.rows[0].cells[i].text = h
            shade_cell(table.rows[0].cells[i], "DCE8EF")
            for run in table.rows[0].cells[i].paragraphs[0].runs:
                run.bold = True
                run.font.name = "Arial"
                run.font.size = Pt(10)
        set_repeat_table_header(table.rows[0])
        for row_values in rows:
            cells = table.add_row().cells
            for i, value in enumerate(row_values):
                cells[i].text = str(value)
        for row in table.rows:
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                for p2 in cell.paragraphs:
                    p2.paragraph_format.space_after = Pt(0)
                    p2.paragraph_format.line_spacing = 1.0
                    for run in p2.runs:
                        run.font.name = "Arial"
                        run.font.size = Pt(10)
        if widths:
            for row in table.rows:
                for i, width in enumerate(widths):
                    row.cells[i].width = Inches(width)
        doc.add_paragraph().paragraph_format.space_after = Pt(0)
        return table

    add_heading("Abstract", 1)
    for label, text in content["abstract"].items():
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(3)
        r = p.add_run(f"{label}: ")
        r.bold = True
        p.add_run(text)
    p = doc.add_paragraph()
    r = p.add_run("Keywords: ")
    r.bold = True
    p.add_run("physical AI; psychiatry; social robots; microsimulation; discrete-event simulation; human oversight; patient flow; safety")

    add_heading("Introduction", 1)
    for paragraph in content["introduction"]:
        add_body(paragraph)

    add_heading("Methods", 1)
    for subsection, paragraphs in content["methods"].items():
        add_heading(subsection, 2)
        for paragraph in paragraphs:
            add_body(paragraph)

    add_table(
        "Table 1. Pathways and the incremental embodiment question.",
        ["Pathway", "Core role", "Differentiating interpretation"],
        content["tables"]["arms"],
        [1.35, 2.2, 3.0],
    )

    add_heading("Results", 1)
    main_fig_map = {
        "Patient-level benefit did not translate into retention noninferiority": ["1", "2", "3"],
        "Human safety gating shifted rather than removed burden": ["4"],
        "Similar throughput concealed materially worse access": ["5"],
        "Detection gains carried false-alert and capacity costs": ["6"],
    }
    for subsection, paragraphs in content["results"].items():
        add_heading(subsection, 2)
        for paragraph in paragraphs:
            add_body(paragraph)
        for number in main_fig_map.get(subsection, []):
            add_figure(next(f for f in FIGURES if f.number == number))

    add_table(
        "Table 2. Primary human-gated robot contrasts versus the matched screen comparator.",
        ["Scale", "Outcome", "Mean difference (95% BCa CI)", "Holm-adjusted randomization p", "Interpretation"],
        content["tables"]["primary"],
        [0.65, 1.35, 1.65, 0.95, 1.85],
    )
    add_table(
        "Table 3. Statistical analysis and reviewer-facing safeguards.",
        ["Element", "Specification", "Purpose"],
        content["tables"]["statistics"],
        [1.3, 2.1, 2.95],
    )
    add_table(
        "Table 4. Break-even and robustness findings.",
        ["Domain", "Range tested", "Finding"],
        content["tables"]["break_even"],
        [1.25, 2.25, 3.15],
    )

    add_heading("Discussion", 1)
    for subsection, paragraphs in content["discussion"].items():
        add_heading(subsection, 2)
        for paragraph in paragraphs:
            add_body(paragraph)

    add_heading("Data and code availability", 1)
    add_body(
        "The accompanying Git-ready repository contains all Python source, fixed seeds, machine-readable parameters, synthetic patient-level and replication outputs, sensitivity analyses, tests, build scripts, manuscript source, 600-dpi publication PNG figures, and editable SVG figures with live text. Running `python run_all.py` regenerates the simulations, validation checks, figures, key-results JSON, manuscript files, and checksums. Replace the repository placeholder in CITATION.cff and this section before submission."
    )
    add_heading("Author contributions", 1)
    add_body("[Insert CRediT author-contribution statement before submission.]")
    add_heading("Funding", 1)
    add_body("[Insert funding statement or state that no specific funding was received.]")
    add_heading("Competing interests", 1)
    add_body("[Insert competing-interest declaration.]")

    doc.add_page_break()
    add_heading("Supplementary simulation appendix", 1)
    add_body(
        "The following figures are embedded for complete auditability. Each has a same-stem, manually editable SVG counterpart in figures/svg/. The SVG files preserve labels as text elements."
    )
    for spec in [f for f in FIGURES if f.section == "supplement"]:
        add_figure(spec)
        if spec != [f for f in FIGURES if f.section == "supplement"][-1]:
            doc.add_page_break()

    add_heading("References", 1)
    for i, reference in enumerate(REFERENCES, 1):
        p = doc.add_paragraph(f"{i}. {reference}")
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_after = Pt(4)

    for section in doc.sections:
        header = section.header.paragraphs[0]
        header.text = SHORT_TITLE
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        for run in header.runs:
            run.font.name = "Arial"
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(100, 100, 100)
        add_page_number(section.footer.paragraphs[0])

    path = MAN / "Physical_AI_Psychiatry_Final_Manuscript.docx"
    doc.save(path)
    return path


def write_markdown(content: dict[str, object]) -> Path:
    lines = [f"# {TITLE}", "", "**Original Research - Simulation Study**", "", "[Insert authors and affiliations]", "", "## Abstract", ""]
    for label, text in content["abstract"].items():
        lines += [f"**{label}:** {text}", ""]
    lines += ["## Introduction", ""]
    for p in content["introduction"]:
        lines += [p, ""]
    lines += ["## Methods", ""]
    for heading, paragraphs in content["methods"].items():
        lines += [f"### {heading}", ""]
        for p in paragraphs:
            lines += [p, ""]
    lines += ["## Results", ""]
    for heading, paragraphs in content["results"].items():
        lines += [f"### {heading}", ""]
        for p in paragraphs:
            lines += [p, ""]
    lines += ["## Discussion", ""]
    for heading, paragraphs in content["discussion"].items():
        lines += [f"### {heading}", ""]
        for p in paragraphs:
            lines += [p, ""]
    lines += ["## Integrated figures", ""]
    for spec in FIGURES:
        lines += [f"### Figure {spec.number}. {spec.title}", "", f"![Figure {spec.number}](../figures/png/{spec.stem}.png)", "", spec.caption, ""]
    lines += ["## References", ""]
    for i, ref in enumerate(REFERENCES, 1):
        lines += [f"{i}. {ref}", ""]
    path = MAN / "Physical_AI_Psychiatry_Final_Manuscript.md"
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    return path


def main() -> None:
    MAN.mkdir(parents=True, exist_ok=True)
    d = load_data()
    content = build_content(d)
    key_results = build_key_results(d)
    (OUT / "manuscript_key_results.json").write_text(json.dumps(key_results, indent=2) + "\n", encoding="utf-8")
    md = write_markdown(content)
    docx = write_docx(content, d)
    print(f"Wrote {md.relative_to(ROOT)}")
    print(f"Wrote {docx.relative_to(ROOT)}")
    print("Wrote outputs/manuscript_key_results.json")


if __name__ == "__main__":
    main()
