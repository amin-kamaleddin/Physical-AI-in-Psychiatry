# Public data inventory

The complete research dataset in this repository is **computationally generated**.
It contains no real patient records, protected health information, or participant
identifiers. Outcomes describe the assumptions and synthetic event processes
implemented by the released code; do not use these outputs to estimate clinical
incidence or treatment effectiveness in a patient population.

## Where to find the data

- `config/` — the 47-parameter individual and 33-parameter service documentation,
  evidence/status classes and structured elicitation template.
- `scenario_library.csv`, `safety_case_schema.yaml` — scenario definitions.
- `outputs/individual_patient_level_synthetic.csv` — generated patient trajectories
  and events from the base cohort (synthetic records only).
- `outputs/individual_*`, `outputs/system_*` — arm and paired-replication data,
  break-even summaries, uncertainty intervals and time-course results.
- `outputs/assumption_scenarios_v4_3/` — neutral/skeptical replications.
- `outputs/reviewer_reanalysis/` — retained estimand, capacity and pathway diagnostics.
- `outputs/global_sensitivity/` — original N=128 screening design and outputs
  (historical diagnostic only; not the publication-recommended estimate).
- `outputs/global_sensitivity_v4_4/` — revised N=1,024 design, input matrices,
  simulation output matrices, Sobol indices, estimator diagnostics and metadata.

All source data consist of synthetic model outputs and their fixed inputs.
There are **no external restricted clinical datasets** required to reproduce
these published computational results. The `data/private/`, `data/clinical/` and
`data/restricted/` paths are intentionally ignored in git if created locally.

## Reproduction

`python -m pytest -q` runs the fast model and output checks.
`python validate_models.py` validates structural invariants.
`python run_all.py` regenerates the entire model outputs, plots and manuscript;
this includes an expensive high-resolution variance-based sensitivity analysis.
The README and parameter dictionaries document model assumptions and seeds.
