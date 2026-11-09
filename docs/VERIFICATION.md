# Computational verification

## Automated checks

The repository's `tests/` directory includes deterministic simulation checks, shared baseline and demand streams, nonembodied physical-exposure exclusion, bootstrap reproducibility, probability/range constraints, and queue accounting. It also verifies the scientific result tables, manuscript display counts, parameter-dictionary coverage, saved global-sensitivity matrices, and editable SVG text.

The queue test explicitly checks that unfinished service work continues across successive 420-minute productive working-day blocks. The service model advances in working-minute time; scheduled calendar closures and explicit overtime shifts are outside this implementation.

```bash
python -m pytest -q
python analysis/validate_models.py
```

The GitHub workflow in `.github/workflows/ci.yml` runs the automated test suite and structural model checks on push and pull-request events. The full computational workflow can be triggered separately through workflow dispatch.

## Interpretation of checks

Passing these checks supports implementation consistency, reproducible output generation, and preservation of the declared statistical methods. It does not establish that modeled clinical or operational parameters describe actual psychiatric care. Empirical calibration, external predictive validation, and structured multidisciplinary face validation have not been completed. Their prospective design is documented in [`ELICITATION_AND_VALIDATION_PROTOCOL.md`](ELICITATION_AND_VALIDATION_PROTOCOL.md).

The initial screening analysis and the higher-precision variance-based analysis are both retained. The larger design addresses first-order/total-order estimation instability for principal endpoints; small remaining finite-design violations are visible in the raw estimator diagnostics and are excluded from substantive interpretation.
