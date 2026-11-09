# Computational analysis provenance

## Primary simulations

Two complementary models evaluate longitudinal care and intake operations. The primary numerical contrasts are generated in `analysis/individual_microsimulation.py` and `analysis/service_queue_simulation.py`, then summarized by `analysis/statistical_report.py`. The full 200-replication records, paired contrasts, 10,000-resample BCa intervals, sign-flip randomization tests, multiplicity corrections, and Monte Carlo standard errors are retained under `results/`.

## Alternative assumptions and implementation conditions

`analysis/assumption_scenarios.py` evaluates neutral and skeptical assumption sets. `analysis/structural_sensitivity.py` evaluates endpoint definitions under attrition, clinic intake capacity, nested parameter uncertainty, and selective parameter-block substitutions. These analyses have distinct deterministic random streams. Comparisons across their estimated means are consequently subject to finite-replication Monte Carlo differences even when configured values are nominally identical.

## Global sensitivity

The 1,024-base-point scrambled Sobol design uses a Saltelli A/B/cross-sampled construction and fixed common random streams within the cross-sampling row. First-order indices use a covariance estimator, total-order indices the Jansen squared-difference estimator, and pairwise interactions a cross-matrix estimator. Bootstrap intervals resample design rows intact. Independent uniform input distributions express a declared stress-test range; the indices do not represent calibrated parameter uncertainty.

Complete inputs and outputs are in `results/global_sensitivity/raw/`. Summary tables and diagnostics are in the parent directory. `results/global_sensitivity_screening/` preserves the preceding lower-resolution sensitivity experiment for comparison and estimator diagnostics. These are two scientifically distinct analyses with separate design sizes; the higher-precision estimates inform the primary global-sensitivity display.

## Source and figure regeneration

The figure builder `analysis/publication_figures.py` reads saved numerical results. The manuscript generator `analysis/publication_layout.py` composes the method tables and display references, and `analysis/publication_text.py` prepares the accompanying current narrative. `publication/source_material/integrated_model_text.docx` is a deterministic publication-build input. The current manuscript and supplement are directly accessible in `publication/`.

Changing model assumptions requires regenerating the corresponding results and any dependent figures and tables. The [results-to-code map](RESULTS_TO_CODE.md) traces those dependencies without discarding prior computed outputs.
