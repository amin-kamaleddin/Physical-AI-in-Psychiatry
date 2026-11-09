"""Draft cover letter requiring author verification; no invented identities/declarations."""
from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt
ROOT=Path(__file__).resolve().parent
D=Document();s=D.sections[0];s.left_margin=s.right_margin=Inches(.8);s.top_margin=Inches(.7);s.bottom_margin=Inches(.7)
f=D.styles['Normal'].font;f.name='Arial';f.size=Pt(10)
D.add_paragraph('[Date and corresponding-author contact information — AUTHOR INPUT REQUIRED]')
D.add_paragraph('Editorial Office\nnpj Digital Medicine')
D.add_paragraph('Re: Original Research Article submission')
D.add_paragraph('Dear Editors,')
D.add_paragraph('We submit for consideration our original simulation study, “Reimagining Psychiatric Care with Physical AI: Multiscale Simulation Stress Tests of Benefit, Burden, and Break-Even Conditions.” [The journal states a 15-word punctuation-free title preference; a shorter alternative is supplied in the submission checklist for author approval.]')
D.add_paragraph('The paper evaluates a clinically important but frequently overlooked design question: when can physically embodied AI offer value beyond a functionally matched screen after clinician labor, completion, access, alert burden, reliability and physical exposure are considered? We use two complementary, explicitly uncoupled, transparent synthetic models—12-week patient-level outpatient monitoring and clinic intake discrete-event simulation—to explore this joint requirement.')
D.add_paragraph('The main article presents six connected multi-panel figures and four summary tables, with complete mathematical and operational methods; comprehensive input dictionaries and secondary diagnostics accompany the manuscript as supplementary data. In response to reproducibility concerns, we increased the scrambled Sobol global-sensitivity base design from 128 to 1,024, synchronized common random numbers across each design row, and retained first-, total-, and pairwise second-order diagnostics with uncertainty measures. Distinct independently seeded sensitivity streams and queue-day boundary mechanics are explicitly disclosed.')
D.add_paragraph('Our study is an assumption-driven computational stress test, not a clinical trial and not evidence that physically embodied AI has established clinical efficacy. Parameters have not been empirically calibrated or independently face-validated. We argue that these transparent uncertainties are useful for specifying future clinical, operational, engineering and implementation evaluation requirements.')
D.add_paragraph('[AUTHOR INPUT REQUIRED: confirm originality, all-author approval, conflicts, related submissions, ethics applicability, data/code archival DOI and authorized license. Do not submit before all items are verified.]')
D.add_paragraph('Sincerely,\n[Corresponding author name, credentials, institution and email — AUTHOR INPUT REQUIRED]')
D.save(ROOT/'manuscript/Physical_AI_Psychiatry_Cover_Letter_v4.4.docx')
