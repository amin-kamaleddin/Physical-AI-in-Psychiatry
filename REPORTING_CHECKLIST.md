# Simulation reporting checklist

This repository-specific checklist is informed by established simulation-reporting and model-transparency principles. It is not a claim of formal checklist certification.

## Scope and claims

- [x] State that the simulations contain no patient-level clinical data.
- [x] State that parameters are illustrative and not calibrated estimates.
- [x] Define the estimand as expected model output under fixed assumptions.
- [x] Distinguish confidence intervals for the simulated mean from empirical replication prediction ranges, parameter-scenario uncertainty, and clinical inferential uncertainty.
- [x] Avoid claims of clinical efficacy, safety, incidence, causality, or cost-effectiveness.
- [x] Frame novelty as a qualified combination claim rather than a first-ever claim.

## Conceptual model and inputs

- [x] Define the decision problem, comparators, states, events, resources, time horizons, and outcomes.
- [x] Preserve a content-matched nonembodied comparator and disclose that the complete pathway contrast is bundled.
- [x] Describe human review, fallback, refusal, downtime, queueing, false alerts, and physical-safety mechanisms.
- [x] Disclose that the individual and service models are conceptually aligned but not dynamically coupled.
- [x] Publish exhaustive parameter dictionaries with units, functional roles, base values, neutral and skeptical values, global ranges, range and pathway-ordering rationales, evidence classes, references, and calibration status.
- [x] Publish complete mathematical equations, state-update rules, queue events, resource disciplines, output denominators, and estimands.

## Experiment design and uncertainty

- [x] Report base cohort size, replication count, warm-up, observation period, and sensitivity-grid replication counts.
- [x] Use shared baseline cohorts and common synthetic demand streams for paired comparisons.
- [x] Treat the independent simulation replication as the resampling and testing unit.
- [x] Report the bootstrap method, confidence level, resample count, deterministic seed derivation, and paired resampling structure.
- [x] Use 10,000 BCa resamples for primary mean contrasts and disclose lower resample counts for secondary displays.
- [x] Report MCSE, empirical replication ranges, and parameter-scenario stability separately.
- [x] Report paired sign-flip randomization tests, paired t-tests, Cohen's dz, prespecified outcome families, and Holm multiplicity adjustment.
- [x] Report break-even thresholds and warm-up diagnostics.
- [x] Report attrition-estimand sensitivity, nested scenario replication, intake-capacity sensitivity, and one-block pathway decomposition.
- [x] Report neutral and skeptical assumption sets and their full paired contrasts.
- [x] Implement global interaction-aware sensitivity with first-order, total-order, and pairwise second-order Sobol indices and diagnostic bootstrap intervals.
- [x] Validate the implemented Sobol estimators against the Ishigami benchmark.

## Verification and validation

- [x] Fixed-seed repeatability.
- [x] Range, accounting, and impossible-event checks.
- [x] Shared-cohort and shared-demand checks.
- [x] Deterministic bootstrap and randomization checks.
- [x] Machine-check manuscript headline values against generated contrast files.
- [x] Automated tests for interval fields, p-values, resample counts, and figure integrity.
- [ ] External validation against empirical clinical or operational data; not possible until suitable data are supplied.
- [ ] Structured multi-stakeholder parameter elicitation; prospective protocol and collection template supplied, but no panel was conducted.
- [ ] Face validation by patients, clinicians, engineers, statisticians, and service managers; prospective protocol supplied, but no panel was conducted.

## Publication artifacts

- [x] End-to-end Python runner and pinned reference dependencies.
- [x] Machine-readable raw outputs, bootstrap summaries, test results, effect sizes, MCSEs, and headline-result JSON.
- [x] Preserved provenance manuscripts plus the active integrated v4.3 DOCX/PDF, cover-letter draft, and reproducible builders.
- [x] Twelve provenance figures plus 17 continuously numbered journal-oriented 600-dpi PNG figures, including two global-sensitivity displays.
- [x] Provenance and journal figure sets exported as editable SVG with live text and no embedded raster images.
- [x] Arial-first font declarations, documented Arimo build fallback, and 10-pt minimum SVG font size.
- [x] DOCX accessibility audit and full-page visual inspection of the 30-page active manuscript and one-page cover letter.
- [x] SHA-256 manifest and GitHub Actions workflow.
