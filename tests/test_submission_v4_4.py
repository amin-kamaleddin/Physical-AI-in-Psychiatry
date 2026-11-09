"""Targeted checks for the statistical and editorial revision."""
from pathlib import Path
import pandas as pd
from docx import Document
from global_sensitivity_v4_4 import _evaluate_row, _cfg_ind
from global_sensitivity import INDIVIDUAL_PARAMETERS
from service_queue_simulation import CONFIGS, ArrivalDraw, simulate_one_from_stream
from dataclasses import replace
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def test_global_sensitivity_sample_size_and_primary_bounds():
    data=pd.read_csv(ROOT/'outputs/global_sensitivity_v4_4/sobol_first_total_indices.csv')
    assert (data.n_base==1024).all()
    for model,out in [('individual','response_difference_pp'),('service','mean_wait_difference_minutes')]:
        d=data[(data.model==model)&(data.outcome==out)]
        assert d.S1.sum()<=1.0
        assert (d.S1<=d.ST+1e-9).all()
    # All raw unsanitized estimates retained, including small near-zero violations.
    assert {'S1','ST','S1_Jansen','S1_gt_ST','ST_low','ST_high'}.issubset(data.columns)

def test_parameter_evidence_is_not_indiscriminately_cited():
    d=pd.read_csv(ROOT/'config/individual_parameter_dictionary_v4.3.csv').set_index('parameter')
    assert d.loc['trust_verification_bonus','supporting_references'].startswith('Not parameter-specific')
    assert d.loc['crisis_logit_intercept','supporting_references'].startswith('Not parameter-specific')
    assert '[20' in d.loc['baseline_phq9','supporting_references']
    for name in ['individual','service']:
        d2=pd.read_csv(ROOT/f'config/{name}_parameter_dictionary_v4.3.csv')
        assert not d2.supporting_references.str.contains('et al',regex=False).any()
        assert not d2.astype(str).apply(lambda col:col.str.contains('0.319999999999',regex=False).any()).any()

def test_queue_retains_work_across_nominal_days():
    cfg=replace(CONFIGS['manual'],days=2,warmup_days=0,clinician_servers=1,intake_servers=1)
    def a(day,time):
        return ArrivalDraw(day=day,arrival=time,acuity=2,z_primary_service=0.,z_fallback_service=0.,u_incomplete=1.,u_detection=0.,u_false_alert=1.,u_abandonment=1.)
    rs=simulate_one_from_stream(cfg,np.array([1.,1.]),[a(0,419.),a(1,420.),a(1,421.)])
    assert rs['arrivals']==3 and rs['completed']==3
    assert rs['mean_wait_minutes']>80  # work-in-progress crosses the 420-min boundary

def test_submission_display_counts_and_placeholder_integrity():
    doc=Document(ROOT/'manuscript/Physical_AI_Psychiatry_Manuscript_v4.4.docx')
    assert len(doc.inline_shapes)==6
    assert len(doc.tables)==4
    s=' '.join(x.text for x in doc.paragraphs)
    assert 'v4.1 outputs' not in s and 'post-review analyses' not in s.lower()
    assert 'not dynamically coupled' in s or 'intentionally uncoupled' in s
    assert 'AUTHOR INPUT REQUIRED' in s
    assert '1,024' in s

def test_pub_figures_are_svg_editable_and_nonrasterized():
    svgs=list((ROOT/'figures/submission_v4_4/svg').glob('Figure_*.svg'))
    assert len(svgs)==6
    for p in svgs:
        z=p.read_text(encoding='utf-8')
        assert '<text' in z and '<image' not in z
