# Release validation history

**Validation date:** 29 July 2026  
**Reference command:** `python run_all.py`

## End-to-end reproduction

- Sequential clean reproduction completed with exit code 0.
- Individual base case: 5,000 synthetic participants per arm.
- Individual primary analysis: 200 paired trials, 1,200 participants per arm per trial.
- Individual parameter scenarios: 250.
- Service primary analysis: 200 paired replications with common synthetic demand streams.
- Service horizon: five-working-day warm-up plus 35 observed working days.
- Primary contrasts: 10,000 BCa bootstrap resamples and 100,000 paired sign-flip draws.
- Secondary arm, weekly, sensitivity, scenario-stability, and warm-up intervals regenerated at their documented resample counts.

## Statistical and computational checks

- `pytest`: 8 tests passed.
- `python validate_models.py`: all deterministic verification checks passed.
- Shared baseline cohorts and common service demand verified.
- Exact queue accounting and nonembodied impossible-event checks verified.
- Bootstrap and randomization outputs are deterministic under exported seeds.
- Primary contrast files export bootstrap method, CI level, resample count, bootstrap seed, randomization seed, minimum attainable Monte Carlo p-value, paired t statistic and degrees of freedom, raw and Holm-adjusted p-values, Cohen's dz, MCSE, empirical replication range, and family size.
- Manuscript headline-result JSON matches the generated contrast CSV files.

## Publication-artifact checks

- 12 valid 600-dpi publication PNG files generated.
- 12 editable SVG files generated.
- Every SVG contains live `<text>` elements, an Arial-first/Arimo-fallback declaration, and a minimum font size of 10 pt.
- No SVG contains an embedded raster `<image>` element.
- Final DOCX contains 12 embedded figures and renders to 20 pages.
- All 20 pages were visually inspected for clipping, overlap, missing content, table integrity, and figure-caption placement.
- The final post-regeneration render is pixel-identical across all 20 pages to the inspected render.
- DOCX accessibility audit: 0 high-, 0 medium-, and 0 low-severity findings.

## Release-integrity checks

- `outputs/statistical_analysis_summary.csv` consolidates all primary contrasts.
- `docs/STATISTICAL_ANALYSIS.md` documents estimands, resampling, tests, multiplicity, effect sizes, seeds, and interpretation limits.
- `outputs/manuscript_key_results.json` is regenerated from current CSV outputs.
- `manifest.json` and `SHA256SUMS` cover release files using SHA-256.
- Active manuscript, uncertainty outputs, and figure paths are asserted in CI.

## Interpretation boundary

This validation establishes computational reproducibility, internal consistency, and Monte Carlo precision under the fixed synthetic assumptions. It does not establish empirical calibration, clinical efficacy, clinical safety, causal validity, cost-effectiveness, external validity, or regulatory acceptability.

## v4.1 review validation - 29 July 2026

- Full primary individual and service simulations regenerated.
- `pytest -q`: 9 tests passed after v4.1 additions.
- `python validate_models.py`: all deterministic structural checks passed.
- Reviewer reanalysis completed: attrition estimands, nested scenarios, intake capacity, and pathway-block decomposition.
- Journal figure set generated: 6 main plus 9 supplementary figures in 600-dpi PNG and live-text SVG.
- Main manuscript rendered to 9 pages and visually inspected.
- Supplementary Information rendered to 11 pages and visually inspected; PDF render verified.
- Scientific and reproducibility report rendered to 6 landscape pages and visually inspected; PDF render verified.
- No credentials, access tokens, patient-level information, or absolute local paths were identified in the release files.
- Author metadata, license, repository DOI, funding, contribution, and competing-interest placeholders remain intentionally unresolved.
## v4.2 narrative and display-integration validation - 30 July 2026

- No simulation, bootstrap, randomization, or sensitivity analysis was rerun for the v4.2 narrative revision.
- The active manuscript was rebuilt directly from the audited v4.1 machine-readable outputs and existing journal figures.
- The preferred title was restored exactly in the manuscript, cover letter, README, and citation metadata.
- The active DOCX contains 15 embedded figures and 8 integrated tables with continuous numbering.
- Every figure and table is introduced or interpreted in the main text, with explicit transitions between patient, service, robustness, and component analyses.
- The Introduction and Discussion were expanded with 26 total references covering physical copresence, social-robot evidence synthesis, digital psychiatry, implementation science, simulation reporting, and clinical-AI evaluation guidance.
- The active manuscript rendered to 18 pages; all pages were visually inspected for clipping, overlap, table splitting, missing content, and figure-caption placement.
- The v4.2 cover letter rendered to one page and was visually inspected.
- The former v4.1 main and supplementary submission files remain archived for provenance.
