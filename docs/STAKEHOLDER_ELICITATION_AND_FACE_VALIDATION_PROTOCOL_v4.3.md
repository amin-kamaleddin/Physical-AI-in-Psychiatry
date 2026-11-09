# Structured parameter elicitation and face-validation protocol (v4.3)

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
