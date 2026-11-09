"""Rebuild the npj Digital Medicine v4.5 manuscript and reproducibility package.

The base analyses are rerun deterministically and written to their original
output paths. The new global sensitivity audit uses a larger CRN-synchronized
Saltelli design and is computationally expensive; for fast editorial rebuilds,
run `python build_submission_figures_v4_4.py` and `python build_submission_v4_4.py`.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent

def run(script: str, env: dict[str,str]|None=None, args: list[str]|None=None)->None:
    e=os.environ.copy();e.update(env or {})
    subprocess.run([sys.executable,str(ROOT/script),*(args or [])],cwd=ROOT,check=True,env=e)

def main()->None:
    stages=[
      ('individual-level base simulation','individual_microsimulation.py'),
      ('service-level base simulation','service_queue_simulation.py'),
      ('deterministic model verification','validate_models.py'),
      ('base-case statistical report','generate_statistical_report.py'),
      ('base-case manuscript-source output','build_manuscript.py'),
      ('previous structural/estimand diagnostics','reviewer_reanalysis.py'),
      ('archived model plots','build_journal_figures.py'),
      ('neutral/skeptical model stress tests','scenario_analysis_v4_3.py'),
      ('complete parameter documentation','build_parameter_documentation_v4_3.py'),
      ('evidence/citation repair','repair_provenance_v4_4.py'),
      ('CRN-synchronized N=1,024 global Sobol analysis','global_sensitivity_v4_4.py'),
      ('six publication figures','build_submission_figures_v4_4.py'),
      ('streamlined manuscript and supplementary tables','build_submission_v4_4.py'),
      ('updated manuscript cover letter','build_cover_letter_v4_4.py'),
      ('clinical narrative, 2026 literature, and v4.5 submission draft','revise_narrative_v4_5.py'),
      ('SHA-256 provenance checksums','generate_manifest.py'),
    ]
    for label,script in stages:
        print(f'Running: {label} ({script})',flush=True)
        run(script,{'PHYSICAL_AI_SKIP_TEX_PDF':'1'} if script=='build_manuscript.py' else None)
    print('Reproduction complete: manuscript/, outputs/, figures/submission_v4_4/, docs/ and manifest.json',flush=True)

if __name__=='__main__':main()
