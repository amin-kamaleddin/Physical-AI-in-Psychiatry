# Contributing

Use a feature branch and keep simulation changes traceable to explicit assumptions.

1. Record any parameter change in `config/parameter_provenance.csv` and `CHANGELOG.md`.
2. Preserve the functionally matched screen comparator and common-random-number design.
3. Add or update tests for structural invariants and impossible events.
4. Run `pytest`, `python validate_models.py`, and `python run_all.py` before opening a pull request.
5. Do not describe synthetic outputs as clinical efficacy, safety, or incidence estimates.
6. Commit regenerated CSV, PNG, SVG, manuscript, and checksum files when outputs change.
