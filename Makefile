.PHONY: install reproduce test validate scenarios sensitivity parameters figures manuscript checksums qa clean

install:
	python -m pip install -r requirements-lock.txt

reproduce:
	python run_all.py

test:
	pytest -q

validate:
	python validate_models.py

scenarios:
	python scenario_analysis_v4_3.py

sensitivity:
	python global_sensitivity_v4_4.py --n-base 1024 --inner 2 --patients 350 --days 18

parameters:
	python build_parameter_documentation_v4_3.py
	python repair_provenance_v4_4.py

figures:
	python build_submission_figures_v4_4.py

manuscript: figures
	python build_submission_v4_4.py
	python build_cover_letter_v4_4.py
	python revise_narrative_v4_5.py

checksums:
	python generate_manifest.py

qa: test validate

clean:
	rm -rf __pycache__ .pytest_cache tests/__pycache__ _docx_render
	rm -f manuscript/*.aux manuscript/*.log manuscript/*.out manuscript/*.toc
