# Reproducing the computational results

The repository contains the scripts, parameter configurations, raw model-generated data, numeric contrasts, sensitivity matrices, figures, and automated integrity checks.

## Requirements

Python **3.10 or later**; GitHub Actions tests use Python 3.13. The package dependencies are recorded in `requirements-lock.txt` (NumPy, pandas, SciPy, Matplotlib, and python-docx). Tests also require `pytest` from `requirements-dev.txt`.

```bash
python -m pip install -r requirements-dev.txt
```

## Fast verification from provided results

```bash
python -m pytest -q
python analysis/validate_models.py
make figures
```

These commands validate model invariants and regenerate all six main PNG/SVG figures from the saved output tables without repeating the full stochastic simulation experiments.

## Manuscript and supplementary document rebuild

```bash
make manuscript
```

This runs `analysis/publication_figures.py`, `analysis/publication_layout.py`, and `analysis/publication_text.py`. The intermediate document build uses [`publication/source_material/integrated_model_text.docx`](../publication/source_material/integrated_model_text.docx). The resulting editable files are `publication/manuscript.docx` and `publication/supplementary_information.docx`. The included PDFs are static reading copies; PDF export is separate from the Python workflow. The source DOCX permits table/legend edits without rerunning simulations.

## Individual analysis modules

```bash
make scenarios          # neutral and skeptical model configurations
make parameters         # parameter documentation and evidence mapping
make sensitivity        # global CRN-aligned Sobol analysis: computationally demanding
make qa                 # tests and structural validation
make checksums          # refresh SHA-256 file inventory
```

For a full computational rebuild:

```bash
make reproduce
```

This reruns primary patient/service models, paired statistics, additional estimands and implementation diagnostics, assumption scenarios, parameter documentation, the 1,024-point Sobol analysis, publication figures, publication documents, and file checksums. The global sensitivity computation evaluates multiple thousands of parameter vectors with repeated stochastic model evaluations, so resources and runtime depend on the execution environment. The already distributed raw matrices make reanalysis and figure exploration possible without that step.

## Which inputs are fixed?

- The individual baseline uses common synthetic cohort seeds within each replication; arm-specific event streams remain separate.
- The service simulation uses matched arrival and latent event streams for pathway comparisons.
- Other analyses use independently derived deterministic seed streams, so nominally equivalent settings can yield slightly different replication means.
- Sobol estimates retain all raw input/output matrices, estimator values and confidence-interval endpoints; small finite-design bound violations are intentionally retained and documented.
- Parameters are illustrative, with units and evidence classes recorded in `config/individual_parameter_dictionary.csv` and `config/service_parameter_dictionary.csv`.

## Output directories

`results/` contains primary tables and datasets. `results/assumption_stress_tests/` contains alternative assumptions; `results/diagnostics/` contains attrition, capacity and pathway-block results; `results/global_sensitivity/` contains the 1,024-point variance-based analysis with complete matrix exports; `results/global_sensitivity_screening/` retains the lower-resolution screening experiment.

Publication plots are under `figures/main/`, and detailed visualizations are under `figures/individual_displays/`, `figures/diagnostics/`, and `figures/model_outputs/`. The [`data catalog`](DATA_CATALOG.md) and [`results map`](RESULTS_TO_CODE.md) document paths and dependencies.

## Integrity checks

The included `SHA256SUMS` and `manifest.json` describe the packaged files. To verify checksums without changing files, run `sha256sum -c SHA256SUMS` on Linux (or `shasum -a 256 -c SHA256SUMS` on macOS). To regenerate the checksum inventory after an intentional modification, use `make checksums`.

No empirical clinical records or identifiers are used in these simulations. Reproducibility establishes numerical behavior under the documented assumptions; the external clinical validity of those assumptions is a separate research question.
