"""Rebuild the npj Digital Medicine current manuscript and reproducibility package.

The base analyses are rerun deterministically and written to their original
output paths. The new global sensitivity audit uses a larger CRN-synchronized
Saltelli design and is computationally expensive; for fast editorial rebuilds,
run `python publication_figures.py` and `python publication_layout.py`.
"""
from __future__ import annotations
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def run(script: str, env: dict[str,str]|None=None, args: list[str]|None=None)->None:
    e=os.environ.copy();e.update(env or {})
    subprocess.run([sys.executable,str(ROOT/"analysis"/script),*(args or [])],cwd=ROOT,check=True,env=e)

def main()->None:
    stages=[
      ('individual-level base simulation','individual_microsimulation.py'),
      ('service-level base simulation','service_queue_simulation.py'),
      ('deterministic model verification','validate_models.py'),
      ('base-case statistical report','statistical_report.py'),
      ('base-case manuscript-source output','model_manuscript_entrypoint.py'),
      ('structural and estimand diagnostics','structural_sensitivity.py'),
      ('diagnostic model visualizations','exploratory_figures.py'),
      ('neutral/skeptical model stress tests','assumption_scenarios.py'),
      ('complete parameter documentation','parameter_documentation.py'),
      ('evidence/citation repair','parameter_reference_audit.py'),
      ('CRN-synchronized N=1,024 global Sobol analysis','sobol_high_precision.py'),
      ('six publication figures','publication_figures.py'),
      ('streamlined manuscript and supplementary tables','publication_layout.py'),
      ('publication narrative and bibliography','publication_text.py'),
      ('SHA-256 provenance checksums','checksum_manifest.py'),
    ]
    for label,script in stages:
        print(f'Running: {label} ({script})',flush=True)
        run(script,{'PHYSICAL_AI_SKIP_TEX_PDF':'1'} if script=='model_manuscript_entrypoint.py' else None)
    print('Reproduction complete: publication/, results/, figures/main/, docs/ and manifest.json',flush=True)

if __name__=='__main__':main()
