.PHONY: install test validate reproduce scenarios sensitivity figures manuscript parameters checksums qa
install:
	python -m pip install -r requirements-lock.txt
reproduce:
	python run_all.py
test:
	python -m pytest -q
validate:
	python analysis/validate_models.py
scenarios:
	python analysis/assumption_scenarios.py
sensitivity:
	python analysis/sobol_high_precision.py --n-base 1024 --inner 2 --patients 350 --days 18
parameters:
	python analysis/parameter_documentation.py
	python analysis/parameter_reference_audit.py
figures:
	python analysis/publication_figures.py
manuscript: figures
	python analysis/publication_layout.py
	python analysis/publication_text.py
checksums:
	python analysis/checksum_manifest.py
qa: test validate
