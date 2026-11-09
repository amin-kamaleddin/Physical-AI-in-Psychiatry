# Results-to-code map

This map links each main display in the accompanying manuscript to its saved data and executable implementation. All figure assets are available as editable SVG and high-resolution PNG in [`figures/main/`](../figures/main/). Figure generation uses [`analysis/publication_figures.py`](../analysis/publication_figures.py); table composition uses [`analysis/publication_layout.py`](../analysis/publication_layout.py).

## Main figures

| Figure | Scientific content | Saved inputs | Computational source |
| --- | --- | --- | --- |
| **1. Complementary care contexts** | Longitudinal monitoring, clinic intake, compared pathways, dual-gate decision criterion | Pathway configurations in code | [`individual_microsimulation.py`](../analysis/individual_microsimulation.py), [`service_queue_simulation.py`](../analysis/service_queue_simulation.py), `publication_figures.py` |
| **2. Patient outcomes and oversight burden** | PHQ-9 trajectories; response, remission, completion; paired contrasts; near-misses, review minutes, missed-risk weeks | [`individual_weekly_bootstrap_summary.csv`](../results/individual_weekly_bootstrap_summary.csv), [`individual_arm_summary.csv`](../results/individual_arm_summary.csv), [`individual_contrast_summary.csv`](../results/individual_contrast_summary.csv) | `individual_microsimulation.py`, [`statistical_report.py`](../analysis/statistical_report.py), `publication_figures.py` |
| **3. Clinic intake access and safety** | Wait distributions, mean waiting, risk detection and false alerts, throughput | [`system_replication_results.csv`](../results/system_replication_results.csv), [`system_contrast_summary.csv`](../results/system_contrast_summary.csv), [`system_scenario_summary.csv`](../results/system_scenario_summary.csv) | `service_queue_simulation.py`, `statistical_report.py`, `publication_figures.py` |
| **4. Robustness and break-even conditions** | Neutral and skeptical scenarios, engagement/downtime grid, waiting-time grid, parameter ensemble | [`neutral_skeptical_contrast_summary.csv`](../results/assumption_stress_tests/neutral_skeptical_contrast_summary.csv), [`individual_sensitivity_grid.csv`](../results/individual_sensitivity_grid.csv), [`system_sensitivity_grid.csv`](../results/system_sensitivity_grid.csv), [`individual_parameter_uncertainty.csv`](../results/individual_parameter_uncertainty.csv) | [`assumption_scenarios.py`](../analysis/assumption_scenarios.py), `individual_microsimulation.py`, `service_queue_simulation.py`, `publication_figures.py` |
| **5. Global sensitivity** | Total-order Sobol importance and pairwise interaction diagnostics | [`sobol_first_total_indices.csv`](../results/global_sensitivity/sobol_first_total_indices.csv), [`sobol_second_order_indices.csv`](../results/global_sensitivity/sobol_second_order_indices.csv), [`raw design matrices`](../results/global_sensitivity/raw), [`estimator_diagnostics.csv`](../results/global_sensitivity/estimator_diagnostics.csv) | [`sobol_high_precision.py`](../analysis/sobol_high_precision.py), [`sobol_design_and_screening.py`](../analysis/sobol_design_and_screening.py), `publication_figures.py` |
| **6. Estimand and implementation checks** | Attrition estimands, intake capacity, pathway-block substitutions, queue warm-up | [`individual_estimand_sensitivity_summary.csv`](../results/diagnostics/individual_estimand_sensitivity_summary.csv), [`service_capacity_sensitivity_summary.csv`](../results/diagnostics/service_capacity_sensitivity_summary.csv), [`patient_pathway_bundle_ablation_summary.csv`](../results/diagnostics/patient_pathway_bundle_ablation_summary.csv), [`system_warmup_diagnostic.csv`](../results/system_warmup_diagnostic.csv) | [`structural_sensitivity.py`](../analysis/structural_sensitivity.py), `service_queue_simulation.py`, `publication_figures.py` |

## Main tables

| Table | Content | Source |
| --- | --- | --- |
| **1. Compared care pathways** | Four pathways and their functions in each care context | `ARM_CONFIGS` in `individual_microsimulation.py`; `CONFIGS` in `service_queue_simulation.py`; `publication_layout.py` |
| **2. Primary pathway contrasts** | Patient and service outcomes with paired BCa intervals | [`individual_contrast_summary.csv`](../results/individual_contrast_summary.csv) and [`system_contrast_summary.csv`](../results/system_contrast_summary.csv) |
| **3. Neutral and skeptical settings** | Outcome contrasts under alternate parameter settings | [`neutral_skeptical_contrast_summary.csv`](../results/assumption_stress_tests/neutral_skeptical_contrast_summary.csv) |
| **4. Global input importance** | Total-order Sobol estimates with finite-design uncertainty | [`sobol_first_total_indices.csv`](../results/global_sensitivity/sobol_first_total_indices.csv) |

## Supplementary tables and data

The supplementary document is in [`publication/supplementary_information.docx`](../publication/supplementary_information.docx). Its statistical diagnostics are linked to the [`results/diagnostics`](../results/diagnostics/) directory and the complete [`results/global_sensitivity`](../results/global_sensitivity/) matrix exports. The full input documentation is supplied separately as [`supplementary_data_patient_parameters.csv`](../publication/supplementary_data_patient_parameters.csv) and [`supplementary_data_service_parameters.csv`](../publication/supplementary_data_service_parameters.csv).

## Numerical provenance

Primary paired comparisons use 200 independent replications, while endpoint, capacity, and assumption modules use deterministic **separate** random streams. Slight differences across modules evaluating the same nominal configuration reflect independent Monte Carlo replication and are retained. Sobol sensitivity uses 1,024 design base points with matched random streams within each cross-sampling row. The preliminary screening design is separately retained in [`results/global_sensitivity_screening`](../results/global_sensitivity_screening/) for estimator diagnostics. See [`ANALYSIS_PROVENANCE.md`](ANALYSIS_PROVENANCE.md).
