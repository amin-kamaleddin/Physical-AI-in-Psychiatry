# Statistical analysis and uncertainty report

## Estimand and resampling unit

The primary estimand is the expected paired pathway difference under the fixed base-case data-generating assumptions. The independent simulation replication is the uncertainty unit. For paired comparisons, replication identifiers are resampled as intact pairs, preserving the common synthetic cohort or common demand stream.

## Primary uncertainty analysis

Primary contrasts use 10,000 nonparametric bias-corrected and accelerated (BCa) bootstrap resamples to obtain 95% confidence intervals for the mean simulation contrast. Monte Carlo standard errors are also reported. The empirical 2.5th-97.5th percentile range of individual replication contrasts is retained separately as a stochastic prediction-range diagnostic; it is not the confidence interval for the mean.

## Hypothesis tests and multiplicity

Each paired contrast is evaluated using a two-sided paired t-test and a two-sided paired sign-flip randomization test with 100,000 draws and a plus-one correction. The minimum attainable Monte Carlo p-value is therefore 1/100,001. The NumPy PCG64 generator is used; deterministic bootstrap and randomization seeds are exported for every primary contrast. Holm adjustment controls the family-wise error rate across the seven prespecified outcomes within each comparator and model. Cohen's dz describes standardized separation across paired replications. The randomization test is the primary robustness test because it does not require normal replication-level contrasts; the t-test is reported as a concordance analysis.

## Interpretation boundary

These CIs, p-values, and effect sizes refer only to stochastic uncertainty in expected model output under fixed synthetic assumptions. They are not estimates of clinical sampling uncertainty, efficacy, safety incidence, causal effects, or external validity. Small p-values can arise because the model is deliberately repeated many times; they should be described as model-internal inferential separation, not clinical statistical significance.

## Complete primary contrasts

| Scale | Comparator | Metric | Mean difference | 95% BCa bootstrap CI | Holm-adjusted sign-flip p | Cohen dz | MCSE |
|---|---|---|---:|---:|---:|---:|---:|
| Individual microsimulation | Embodied social robot | response_percent | 2.4008 | 2.1918 to 2.6133 | <0.0001 | 1.569 | 0.1082 |
| Individual microsimulation | Embodied social robot | remission_percent | 0.9404 | 0.8171 to 1.0612 | <0.0001 | 1.061 | 0.0627 |
| Individual microsimulation | Embodied social robot | completion_percent | -10.8017 | -11.0659 to -10.5371 | <0.0001 | -5.683 | 0.1344 |
| Individual microsimulation | Embodied social robot | mean_phq9_change | 0.0424 | 0.0259 to 0.0584 | <0.0001 | 0.359 | 0.0083 |
| Individual microsimulation | Embodied social robot | missed_crises_per_100_crisis_weeks | -7.1367 | -8.8459 to -5.4394 | <0.0001 | -0.577 | 0.8742 |
| Individual microsimulation | Embodied social robot | mean_clinician_review_minutes | 1.8473 | 1.8276 to 1.8672 | <0.0001 | 13.012 | 0.0100 |
| Individual microsimulation | Embodied social robot | physical_near_misses_per_100 | 0.5754 | 0.5456 to 0.6075 | <0.0001 | 2.584 | 0.0157 |
| Individual microsimulation | Embodied robot + human safety gate | response_percent | 6.2950 | 6.0929 to 6.4992 | <0.0001 | 4.241 | 0.1050 |
| Individual microsimulation | Embodied robot + human safety gate | remission_percent | 2.1979 | 2.0858 to 2.3108 | <0.0001 | 2.727 | 0.0570 |
| Individual microsimulation | Embodied robot + human safety gate | completion_percent | -5.4238 | -5.6896 to -5.1746 | <0.0001 | -2.997 | 0.1280 |
| Individual microsimulation | Embodied robot + human safety gate | mean_phq9_change | -0.3910 | -0.4061 to -0.3759 | <0.0001 | -3.549 | 0.0078 |
| Individual microsimulation | Embodied robot + human safety gate | missed_crises_per_100_crisis_weeks | -10.2557 | -11.8744 to -8.5334 | <0.0001 | -0.869 | 0.8349 |
| Individual microsimulation | Embodied robot + human safety gate | mean_clinician_review_minutes | 4.3752 | 4.3536 to 4.3962 | <0.0001 | 28.258 | 0.0109 |
| Individual microsimulation | Embodied robot + human safety gate | physical_near_misses_per_100 | 0.5454 | 0.5146 to 0.5758 | <0.0001 | 2.473 | 0.0156 |
| Service discrete-event simulation | Embodied robot (realistic faults) | mean_wait_minutes | 53.1547 | 48.4085 to 58.3956 | <0.0001 | 1.468 | 2.5608 |
| Service discrete-event simulation | Embodied robot (realistic faults) | p90_wait_minutes | 149.3018 | 134.2446 to 166.2940 | <0.0001 | 1.289 | 8.1918 |
| Service discrete-event simulation | Embodied robot (realistic faults) | throughput_per_day | -0.3009 | -0.3605 to -0.2500 | <0.0001 | -0.755 | 0.0282 |
| Service discrete-event simulation | Embodied robot (realistic faults) | abandonment_percent | 0.8578 | 0.7147 to 1.0291 | <0.0001 | 0.757 | 0.0801 |
| Service discrete-event simulation | Embodied robot (realistic faults) | false_alerts_per_100_arrivals | 2.6589 | 2.5985 to 2.7208 | <0.0001 | 5.974 | 0.0315 |
| Service discrete-event simulation | Embodied robot (realistic faults) | missed_high_acuity_percent | -5.9369 | -6.2508 to -5.6271 | <0.0001 | -2.616 | 0.1605 |
| Service discrete-event simulation | Embodied robot (realistic faults) | mean_clinician_utilization_percent | 0.6344 | 0.4943 to 0.7488 | <0.0001 | 0.697 | 0.0644 |
| Service discrete-event simulation | Embodied robot + human safety gate | mean_wait_minutes | 34.4119 | 30.6854 to 39.0192 | <0.0001 | 1.139 | 2.1370 |
| Service discrete-event simulation | Embodied robot + human safety gate | p90_wait_minutes | 102.2414 | 89.8191 to 116.2890 | <0.0001 | 1.055 | 6.8507 |
| Service discrete-event simulation | Embodied robot + human safety gate | throughput_per_day | -0.1601 | -0.2070 to -0.1260 | <0.0001 | -0.549 | 0.0206 |
| Service discrete-event simulation | Embodied robot + human safety gate | abandonment_percent | 0.4567 | 0.3581 to 0.5913 | <0.0001 | 0.551 | 0.0587 |
| Service discrete-event simulation | Embodied robot + human safety gate | false_alerts_per_100_arrivals | 2.2305 | 2.1792 to 2.2829 | <0.0001 | 5.807 | 0.0272 |
| Service discrete-event simulation | Embodied robot + human safety gate | missed_high_acuity_percent | -10.8499 | -11.2507 to -10.4701 | <0.0001 | -3.840 | 0.1998 |
| Service discrete-event simulation | Embodied robot + human safety gate | mean_clinician_utilization_percent | 1.6140 | 1.5082 to 1.6939 | <0.0001 | 2.409 | 0.0474 |

## Reviewer-facing checks

- Fixed random seeds are declared in source code and bootstrap/randomization seeds are derived deterministically from analysis labels.
- Common-random-number pairing is preserved during simulation and resampling.
- All primary outcome families and multiplicity adjustments are machine-readable in the contrast CSV files.
- Bootstrap method, number of resamples, confidence level, test statistics, raw and adjusted p-values, effect sizes, MCSEs, and empirical replication ranges are exported.
- Sensitivity-grid cells and warm-up diagnostics include bootstrap intervals; heatmaps identify cells whose interval excludes the null.
- Scenario-uncertainty proportions use clearly labeled resampling-stability intervals and are not presented as posterior probabilities.
- Figure-generation tests verify live SVG text, absence of embedded raster images, Arial/Arimo-compatible font declarations, and a minimum SVG font size of 10 pt.
