# Novelty, statistical interpretation, and claim audit

**Search date:** 29 July 2026  
**Scope:** targeted, non-systematic search of psychiatric social-robot reviews, matched embodiment comparisons, mental-health service simulation, and simulation-statistics guidance. This is not a PRISMA review, meta-analysis, or legal priority opinion.

## Claims that should not be made

- Do not claim the first use of social robots in mental-health care.
- Do not claim the first physical robot-versus-screen comparison.
- Do not claim the first use of discrete-event simulation in mental-health services.
- Do not describe bootstrap intervals as empirical clinical confidence intervals or parameter-scenario proportions as posterior probabilities.
- Do not use “clinically significant,” “proved efficacy,” or “established safety” for synthetic outputs.

## Defensible novelty statement

> To our knowledge, after a targeted literature search updated 29 July 2026, we did not identify a prior psychiatric physical-AI study integrating a functionally matched screen comparator; patient-level symptom, retention, safety, and hidden-labor microsimulation; service-level discrete-event modeling with paired common demand streams; explicit physical near-miss and reset burdens; downtime and clinician-review break-even thresholds; bootstrap uncertainty and multiplicity-adjusted paired testing; broad parameter-scenario checks; warm-up diagnostics; and a machine-readable reproducibility package with editable figures.

This is a qualified **combination claim** and must retain “to our knowledge” plus the targeted-search qualification.

## Compelling result

> **An embodiment dividend is not necessarily a deployment dividend.**

Under the specified assumptions, the human-gated robot improves selected expected patient thresholds and high-acuity detection while reducing completion and increasing review labor, waiting, false alerts, and physical exposure. The resulting dual-gate standard is:

1. demonstrate incremental patient benefit against a functionally matched screen comparator; and
2. demonstrate operational noninferiority after reliability, access, human labor, and physical-safety burden are counted.

## Model-internal inferential separation

For the human-gated robot versus screen, 200 paired replications produced:

- response: +6.30 percentage points, 95% BCa CI +6.09 to +6.50;
- remission: +2.20 points, +2.09 to +2.31;
- completion: -5.42 points, -5.69 to -5.17;
- PHQ-9 change: -0.39 points, -0.41 to -0.38;
- clinician review: +4.38 minutes per participant, +4.35 to +4.40;
- physical near-misses: +0.55 per 100 participants, +0.51 to +0.58;
- service mean wait: +34.41 working minutes, +30.69 to +39.02;
- missed high-acuity cases: -10.85 points, -11.25 to -10.47;
- false alerts: +2.23 per 100 arrivals, +2.18 to +2.28.

For each of these primary contrasts, the Holm-adjusted paired sign-flip randomization p-value is <0.0001. Cohen's dz and MCSE are reported in the machine-readable contrast files and `docs/STATISTICAL_ANALYSIS.md`.

These intervals estimate the expected simulated contrast under fixed assumptions. The empirical range of single-replication missed-crisis contrasts crosses zero, illustrating that a precise expected mean does not guarantee the result of any one finite simulated trial.

Across 250 broad parameter scenarios, response favored the human-gated robot in 80.4% (resampling-stability interval 75.2%-84.8%), completion was unfavorable in 100%, review burden was higher in 100%, and physical near-miss burden was higher in 97.2%. These are scenario-stability summaries, not fitted probabilities.

## Break-even result

Mean-wait noninferiority occurred only with zero modeled day-level downtime and review no longer than eight minutes. Requiring the upper 95% bootstrap bound to remain nonpositive reduced the threshold to four minutes. At downtime of 6% or more, no tested review duration achieved mean noninferiority.

## Recommended language

Use:

- “conditional under the specified assumptions”
- “95% BCa confidence interval for expected simulation output”
- “empirical replication prediction range”
- “Holm-adjusted paired randomization test”
- “model-internal inferential separation”
- “decision-relevant trade-off”
- “hypothesis-generating break-even threshold”

Avoid:

- “clinically significant”
- “proves efficacy”
- “establishes safety”
- “probability the robot is superior”
- “first-ever simulation in mental health”

## Targeted search anchors

1. Fiske A, Henningsen P, Buyx A. *Your Robot Therapist Will See You Now*. J Med Internet Res. 2019;21(5):e13216.
2. Guemghar I, et al. *Social Robot Interventions in Mental Health Care and Their Outcomes, Barriers, and Facilitators*. JMIR Ment Health. 2022;9(4):e36094.
3. Kling M, et al. *Social robots in adult psychiatry: a summary of utilisation and impact*. Front Psychiatry. 2025;16:1506776.
4. Konijn EA, et al. *Examining the Potential of Social Robots to Increase Adherence in Internet-based CBT*. Int J Soc Robot. 2026;18:83.
5. Kim B, et al. *Use of discrete event simulation to improve a mental health clinic*. Gen Hosp Psychiatry. 2013;35(6):668-670.
6. Morris MD, et al. *Statistical methodology for simulation studies*. Stat Med. 2019;38:2074-2102.
7. Efron B, Tibshirani RJ. *An Introduction to the Bootstrap*. Chapman & Hall/CRC; 1993.
