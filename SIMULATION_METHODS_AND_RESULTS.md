# Current simulation methods and results

This concise repository summary is subordinate to the data-driven manuscript and statistical report:

- `manuscript/Physical_AI_Psychiatry_Final_Manuscript.docx`
- `manuscript/Physical_AI_Psychiatry_Final_Manuscript.md`
- `docs/STATISTICAL_ANALYSIS.md`
- `outputs/statistical_analysis_summary.csv`
- `outputs/manuscript_key_results.json`

## Design

The framework combines a 12-week individual microsimulation and a service-level discrete-event intake model. Both compare a human-gated embodied pathway with a functionally matched screen pathway, alongside additional comparators.

The individual analysis uses a 5,000-participant-per-arm base case, 200 paired synthetic trials with 1,200 participants per arm, weekly bootstrap trajectories, a replicated sensitivity grid, and 250 broad parameter scenarios. The service analysis uses 200 paired replications, common synthetic demand streams, a five-day warm-up plus 35 observed working days, a replicated sensitivity grid, break-even analysis, and warm-up diagnostics.

The independent replication is the uncertainty unit. Primary expected mean contrasts use 10,000 BCa bootstrap resamples. Two-sided paired sign-flip tests use 100,000 draws with plus-one correction; paired t-tests are concordance analyses. Holm adjustment is applied within prespecified seven-outcome families, with Cohen's dz and MCSE reported.

## Headline human-gated-robot contrasts versus screen

### Individual model

- Response: +6.30 percentage points; 95% BCa CI +6.09 to +6.50.
- Remission: +2.20 points; +2.09 to +2.31.
- Completion: -5.42 points; -5.69 to -5.17.
- Mean PHQ-9 change: -0.39 points; -0.41 to -0.38, where negative favors the robot.
- Missed high-risk weeks: -10.26 per 100 high-risk weeks; -11.87 to -8.53.
- Clinician review: +4.38 minutes per participant; +4.35 to +4.40.
- Physical near-misses: +0.55 per 100 participants; +0.51 to +0.58.

All Holm-adjusted paired sign-flip p-values are <0.0001. The empirical single-replication range for missed high-risk weeks crosses zero, demonstrating the distinction between a confidence interval for expected model output and variability in any one finite simulated trial.

Across 250 broad parameter scenarios, response favored the robot in 80.4% (resampling-stability interval 75.2%-84.8%), completion was unfavorable in 100%, review burden was higher in 100%, and physical near-miss burden was higher in 97.2%.

### Service model

- Mean wait: +34.41 working minutes; 95% BCa CI +30.69 to +39.02.
- P90 wait: +102.24 minutes; +89.82 to +116.29.
- Throughput: -0.16 completed assessments/day; -0.21 to -0.13.
- Abandonment: +0.46 percentage points; +0.36 to +0.59.
- False alerts: +2.23 per 100 arrivals; +2.18 to +2.28.
- Missed high-acuity cases: -10.85 points; -11.25 to -10.47.
- Clinician utilization: +1.61 points; +1.51 to +1.69.

All Holm-adjusted paired sign-flip p-values are <0.0001.

Mean-wait noninferiority occurred only at zero day-level downtime with clinician review no longer than eight minutes. Requiring the upper 95% bootstrap confidence bound to be nonpositive reduced that threshold to four minutes. No tested review duration achieved mean-wait noninferiority at day-level downtime of 6% or more.

## Interpretation

The central result is a multiscale divergence: selected expected patient or detection gains can coexist with lower completion and worse labor, access, false-alert, and cyber-physical burden. This supports a dual-gate standard requiring both incremental patient benefit and operational noninferiority against a matched screen comparator.

All values are synthetic and conditional on the stated assumptions. Bootstrap intervals and adjusted p-values establish model-internal separation only; they are not clinical effect estimates, injury rates, diagnostic-performance estimates, or evidence of efficacy, safety, causality, external validity, or regulatory acceptability.
