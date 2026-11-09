# Reporting framework

The computational study follows simulation-reporting and model-transparency principles with explicit description of comparators, input assumptions, outputs, statistical units, random stream design, simulation horizon, model equations, implementation checks, and sensitivity analysis.

| Component | Documentation |
| --- | --- |
| Clinical decision context and comparators | Manuscript Introduction and Methods; `README.md` |
| Full patient and service equations and event ordering | `docs/MODEL_SPECIFICATION.md` |
| Parameter values, units, roles, rationales and range definitions | `config/*parameter_dictionary.csv` |
| Primary estimands and Monte Carlo intervals | `docs/STATISTICAL_METHODS.md`; `results/*contrast_summary.csv` |
| Common random numbers, seed choices and structural diagnostics | `docs/ANALYSIS_PROVENANCE.md` |
| Neutral, skeptical, and global sensitivity analysis | `results/assumption_stress_tests/`; `results/global_sensitivity/` |
| Verification and deterministic tests | `tests/`; `analysis/validate_models.py` |
| Computation-to-display traceability | `docs/RESULTS_TO_CODE.md` |
| Independent face validation and empirical calibration | Not completed; prospective protocol in `docs/ELICITATION_AND_VALIDATION_PROTOCOL.md` |

All patient-level and clinic-level records in this repository are computationally generated. Model precision, structural verification, and sensitivity robustness address different dimensions of inference; none substitutes for external clinical validation.
