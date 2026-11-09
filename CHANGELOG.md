# Changelog

## 4.3.0 - 2026-07-30

- Added exhaustive individual and service parameter dictionaries documenting units, functional roles, base values, neutral and skeptical values, global ranges, range and pathway-ordering rationales, evidence classes, supporting references, and calibration status.
- Added a complete mathematical and operational model specification covering state variables, baseline draws, engagement, symptoms, crises, alerts, verification, trust, dropout, queue resources, arrivals, service times, clinician work, abandonment, outputs, pairing, and uncertainty estimators.
- Added prespecified neutral and skeptical assumption scenarios. Neutral assumptions removed robot-specific engagement and symptom advantages; skeptical assumptions combined adverse but declared-range acceptance, reliability, detection, review, dropout, and physical-burden values.
- Implemented global interaction-aware Sobol sensitivity analysis over 12 individual and 11 service inputs, including first-order, total-order, and every pairwise second-order index with row-bootstrap diagnostic intervals.
- Added an Ishigami benchmark test for the implemented Sobol estimators and completeness tests for parameter dictionaries and v4.3 manuscript artifacts.
- Added a prospective structured multi-stakeholder elicitation and face-validation protocol and a machine-readable elicitation template. Explicitly stated that empirical calibration, formal elicitation, and independent face validation were not completed.
- Integrated the new scenario results, two global-sensitivity figures, five additional tables, complete equations, parameter documentation, calibration status, and validation plan into the main manuscript without changing the audited primary base-case outputs.
- Expanded the reference base for adherence, attrition, app engagement, model parameter uncertainty, expert elicitation, model validation, global sensitivity, physical health-care robots, and alarm burden.
- Added 300-dpi manuscript-preview images while retaining the 600-dpi PNG and live-text SVG publication originals.
- Updated the end-to-end workflow, Makefile targets, README, cover letter, citation metadata, reporting checklist, tests, and integrity manifests for v4.3.

## 4.2.0 - 2026-07-30

- Restored the preferred manuscript title: *Reimagining Psychiatric Care with Physical AI: Multiscale Simulation Stress Tests of Benefit, Burden, and Break-Even Conditions*.
- Performed a narrative-only revision; no simulation, bootstrap, randomization, or sensitivity analysis was rerun or numerically altered.
- Integrated all 15 journal figures and all 8 tables, including the former supplementary displays, into the active main manuscript at the point of first substantive discussion.
- Renumbered displays continuously and added explicit transitions from patient trajectories to thresholds, safety and labor, service access, break-even analyses, estimand sensitivity, capacity sensitivity, and pathway decomposition.
- Expanded the Introduction and Discussion with literature on physical copresence, socially assistive-robot evidence, digital psychiatry, implementation and scale-up, and clinical-AI reporting guidance.
- Archived the separate v4.1 main and supplementary submission files for provenance and made the v4.2 integrated manuscript the active submission artifact.
- Updated the cover letter, README, citation metadata, CI checks, tests, revision notes, and integrity manifests.

## 4.1.0 - 2026-07-29

- Preserved the audited v4.0 primary simulation outputs and added four reviewer-motivated exploratory analyses: attrition-estimand sensitivity, nested parameter-scenario replication, embodied intake-capacity sensitivity, and one-block pathway decomposition.
- Reframed the screen comparison as a content-matched bundled pathway contrast rather than a pure causal embodiment effect.
- Added six main and nine supplementary journal-oriented figures using full replication distributions, grayscale-safe encodings, 600-dpi PNG, and live-text SVG.
- Added an npj Digital Medicine-structured manuscript with an 11-word unpunctuated title, 137-word unstructured abstract, current section order, separate Data and Code Availability statements, and one separate supplementary-information file.
- Added a cover-letter draft and a 12-part scientific, statistical, code, figure, journal-compliance, and repository-readiness report.
- Clarified that the service physical-reset variable represents routine reset work rather than stochastic incidents and added an explicit output alias.
- Extended the end-to-end workflow and CI expectations to regenerate reviewer analyses and journal artifacts.

## 4.0.0 - 2026-07-29

- Added paired BCa bootstrap 95% confidence intervals for primary individual and service contrasts using 10,000 resamples.
- Added bootstrap intervals to arm endpoints, weekly trajectories, sensitivity grids, parameter-scenario stability summaries, and warm-up diagnostics where statistically meaningful.
- Separated confidence intervals for expected mean simulation output from empirical replication prediction ranges.
- Added paired sign-flip randomization tests with 100,000 draws, paired t-test concordance analyses, Holm family-wise multiplicity adjustment, Cohen's dz, and Monte Carlo standard errors.
- Added consolidated machine-readable and reviewer-facing statistical reports.
- Rebuilt all 12 figures with uncertainty displays, live editable SVG text, Arial-first font declarations, an Arimo build fallback, and a 10-pt minimum figure font size.
- Increased generated PNG output to 600 dpi and added automated vector, raster-wrapper, font, and manuscript-embedding checks.
- Updated the final DOCX and Markdown manuscript, figure captions, limitations, statistical interpretation, dependencies, CI tests, workflow documentation, package metadata, and integrity manifests.
- Changed the end-to-end runner to sequential model execution to reduce peak memory during resampling.

## 3.0.0 - 2026-07-29

- Re-ran the complete individual and service simulation framework and reproduced all headline values.
- Replaced the earlier drop-in insert with a complete standalone DOCX and Markdown paper built directly from current result files.
- Reframed the contribution around a dual-gate standard: incremental patient benefit plus operational noninferiority.
- Integrated six primary and six supplementary figures into the manuscript while retaining all 12 editable SVG originals in a separate directory.
- Added `outputs/manuscript_key_results.json` to make manuscript-result consistency machine-checkable.
- Updated the novelty claim to a qualified combination claim and removed any implication of first-ever priority or clinical statistical significance.
- Added the conceptual-versus-dynamically-coupled limitation and strengthened queue, threshold, external-validity, and safety caveats.
- Updated README, manuscript/figure workflow, CI, regression tests, package metadata, and checksums for the final release.
- Archived v2 manuscript artifacts for provenance rather than treating them as active deliverables.

## 2.0.0 - 2026-07-29

- Corrected service comparisons to use paired common random numbers, so all pathways see identical synthetic arrival and acuity streams within each replication.
- Increased base replication counts to 200 for both individual and service models.
- Added standard deviations and Monte Carlo standard errors to paired contrast summaries.
- Added replicated individual sensitivity cells, break-even summaries, and 250-draw scenario-based parameter uncertainty.
- Added service break-even thresholds and warm-up diagnostics.
- Added exact queue flow accounting and expanded impossible-event validation.
- Added 12 paired publication outputs in 300-dpi PNG and editable SVG with live text.
- Added integrated Markdown, LaTeX, DOCX, and PDF manuscript artifacts with all figures.
- Added a targeted novelty/significance audit and conservative claim wording.
- Added parameter provenance, tests, CI, pinned dependencies, Makefile, citation metadata, contribution guidance, and checksums.
- Preserved the synthetic, assumption-driven status of all findings and removed unsupported clinical-significance language.

## 1.1.0

- Separated synthetic cohort and arm-specific random streams.
- Added shared baseline cohorts for lower-noise individual contrasts.
- Added repeated individual experiments and initial Monte Carlo intervals.
- Added a queue warm-up period and deterministic checks.
