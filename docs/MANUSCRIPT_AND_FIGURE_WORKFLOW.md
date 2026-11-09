# Manuscript and editable-figure workflow

## Active manuscript

The active submission-oriented paper is:

- `manuscript/Physical_AI_Psychiatry_Integrated_Manuscript_v4.3.docx`
- `manuscript/Physical_AI_Psychiatry_Integrated_Manuscript_v4.3.pdf`
- `manuscript/Cover_Letter_Draft_v4.3.docx`
- `manuscript/Cover_Letter_Draft_v4.3.pdf`

Earlier v4.2, v4.1, and provenance manuscript files are retained for traceability and are not the active submission artifacts.

`python build_integrated_manuscript_v4_3.py` reads current CSV/JSON outputs and parameter dictionaries rather than hard-coding headline results. It does not execute either primary model; generate or verify analyses before rebuilding the manuscript.

## Statistical regeneration

- `individual_microsimulation.py` and `service_queue_simulation.py` regenerate the audited primary simulations and paired uncertainty analyses.
- `reviewer_reanalysis.py` regenerates attrition-estimand, nested-scenario, capacity, and pathway-block analyses.
- `scenario_analysis_v4_3.py` regenerates the neutral and skeptical assumption contrasts.
- `global_sensitivity.py` regenerates the complete Sobol `S1`, `ST`, and pairwise `S2` analysis, raw Saltelli designs, matrix outputs, summaries, and Figures 16-17.
- `build_parameter_documentation_v4_3.py` regenerates the exhaustive dictionaries, complete specification, elicitation template, and validation protocol.

The independent simulation replication is the resampling unit. Paired pathways remain paired during resampling and testing. Do not bootstrap patient rows across already simulated arms or service encounters independently; that would destroy the common-random-number design.

## Figure structure and typography

The active manuscript contains 17 continuously numbered figures and 15 tables.

- `figures/journal/png/`: 600-dpi publication originals.
- `figures/journal/svg/`: editable live-text vector originals with no embedded raster image.
- `figures/manuscript_preview/`: 300-dpi copies embedded in the DOCX to keep the document portable and renderable.

Generated figures use an Arial-first font policy with Arimo as the metric-compatible Linux build fallback. The minimum generated figure font size is 10 pt. Error bars and shaded bands are 95% bootstrap intervals unless a caption states otherwise.

## Editing an SVG manually

1. Open the corresponding file in Inkscape, Illustrator, Affinity Designer, or another SVG editor.
2. Preserve axes, units, uncertainty definitions, null markers, and direction-of-benefit annotations.
3. Keep final visible text at 10 pt or larger at intended print size.
4. Export a 600-dpi PNG with the same filename stem into `figures/journal/png/`.
5. Regenerate `figures/manuscript_preview/` or rerun the documented preview step.
6. Rebuild with `python build_integrated_manuscript_v4_3.py`.
7. Render the DOCX and inspect every page before submission.

Re-running an analysis script can overwrite generated figure files. Keep manual edits on a dedicated branch or outside generated directories until journal styling is final.

## Full reproducibility run

```bash
python -m pip install -r requirements-lock.txt
python run_all.py
pytest -q
python validate_models.py
```

The global Sobol stage is computationally intensive and prints progress by matrix. The models run sequentially to constrain peak memory.

## Submission checks

- Replace author, affiliation, ethics, funding, competing-interest, repository URL, DOI, and license placeholders.
- Complete empirical calibration, structured multi-stakeholder elicitation, and independent face validation, or retain explicit limitations if submitting the work as an assumption-driven methods study.
- Reconcile citation style, word count, figure limits, and table placement with the target journal.
- Keep the content-matched screen comparator and bundled-pathway limitation central.
- Report the bootstrap method, resampling unit, number of resamples, confidence level, paired tests, multiplicity family, effect size, MCSE, deterministic seed strategy, and Sobol design.
- Keep “model-internal,” “conditional,” “stress test,” and “hypothesis-generating” qualifiers wherever statistical separation is discussed.
- Do not describe simulation intervals as clinical confidence intervals or stress ranges as empirical posterior distributions.
- Do not claim “first-ever”; novelty is the integrated multiscale dual-gate and parameter-audit framework.
