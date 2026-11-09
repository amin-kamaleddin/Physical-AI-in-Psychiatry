"""Produce streamlined npj Digital Medicine v4.4 manuscript and Supplementary Information.
Reuses frozen, audited v4.3 base results; uses new N=1024 global sensitivity outputs.
"""
from __future__ import annotations
from pathlib import Path
import re, json, math
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_ORIENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
import pandas as pd
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs';FIG=ROOT/'figures'/'submission_v4_4'/'png';MAN=ROOT/'manuscript';MAN.mkdir(exist_ok=True)
ORIG=Document(ROOT/'manuscript'/'Physical_AI_Psychiatry_Integrated_Manuscript_v4.3.docx')
P={i:p.text for i,p in enumerate(ORIG.paragraphs)}
TITLE=P[0]
NAVY='183655';TEAL='006E79'

def S(f):return pd.read_csv(OUT/f)
ind=S('individual_contrast_summary.csv');svc=S('system_contrast_summary.csv')
ass=S('assumption_scenarios_v4_3/neutral_skeptical_contrast_summary.csv')
sob=S('global_sensitivity_v4_4/sobol_first_total_indices.csv');s2=S('global_sensitivity_v4_4/sobol_second_order_indices.csv')
est=S('reviewer_reanalysis/individual_estimand_sensitivity_summary.csv')
cap=S('reviewer_reanalysis/service_capacity_sensitivity_summary.csv')
gated='Embodied robot + human safety gate'
def row(df,metric):return df[(df.comparator==gated)&(df.metric==metric)].iloc[0]
def st(m,o,p):return sob[(sob.model==m)&(sob.outcome==o)&(sob.parameter==p)].iloc[0]
def F(v,d=2):return f'{float(v):.{d}f}'
def CI(r,d=2):return f"{float(r.mean_difference):+.{d}f} ({float(r.bootstrap_ci_low):.{d}f} to {float(r.bootstrap_ci_high):.{d}f})"

def shade(cell,fill):
 tcpr=cell._tc.get_or_add_tcPr(); sh=tcpr.find(qn('w:shd'))
 if sh is None:sh=OxmlElement('w:shd');tcpr.append(sh)
 sh.set(qn('w:fill'),fill)
def repeat_head(row):
 x=OxmlElement('w:tblHeader');x.set(qn('w:val'),'true');row._tr.get_or_add_trPr().append(x)
def init_doc(supp=False):
 doc=Document(); sec=doc.sections[0]
 sec.top_margin=Inches(.74);sec.bottom_margin=Inches(.73)
 sec.left_margin=sec.right_margin=Inches(.82)
 sec.header_distance=Inches(.32);sec.footer_distance=Inches(.32)
 base=doc.styles['Normal'];base.font.name='Arial';base.font.size=Pt(10.2);base.paragraph_format.space_after=Pt(4);base.paragraph_format.line_spacing=1.10
 for typ,size in [('Title',17),('Heading 1',13),('Heading 2',11.3),('Heading 3',10.6)]:
  x=doc.styles[typ];x.font.name='Arial';x.font.size=Pt(size);x.font.bold=True;x.font.color.rgb=RGBColor.from_string(NAVY)
  x.paragraph_format.space_before=Pt(9);x.paragraph_format.space_after=Pt(4);x.paragraph_format.keep_with_next=True
 foot=sec.footer.paragraphs[0];foot.alignment=WD_ALIGN_PARAGRAPH.CENTER
 foot.add_run('Supplementary information  |  ' if supp else 'Physical AI psychiatry  |  ')
 x=foot.add_run();a=OxmlElement('w:fldChar');a.set(qn('w:fldCharType'),'begin');b=OxmlElement('w:instrText');b.text='PAGE';c=OxmlElement('w:fldChar');c.set(qn('w:fldCharType'),'end');x._r.extend([a,b,c])
 return doc

def txt(doc, s, boldlead=None):
 p=doc.add_paragraph()
 if boldlead and s.startswith(boldlead):p.add_run(boldlead).bold=True;p.add_run(s[len(boldlead):])
 else:p.add_run(s)
 return p

def t(doc,title,head,rows,notes=None):
 p=doc.add_paragraph();p.paragraph_format.keep_with_next=True;p.paragraph_format.space_before=Pt(9)
 p.add_run(title).bold=True
 tab=doc.add_table(rows=1,cols=len(head));tab.alignment=WD_TABLE_ALIGNMENT.CENTER
 tab.style='Table Grid';repeat_head(tab.rows[0])
 for j,x in enumerate(head):
  cell=tab.rows[0].cells[j];cell.text=str(x);shade(cell,'DAE9ED')
  for par in cell.paragraphs:
   par.paragraph_format.space_after=Pt(1)
   for run in par.runs:run.bold=True;run.font.size=Pt(8.6);run.font.name='Arial'
 for i,r in enumerate(rows):
  rr=tab.add_row().cells
  for j,x in enumerate(r):
   rr[j].text=str(x)
   rr[j].vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   if i%2:shade(rr[j],'F2F6F8')
   for par in rr[j].paragraphs:
    par.paragraph_format.space_after=Pt(0)
    for run in par.runs:run.font.size=Pt(8.5);run.font.name='Arial'
 if notes:
  p=doc.add_paragraph();p.paragraph_format.space_before=Pt(2)
  r=p.add_run(notes);r.font.size=Pt(8.7);r.italic=True
 return tab

def fig(doc,n,stem,legend):
 pp=doc.add_paragraph();pp.alignment=WD_ALIGN_PARAGRAPH.CENTER
 pp.paragraph_format.keep_with_next=True;pp.paragraph_format.keep_together=True;pp.paragraph_format.space_before=Pt(7);pp.paragraph_format.space_after=Pt(2)
 image=pp.add_run().add_picture(str(FIG/(stem+'.png')),width=Inches(6.8))
 image._inline.docPr.set('descr',f'Figure {n}. {legend}')
 cap=doc.add_paragraph();cap.paragraph_format.keep_together=True;cap.paragraph_format.space_after=Pt(8)
 cap.add_run(f'Figure {n}. ').bold=True;cap.add_run(legend)

def add_ref(doc,s):
 p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2);p.paragraph_format.left_indent=Inches(.20);p.paragraph_format.first_line_indent=Inches(-.20)
 r=p.add_run(s);r.font.size=Pt(9.2);p.paragraph_format.line_spacing=1.0

def build_main():
 doc=init_doc()
 doc.add_paragraph(TITLE,style='Title')
 txt(doc,'[AUTHOR INPUT REQUIRED: author names, affiliations, ORCID IDs, corresponding author email]')
 txt(doc,'Article | Original Research — Simulation Study')
 doc.add_heading('Abstract',1)
 abstract=(
 'Physical artificial intelligence (AI) may improve engagement in psychiatric care but adds operational and safety burdens. '
 'We compared a matched screen with embodied pathways in two complementary, uncoupled simulations: 12-week outpatient monitoring and clinic intake. '
 'All model parameters were transparent, uncalibrated assumptions. '
 'Across 200 paired replications, human-gated robots increased modeled response by 6.29 percentage points and reduced missed high-acuity cases by 10.85 points, but reduced completion by 5.42 points, added 4.38 clinician-review minutes per participant, and increased waiting by 34.41 working minutes. '
 'When hypothesized embodiment advantages were removed, response fell 1.38 points below screen; under skeptical assumptions, response fell 8.83 points. '
 'A 1,024-base-point global sensitivity analysis using synchronized random streams showed response sensitivity to the assumed symptom increment and waiting sensitivity to demand. '
 'These are model-internal stress-test consequences, not clinical efficacy estimates. Physical AI should demonstrate both benefit and operational acceptability before deployment.'
 )
 txt(doc,abstract)
 txt(doc,'Keywords: physical AI; digital psychiatry; socially assistive robots; microsimulation; discrete-event simulation; global sensitivity; patient safety')
 doc.add_heading('Introduction',1)
 intro=[P[10],P[11],P[13],P[14]]
 intro=[x.replace('The present revision consequently adds','This study therefore reports').replace('current revision','study') for x in intro]
 for para in intro:txt(doc,para)
 txt(doc,'We study two complementary decision contexts, not a continuous patient trajectory: longitudinal outpatient monitoring and clinic intake triage. The models share pathway constructs and expose the costs of implementation, but no patient-level event feeds dynamically into the queue. Figure 1 specifies this architecture; Table 1 defines the content-matched comparisons. The proposed dual gate requires both additional patient benefit and prespecified non-worsening of access, retention and human workload; it is an evaluation principle, not a validated regulatory threshold.')
 fig(doc,1,'Figure_1_model_architecture','Complementary, independently simulated contexts. The patient microsimulation represents 12-week follow-up and the service model represents intake assessment. Arrows lead to a common decision framework; they do not denote dynamic coupling. Model parameters are illustrative, not empirically fitted.')
 t(doc,'Table 1 | Comparison pathways and contexts', ['Pathway','Longitudinal monitoring','Clinic intake','Incremental question'],[
 ['Usual/manual','Measurement-based usual care','Manual assessment','Contextual comparator'],
 ['Matched screen','Screen agent delivering matched intervention content','Digital kiosk with clinician review','Primary reference'],
 ['Embodied robot','Same digital content plus physical interface','Robot intake with faults and fallback','Bundled effects of embodiment, reliability and workflow'],
 ['Robot + human gate','Robot with mandatory risk-relevant review','Robot with mandatory clinician checks','Detection gain versus oversight and access costs']
 ],'Content was matched in the patient model, but acceptance, engagement dynamics, detection, reliability and oversight also differed. No contrast isolates the physical body as a single randomized component.')

 doc.add_heading('Results',1)
 doc.add_heading('Computational checks and model-internal contrasts',2)
 txt(doc,'Reproduced base-case data files contained 200 independent patient trials with 1,200 synthetic participants per pathway and 200 paired service replications with five warm-up and 35 observed working days. Shared baseline cohorts and paired service demand streams passed structural checks; every service arrival was accounted for as completed or abandoned. Primary-model results below are preserved from the audited base-case run. New global sensitivity results were recomputed using a separate, better-powered input design.')
 txt(doc,'Across the patient trials, mean response was 20.65% (95% bootstrap interval 20.49–20.80) for the screen and 26.94% (26.78–27.11) for the human-gated robot, whereas 12-week completion was 73.43% (73.24–73.62) and 68.00% (67.81–68.19), respectively. Figure 2a–c brings trajectories, endpoint outcomes and paired contrasts together. Patient-level review work and missed risk events, which a threshold-only report would omit, appear in Fig. 2d.')
 fig(doc,2,'Figure_2_patient_results','Patient-scale modeled outcomes. a, Mean last-observation-carried-forward PHQ-9 with 95% BCa intervals across 200 independent synthetic replications. b, Mean response, remission and completion by pathway, with 95% BCa intervals. c, Paired mean differences in percentage points between human-gated robot and screen; error bars are 95% BCa intervals. d, Review time, physical near-miss and missed-risk-week paired contrasts with bootstrap intervals; units are stated for each endpoint. Intervals reflect only fixed-model simulation precision.')
 txt(doc,f"The complete human-gated pathway improved response by {CI(row(ind,'response_percent'))} percentage points and remission by {CI(row(ind,'remission_percent'))} points, while completion was {CI(row(ind,'completion_percent'))} points. Clinician review rose by {CI(row(ind,'mean_clinician_review_minutes'))} minutes per participant and physical near-misses by {CI(row(ind,'physical_near_misses_per_100'))} per 100 participants. These findings support neither a clinical efficacy claim nor a body-only causal contrast (Table 2).")
 doc.add_heading('Access and detection trade-offs at intake',2)
 txt(doc,'The intake model generated slower queues under both robot configurations, despite near-matched throughput. In the human-gated pathway, mean waiting was 78.75 versus 44.34 working minutes for the screen, while missed high-acuity cases fell and false alerts increased. Figure 3 contrasts full replication distributions with mean estimates and safety and throughput outputs; Table 2 places both scales on the same decision surface.')
 fig(doc,3,'Figure_3_service_results','Clinic intake outcomes after a five-day warm-up. a, Distributions of within-replication mean waits across 200 paired replications; boxes indicate interquartile ranges and points individual replication outputs. b, Mean wait with 95% BCa intervals. c, Paired safety differences (the native units differ across rows and are shown explicitly) with 95% BCa intervals. d, Mean assessments per working day with 95% BCa intervals; axis is expanded to resolve small differences and is not a zero-origin bar plot. Waiting is measured in continuous working-minute time.')
 main_rows=[]
 items=[('Patient','Response','response_percent','pp',ind),('Patient','Remission','remission_percent','pp',ind),('Patient','Completion','completion_percent','pp',ind),('Patient','PHQ-9 change','mean_phq9_change','points',ind),('Patient','Review work','mean_clinician_review_minutes','minutes/person',ind),('Patient','Physical near misses','physical_near_misses_per_100','/100 persons',ind),('Service','Waiting time','mean_wait_minutes','working minutes',svc),('Service','Missed high-acuity cases','missed_high_acuity_percent','pp',svc),('Service','False alerts','false_alerts_per_100_arrivals','/100 arrivals',svc),('Service','Throughput','throughput_per_day','assessments/day',svc)]
 for scale,label,key,unit,d in items:
  r=row(d,key);main_rows.append([scale,label,unit,CI(r),'Benefit' if key in ('response_percent','remission_percent','mean_phq9_change','missed_high_acuity_percent') else 'Burden / access' if key in ('completion_percent','mean_wait_minutes','physical_near_misses_per_100','false_alerts_per_100_arrivals','mean_clinician_review_minutes') else 'Capacity'])
 t(doc,'Table 2 | Primary human-gated pathway differences versus matched screen', ['Scale','Endpoint','Unit','Mean contrast (95% BCa interval)','Interpretation'],main_rows,
   'Paired replication is the sampling unit (n=200); 10,000 BCa bootstrap resamples. Positive response/remission and negative PHQ-9 change/missed cases favor robot; greater burden or waiting and lower completion favor screen. Simulation P values hit the 100,000-draw sign-flip resolution floor and are summarized as P<0.0001 (Holm-adjusted), not exact probabilities.')

 doc.add_heading('Assumption stress tests and break-even regions',2)
 txt(doc,'Sensitivity analyses next removed hypothesized benefits or moved parameters toward adverse-but-declared ranges. With a neutral assumption set, the response contrast became −1.38 points and completion remained inferior; with skeptical assumptions, response was −8.83 points, completion −26.16 points and service waiting increased by 205.66 minutes. Figure 4a makes those joint reversals visible; Table 3 reports the corresponding model-internal confidence intervals.')
 txt(doc,'The two-way patient response grid and service waiting grid (Fig. 4b–c) show that engagement, reliability and review duration have separate roles. In the service grid, zero-margin waiting non-worsening was confined to no modeled day-level downtime with short review times, and stricter confidence-bound criteria narrowed the region further. The 250-draw nested scenario ensemble (Fig. 4d) is an illustrative range stress test, not a posterior probability of success.')
 fig(doc,4,'Figure_4_robustness','Sensitivity analyses. a, Human-gated robot minus screen contrasts under neutral and skeptical parameter settings, with 95% BCa intervals. b, Response difference over engagement-logit advantage and session downtime. c, Mean wait difference over review time and day-level downtime. d, Joint scenario-draw response and completion contrasts across 250 illustrative parameter sets; scenario proportions are descriptive of the selected ranges, not probabilities of real deployment outcomes.')
 scenrows=[]
 for kind in ('neutral','skeptical'):
  for scale,metrics in [('Patient',['response_percent','completion_percent','mean_clinician_review_minutes']),('Service',['mean_wait_minutes','false_alerts_per_100_arrivals'])]:
   for metric in metrics:
    hit=ass[(ass.scenario.str.contains(kind))&(ass.scale==scale)&(ass.metric==metric)]
    if len(hit)==1:
     r=hit.iloc[0];scenrows.append([kind.capitalize(),scale,metric.replace('_',' '),CI(r)])
 t(doc,'Table 3 | Neutral and skeptical scenario contrasts', ['Assumption set','Model','Outcome','Robot + gate minus screen (95% BCa interval)'],scenrows,
   'n=200 paired replications per scenario; these contrasts are from separate scenario-specific random streams, not a continuation of the primary replication series. Parameters and units are fully specified in Supplementary Data 1–2 and the repository.')

 doc.add_heading('Global interaction-aware sensitivity',2)
 r_resp=st('individual','response_difference_pp','embodiment_effect');r_comp=st('individual','completion_difference_pp','discomfort_dropout');r_wait=st('service','mean_wait_difference_minutes','arrivals_per_day')
 txt(doc, f"The full variance-based analysis was repeated with 1,024 scrambled Sobol base vectors, 12 patient and 11 service varied inputs, matched common-random-number streams within each design row, and 350 row-bootstrap resamples. Relative to the earlier 128-point screening design, the summed patient-response first-order indices fell within the theoretical bound (ΣS1={F(sob[(sob.model=='individual')&(sob.outcome=='response_difference_pp')].S1.sum(),3)}). Figure 5 compares total-order contributions and exploratory second-order interactions. Response was most sensitive to the assumed embodiment symptom increment (ST={F(r_resp.ST,2)}, 95% design-row interval {F(r_resp.ST_low,2)}–{F(r_resp.ST_high,2)}), completion to the embodiment-related dropout increment (ST={F(r_comp.ST,2)}), and service waiting to demand (ST={F(r_wait.ST,2)}).")
 txt(doc,'Residual small S1>ST inconsistencies persist for some near-zero indices, illustrating finite-sample numerical uncertainty; no indices were forcibly truncated, normalized or treated as exact variance shares. Pairwise interactions were exploratory: none of the patient-response S2 intervals excluded zero; one of 55 service-wait pairwise intervals excluded zero before multiplicity adjustment, so isolated interaction claims would be premature. The sensitivity results apply only to independently uniform input ranges and cannot identify real-world parameter importance without calibration and dependence modeling.')
 fig(doc,5,'Figure_5_global_sensitivity','Variance-based global sensitivity audit with 1,024 base design rows. a–c, Largest total-order Sobol estimates and 95% row-bootstrap intervals for patient response, patient completion and clinic waiting, respectively. d, Five exploratory pairwise second-order estimates for clinic waiting with 95% intervals; these comparisons are not multiplicity adjusted. Inputs were independently uniform across declared stress ranges; estimates and intervals concern only the simulation model. S1 and S2 are retained unaltered in the machine-readable repository, including finite-design violations.')
 trows=[]
 for model,out,pars in [('Patient','response_difference_pp',['embodiment_effect','discomfort_dropout','engagement_logit_advantage']),('Patient','completion_difference_pp',['discomfort_dropout','initial_refusal']),('Service','mean_wait_difference_minutes',['arrivals_per_day','downtime_day_probability','clinician_review_minutes','clinician_servers'])]:
  m='individual' if model=='Patient' else 'service'
  for par in pars:
   r=st(m,out,par)
   trows.append([model,out.replace('_',' '),r.parameter_label,F(r.ST,3),f'{F(r.ST_low,3)} to {F(r.ST_high,3)}'])
 t(doc,'Table 4 | Leading total-order Sobol sensitivity indices', ['Scale','Output contrast','Parameter','ST','95% row-bootstrap interval'],trows,
   '1,024 base points; two inner stochastic evaluations per parameter vector. Index ranges are model-conditional Monte Carlo diagnostics, not confidence intervals for causal effects or posterior parameter uncertainty. Full S1, ST, S2, denominator diagnostics and design outputs are deposited in the repository.')

 doc.add_heading('Alternative estimands, capacity and mechanism diagnostics',2)
 txt(doc,'The final analyses address two distinct alternatives: endpoint definition and implementation composition. The independently seeded attrition module found a +6.23-point response difference under last-observation-carried-forward, +5.53 under baseline-observation-carried-forward and +10.21 among completers. These values differ slightly from the +6.29-point primary LOCF contrast because the modules used separately seeded synthetic replication streams; they are not duplicate evaluations on identical participants. Figure 6a summarizes these differences, and Supplementary Table S1 retains all estimand intervals.')
 txt(doc,'Similarly, the independently seeded capacity module estimated a +36.40-minute mean-wait difference at three robot intake stations, compared with +34.41 minutes in the primary three-station model; differences stem from Monte Carlo stream choice, not changed configured capacity. Increasing robot stations to five left an approximately +36-minute penalty (Fig. 6b). One-block substitutions identified different drivers of modeled response and completion (Fig. 6c), but are neither additive nor causal mediation. Warm-up choice did not reverse queue ordering (Fig. 6d). The corresponding data are retained as Supplementary Tables S2–S3 and source CSVs.')
 fig(doc,6,'Figure_6_diagnostics','Structural and estimand diagnostics. a, Response contrasts under last-observation-carried-forward (LOCF), baseline-observation-carried-forward (BOCF) and completer-only definitions. b, Paired mean-wait differences as robot intake stations vary; the three-station point uses an independent Monte Carlo stream from the primary estimate. c, One-block pathway parameter substitutions into the screen model (diagnostic, not additive or causal). d, Warm-up comparison; queue backlogs may pass between nominal working days. Error bars in a–c are 95% BCa intervals where shown.')

 doc.add_heading('Discussion',1)
 for idx in [101,102,104,105,106,107,108]:
  text=P[idx].replace('This simulation demonstrates a multiscale separation','The complementary simulations demonstrate a decision-scale separation')
  txt(doc,text)
 txt(doc,'Increasing the global design from 128 to 1,024 base points and synchronizing latent streams improved estimator stability but did not make the indices empirical. Response and completion were most sensitive to different patient-model assumptions, while queue waiting depended on jointly varying demand, reliability and clinician work. Some S1 versus ST inequalities remained for effects near zero, and bootstrap intervals for interactions were often wide. A further simulation budget expansion, independent scramble replication and explicitly modeled parameter dependence are needed before assigning robust causal importance to pairwise interactions [36–38].')
 txt(doc,'The two contexts must not be portrayed as a dynamically linked digital twin: the 12-week model counts participant-level review over a longitudinal horizon, whereas the clinic model assigns clinician work to a one-day assessment. Thus +4.38 longitudinal review minutes per participant cannot be converted to clinic staffing without specifying panel size, contact frequency, time horizon and service coverage. For example, for a panel of M participants, required clinician hours per 12-week period would be 4.38×M/60; average weekly FTE then depends on paid weekly hours and whether that additional labor falls on the same clinician pool. This algebra is illustrative; no staffing estimate was inferred from unavailable clinic volumes.')
 txt(doc,'In the intake simulation, time is indexed in consecutive 420-minute productive working-day blocks, with unfinished service and waiting workloads carried into later blocks. It does not insert overnight closures or explicit shift endings, and the original excess-work measure is a daily workload-capacity proxy rather than observed clock-time overtime. Likewise “utilization” is scheduled service minutes relative to nominal daily clinician capacity rather than direct time-weighted occupancy. These restrictions complicate extrapolation to a clinic with overtime policies, appointment calendars, breaks and overnight delays.')
 txt(doc,P[109]);txt(doc,P[110].replace('The individual and service models are not dynamically coupled;','The individual and service models are not dynamically coupled;'))
 txt(doc,'The central contribution is a falsifiable dual-gate evaluation and a transparent experimental agenda, not evidence that physical AI is effective or harmful. A credible next phase will collect site-specific symptom/engagement and operational logs; elicit uncertain robot-specific effects from patients, clinicians, operations, privacy and human-factors experts; externally face-validate the conceptual architecture; and prespecify noninferiority margins and calibration targets [32–35]. Until those steps, the numerical break-even thresholds remain research hypotheses.')

 doc.add_heading('Methods',1)
 doc.add_heading('Design, units and modeling contexts',2)
 txt(doc,'Two models share pathway names and burden categories but are intentionally uncoupled. The longitudinal model evaluates 12 weeks of synthetic outpatient interaction and follow-up. The discrete-event model evaluates a finite-capacity clinic intake assessment and clinician triage. No real patient observations or medical records entered either model. The estimand is the expectation of each complete robot pathway minus a functionally matched screen under fixed, transparent parameter values. The comparison is bundled across hardware, engagement, acceptance, reliability, alerting and oversight; it is not an isolated causal embodiment effect.')
 doc.add_heading('Parameter selection and calibration status',2)
 txt(doc,'All 47 documented patient-model inputs and structural assumptions and all 33 service-model inputs and assumptions have a defined functional role, unit or scale, pathway value, optional neutral/skeptical value, stress range, ordering rationale and evidence class. For an exact machine-readable row-by-row account, see Supplementary Data 1 and 2; these are data tables rather than separate Supplementary Methods. The full formulas, event order, distributional assumptions, horizon and functional definitions necessary for replication are specified below and implemented in the associated Python code.')
 txt(doc,'PHQ-9 scale bounds and response/remission definitions are supported by measurement literature [20,21,31]; attrition and engagement direction classes by digital intervention evidence [27–30]; possible embodiment mechanisms by physical copresence and robot reviews [2,3,5,8,9,39]; and queue/alert-workflow categories by simulation and alarm research [17–19,40]. Those sources do not calibrate the numeric robot-specific effects, trust-update coefficients, crisis intercepts, or alert rates. These remain explicit hypothetical assumptions; parameter-dictionary references were restricted to appropriate conceptual or scale anchors and do not imply extraction of a coefficient from a cited study.')
 txt(doc,'Neutral and skeptical parameter sets remove hypothesized benefit or place burdens near adverse declared bounds. Uniform input distributions used for Sobol sensitivity are independent by construction and are not posterior estimates. Neither empirical calibration, structured stakeholder elicitation nor independent face validation has been completed. A prospective multi-stakeholder elicitation and external face-validation protocol is supplied with the repository, and any calibrated analysis must be rerun with correlated parameter distributions where justified [32–35].')
 doc.add_heading('Patient-level mathematical and operational specification',2)
 for subsection,body in [
 ('State and baseline','For participant i, pathway a and week t=1,…,12, the state is PHQ-9 Y, active indicator Z, past engagement E, trust U, and cumulative risk, alerts, downtime, fallback, review and near-miss counts. Shared baseline draws: Y(i,0)=clip[Normal(15.5,3.2),10,24]; acceptance A~Beta(2.4,1.9); privacy P~Beta(2.1,2.4); support S~Normal(0,1); responsiveness R~Normal(0,0.13) PHQ-9 units/week. Initial trust U(i,a,0)=0.08 H(a)+0.12 A(i)−0.10 P(i), with H the verification indicator. Initial refusal F~Bernoulli(rho(a)); Z(i,a,0)=1−F.'),
 ('Availability and engagement','While active, downtime D(i,a,t)~Bernoulli(d(a)), and conditional fallback B(i,a,t)~Bernoulli(f(a)); a session is available when D=0 or B=1. Engagement logit equals alpha(a)+1.05(A−0.5)−gamma_P(a)(P−0.5)+0.34 E(previous)+0.13 S+U(previous)−delta(a)(t−1)−0.025 max[Y(previous)−15,0]. Realized engagement requires both a successful Bernoulli draw and availability; fallback preserves content but removes the embodiment symptom increment.'),
 ('Symptoms and clinical events','Baseline week-specific trend b(i)=0.24+0.022 max[Y(i,0)−14,0]. Intervention increment Q(i,a,t)=E(i,a,t)[beta_content(a)+beta_emb(a)(1−B(i,a,t))]. Active symptoms evolve as Y(i,a,t)=clip{Y(previous)−[b(i)+Q(i,a,t)+R(i)]+epsilon,0,27}, epsilon~Normal(0,0.62). Worsening W=Y(new)−Y(previous). Crisis logit=−10.2+0.27Y(new)+0.42max(W,0). Alerts occur with sensitivity Se(a) in crisis weeks and false-alert probability FPR(a) otherwise. None of these coefficients is derived from observed clinical data.'),
 ('Oversight, trust and safety','False-alert escalation probabilities are 0.12 under human verification and 0.72 otherwise. Clinician review initializes at pathway-specific routine audit minutes and adds review minutes for every alert. Trust changes +0.025 for a true alert, −0.040 for an escalated false alert, and −0.075 for a missed crisis, clipped to [−0.5,0.5]. A physical near-miss is Bernoulli(h(a)) only for available, nonfallback embodied sessions; it is a synthetic noninjury placeholder.'),
 ('Dropout and endpoints','For active participants, p_drop=clip[0.010+0.030(1−E)+0.016P+kappa(a)+0.010 I(W>1.5)−0.008E,0.002,0.12]. Dropout is Bernoulli(p_drop), with absorbing inactive state. Completion requires activity through week 12; response is ≥50% PHQ-9 reduction, remission Y≤4. Primary missingness handling is last observation carried forward after attrition; BOCF and completer-only results are alternative estimands rather than evidence of missing-data validity.')
 ]:
  doc.add_heading(subsection,3);txt(doc,body)
 doc.add_heading('Clinic discrete-event mathematical and operational specification',2)
 for subsection,body in [
 ('Arrivals, time axis and resources','In each replication, five warm-up days precede 35 observed days; one day is L=420 productive working minutes. Daily arrivals N(d)~Poisson(lambda); within-day timestamps are sorted Uniform(0,L) shifted by dL. Low/medium/high acuity probabilities are 0.60/0.30/0.10. Intake, fallback and clinician resources each maintain a heap of next-available working-minute times. Start=max(arrival,minimum resource availability), finish=start+duration, and the resource heap is updated. A FIFO queue is never reset at day boundaries: an arrival near minute 420 may wait into the next 420-minute block. The time axis compresses overnight/nonworking periods, rather than assuming real-time work during nights. No explicit end-of-shift overtime operation is modeled.'),
 ('Intake, downtime and rework','For each model day, a common outage uniform determines whether the digital pathway uses its available fallback resource. Primary intake duration=max(4,mu_intake+sigma_intake×standard normal) plus any routine reset minutes; fallback duration=max(4,mu_fallback+4×standard normal). Digital incompleteness is a Bernoulli event with probability q(a) and consumes extra rework duration on the fallback resource. Reset work is not an incident or injury rate.'),
 ('Detection, clinician activity and abandonment','An alert occurs with sensitivity Se(a) among high-acuity arrivals and false-alert rate FPR(a) otherwise. Baseline clinician assessment minutes are 38,52,72 for low,medium,high acuity. Final clinician duration=max(base−summary_saving(a),25)+I(digital)×review_minutes(a)+I(alert)×[6H(a)+10(1−H(a))]. Predicted wait=max(intake_finish, earliest_clinician_availability)−arrival; abandonment risk=min{0.25,logistic[−5.2+0.010max(predicted_wait−120,0)]}. Abandoned arrivals never enter clinician service; completed waiting time=clinician_start−arrival.'),
 ('Boundary, denominators and outputs','Observed arrivals are classified by their arrival day after warm-up, even when downstream clinician completion occurs beyond the nominal observation boundary. Therefore “completed per observed day” is an observed-arrival-cohort throughput ratio, not a censored clock-time completion count. Arrivals=completed+abandoned exactly. Mean and 90th-percentile waits are computed among completed arrivals. False alerts use all observed arrivals as denominator; missed high-acuity cases use observed high-acuity arrivals. Clinician workload-to-capacity is assigned clinician service minutes for the observed arrival cohort to that cohort’s arrival day, divided by nominal 420×clinician-server minutes; reported excess above capacity is a workload proxy, not directly simulated calendar overtime. Intakes and fallback work are analogously attributed to arrival day. A full site scheduling model would have to add shifts, overnight closures, unfinished-work censored analyses, appointment/no-show logic and staff breaks.')
 ]:
  doc.add_heading(subsection,3);txt(doc,body)
 doc.add_heading('Primary statistical analysis and module-specific streams',2)
 txt(doc,'The independent simulation replication (not an individual record or arrival) is the uncertainty unit. Arms within each patient replication share a baseline cohort; service pathways within each queue replication share demand, acuity and latent event draws. Contrasts were resampled as intact pairs for two-sided 95% BCa bootstrap mean intervals (10,000 resamples for primary endpoints; 5,000 arm means; 3,000 selected diagnostic grids). The base-case analysis used n=200 paired replications. Simulation MCSE equals the standard deviation of paired replication contrasts divided by √200. The alternative two-sided paired sign-flip randomization test used 100,000 draws and a plus-one correction; Holm adjustment was applied across seven prespecified outcomes per comparator and model, with nominal alpha=.05. At the Monte Carlo floor, the smallest unadjusted P is 1/100,001=0.0000099999 and the smallest seven-test adjusted P is approximately 0.000070; both are reported as P<0.0001, not as estimates of extreme real-world tail probability. Paired t tests and standardized dz were concordance diagnostics [24–26].')
 txt(doc,'The original primary, attrition, capacity, ablation, and scenario modules intentionally use separate deterministic analysis-label seeds. Repeating nominally identical configurations in different modules therefore generates slightly different Monte Carlo means and intervals. All differences retain their unaltered original output files; this distinction is explicit in Results and Supplementary Table S4. No significance claim is based on treating those independently sampled outputs as exact replicates.')
 doc.add_heading('Sensitivity estimators and quality control',2)
 txt(doc,'The patient grid varied engagement-logit advantage 0–0.35 and session downtime 0–30%, and the service grid day downtime 0–30% and review time 4–24 min. A separate 250-draw multivariate scenario ensemble used five inner stochastic replications per scenario. Neutral/skeptical tests each used 200 paired replications. Sobol global analysis used 12 varied patient and 11 service parameters with independently Uniform inputs over registered stress ranges. A scrambled 2d-dimensional Sobol sequence defined two N=1,024 matrices A and B, their d AB matrices and d BA matrices (N×[2d+2] model evaluations per scale). Within each design row, each A/B/AB/BA evaluation shared identical synthetic-cohort and event seeds; for service demand, a maximum-rate Poisson stream was Bernoulli-thinned with fixed per-arrival uniforms so differing arrival rates preserved CRN nesting. Each parameter vector was averaged over two independent matched stochastic replications (350 synthetic participants per arm, or 18 observed service days following warm-up).')
 txt(doc,'First-order S1 was estimated by the Saltelli covariance estimator mean[Y_B×(Y_ABi−Y_A)]/Var(Y); total-order ST by Jansen’s squared-difference estimator mean[(Y_A−Y_ABi)^2]/[2Var(Y)]. Pairwise S2 used the Saltelli BA/AB cross-product correction with first-order terms subtracted. Row bootstrap intervals used 350 resamples, maintaining matrix-row alignment. All raw estimates are retained, even if finite-design effects yield S1<0, S1>ST, ΣS1>1 or uninformative S2 intervals. Interpretation concentrates on stable total-order ranking, while individual S1 violations near zero and unadjusted pairwise interactions are declared exploratory. The full input matrices, outputs, estimator diagnostics and code are deposited. The 1,024-point rerun uses different numerical random streams from the earlier 128-point audit and therefore replaces—not silently augments—the earlier global estimates [36–38].')
 doc.add_heading('Software, reporting, ethical and AI-use disclosures',2)
 txt(doc,'Python, NumPy, pandas, SciPy, Matplotlib and python-docx were used; exact versions are pinned in requirements-lock.txt. The full code, design matrices, synthetic data, tests, figure-generation scripts and SHA-256 manifest are provided in the accompanying reproducibility repository. Tests verify deterministic stream matching, range and impossibility constraints, queue accounting, model outputs, and figure-editable text. The reporting approach follows STRESS and ISPOR-SMDM model-transparency guidance [18,19]. No real human data, tissue or participant interactions were used, so no human research ethics approval or consent was required for the computational work described here; authors must confirm this characterization under their institution’s policies.')
 txt(doc,'Use of AI-assisted tools: OpenAI ChatGPT was used in preparing draft editorial text, reviewing code and developing reproducibility artifacts. All scientific interpretations, source accuracy, analysis outputs and final text require author verification; the human authors retain responsibility for the submission. [AUTHOR VERIFICATION REQUIRED: verify this description against actual use.]')
 doc.add_heading('Data availability',1)
 txt(doc,'Synthetic simulation inputs and machine-readable outputs, including complete Saltelli design/output matrices and parameter dictionaries, are contained in the accompanying repository. [AUTHOR INPUT REQUIRED: insert public repository name, persistent release URL and DOI after deposit; no DOI has yet been assigned.]')
 doc.add_heading('Code availability',1)
 txt(doc,'Complete Python simulation, validation, sensitivity and plotting scripts are included in the accompanying versioned repository, with environment specifications and an end-to-end reproduction workflow. [AUTHOR INPUT REQUIRED: choose and confirm an authorized open-source license, release tag and archived DOI.]')
 doc.add_heading('Acknowledgements',1)
 txt(doc,'[AUTHOR INPUT REQUIRED: acknowledgements and funding source/grant information, or an affirmative statement that no external funding was received.]')
 doc.add_heading('Author contributions',1)
 txt(doc,'[AUTHOR INPUT REQUIRED: identify every author by initials and specify CRediT contributions.]')
 doc.add_heading('Competing interests',1)
 txt(doc,'[AUTHOR INPUT REQUIRED: declare every author’s financial and non-financial competing interests, or state explicitly if none.]')
 doc.add_heading('References',1)
 for i in range(166,206):
  add_ref(doc,P[i])
 path=MAN/'Physical_AI_Psychiatry_Manuscript_v4.4.docx';doc.save(path);return path

def build_supp():
 doc=init_doc(supp=True)
 doc.add_paragraph('Supplementary Information',style='Title')
 txt(doc,TITLE)
 txt(doc,'Reproducibility companion: supplementary numerical contrasts and parameter evidence mapping. All operational model specifications and mathematical equations are in the main manuscript Methods; the large complete dictionaries are supplied separately as Supplementary Data 1–2.')
 doc.add_heading('Supplementary display and data index',1)
 t(doc,'Supplementary Data index',['Item','Description','Location'],[
 ['Supplementary Data 1','47 patient-model input, coefficient and structural rows; units, pathways, ranges, selection rationale, evidence class, citations and calibration status','Supplementary_Data_1_Individual_Parameter_Dictionary.csv'],
 ['Supplementary Data 2','33 service-model input and structural rows with equivalent provenance fields','Supplementary_Data_2_Service_Parameter_Dictionary.csv'],
 ['Supplementary Data 3','Full first/total-order Sobol results, bootstrap uncertainty and finite-design diagnostics','outputs/global_sensitivity_v4_4/sobol_first_total_indices.csv'],
 ['Supplementary Data 4','All patient/service pairwise interaction indices and uncertainty','outputs/global_sensitivity_v4_4/sobol_second_order_indices.csv'],
 ['Supplementary Data 5','All Saltelli input matrices and evaluated output matrices','outputs/global_sensitivity_v4_4/raw/'],
 ])
 doc.add_heading('Supplementary Table S1 | Alternative patient estimands',1)
 tbl=[]
 for _,r in est.iterrows():
  if r.metric=='completion_percent':continue
  tbl.append([r.metric.replace('_',' '),F(r.robot_minus_screen_mean),f'{F(r.bootstrap_ci_low)} to {F(r.bootstrap_ci_high)}',str(int(r.replications))])
 t(doc,'Table S1. Full endpoint estimand sensitivity', ['Outcome/estimand','Mean contrast','95% BCa interval','Replications'],tbl,
   'This independent analysis module uses deterministic seeds different from the primary simulation; compare directions and intervals rather than treating its LOCF estimate as an exact remeasurement of the same synthetic cohort.')
 doc.add_heading('Supplementary Table S2 | Service intake capacity',1)
 trows=[]
 d=cap[cap.metric=='mean_wait_difference_minutes'].sort_values('robot_intake_servers')
 for _,r in d.iterrows(): trows.append([int(r.robot_intake_servers),F(r.robot_minus_screen_mean),f'{F(r.bootstrap_ci_low)} to {F(r.bootstrap_ci_high)}'])
 t(doc,'Table S2. Mean working-minute wait versus robot intake station count',['Robot stations','Mean difference (minutes)','95% BCa interval'],trows,
   'Screen station count remains fixed. This sensitivity experiment uses an independent label-derived random stream; the 3-station value need not equal the base-case estimate.')
 doc.add_heading('Supplementary Table S3 | Pathway component diagnostics',1)
 abl=S('reviewer_reanalysis/patient_pathway_bundle_ablation_summary.csv');trows=[]
 for _,r in abl.iterrows():
  if r.metric in ('response_difference_percentage_points','completion_difference_percentage_points','review_minutes_difference','physical_near_misses_difference'):
   trows.append([r.parameter_block,r.metric.replace('_',' '),F(r.mean_difference_vs_screen),f'{F(r.bootstrap_ci_low)} to {F(r.bootstrap_ci_high)}'])
 t(doc,'Table S3. One-block-at-a-time model substitutions',['Block','Outcome','Mean contrast','95% BCa interval'],trows,'Not additive or causal mediation. Distinct pseudo-random streams, 120 repeated model trials, and bundle-specific parameter substitutions.')
 doc.add_heading('Supplementary Table S4 | Repeated base-case configurations in distinct modules',1)
 r0=row(ind,'response_percent').mean_difference
 e=est[est.metric=='response_locf_percent'].iloc[0].robot_minus_screen_mean
 f=S('reviewer_reanalysis/patient_pathway_bundle_ablation_summary.csv')
 full=f[(f.parameter_block.str.contains('Full'))&(f.metric=='response_difference_percentage_points')]
 capacity=d[d.robot_intake_servers==3].iloc[0].robot_minus_screen_mean
 t(doc,'Table S4. Independent Monte Carlo stream comparison',['Metric','Primary experiment','Sensitivity experiment','Why values differ'],[
 ['Response (pp)',F(r0),f'{F(e)} (alternative estimand); '+(f'{F(full.iloc[0].mean_difference_vs_screen)} (full bundle)' if len(full) else 'Full bundle, separate stream'),'Different label-derived cohort and event seeds'],
 ['Completion (pp)',F(row(ind,'completion_percent').mean_difference),'−5.40 (alternative estimand); −5.56 (full bundle)','Different label-derived cohort and event seeds'],
 ['Review minutes/person',F(row(ind,'mean_clinician_review_minutes').mean_difference),'+4.36 (full bundle)','Independent bundle experiment'],
 ['Service wait (min)',F(row(svc,'mean_wait_minutes').mean_difference),F(capacity)+' (3 stations)','Different service demand and latent event streams'],
 ['Service throughput/day',F(row(svc,'throughput_per_day').mean_difference,3),'−0.178 (3 stations)','Different service demand and latent event streams']
 ],'None of these differences represents a changed physical model setting; each module estimates a fixed-configuration mean using its own Monte Carlo sample. Values are not pooled across modules.')
 doc.add_heading('Supplementary Table S5 | Model and deployment validation status',1)
 t(doc,'Table S5. Evidence needed before real-world decision use',['Process','Status','Author or investigator action'],[
 ['Deterministic computational checks','Completed for the released model','Continue CI and code review'],
 ['Fixed-assumption stochastic verification','Completed','Reassess after model changes'],
 ['Structured stakeholder elicitation','Not completed','Recruit patients, clinicians, operations, robotics, privacy/human factors and modeling experts'],
 ['Empirical parameter calibration','Not completed','Collect site, device and patient observational or trial data'],
 ['Independent conceptual face validation','Not completed','Predefine acceptance criteria and record panel feedback'],
 ['External predictive validation','Not completed','Evaluate model outputs against held-out clinical sites'],
 ['Decision threshold specification','Not completed','Prespecify noninferiority margins and acceptable implementation risk']
 ])
 doc.add_heading('Supplementary Table S6 | Global estimator diagnostics',1)
 diag=S('global_sensitivity_v4_4/estimator_diagnostics.csv');rows=[]
 for _,r in diag.iterrows():
  rows.append([r.model,r.outcome.replace('_',' '),F(r.sum_first_order,3),int(r.violating_pairs)])
 t(doc,'Table S6. Finite-design variance decomposition checks',['Model','Output','Sum first-order estimates','Rows where estimated S1 > ST'],rows,
   'Exact Sobol variance contributions obey 0 ≤ S1 ≤ ST ≤ 1 and ΣS1 ≤ 1; finite-sample estimators need not. Nonphysical estimates were not clipped or renormalized. Low-contribution effects with S1 > ST are not interpreted.')
 doc.add_heading('Source-specific parameter provenance',1)
 txt(doc,'The parameter tables were audited to remove generic citations on coefficients that no study estimated. References in Supplementary Data 1–2 now give only relevant scale anchors or conceptual rationale, explicitly identify when the numerical magnitude is a hypothesis, and otherwise say “Not parameter-specific: uncalibrated structural or operational assumption.” A coefficient of +0.025 for trust updates or −10.2 for a synthetic crisis logit is never presented as validated by a PHQ-9 scale or app-dropout publication. Floating-point strings such as 0.31999999999999995 were normalized to readable precision without altering executable configuration values.')
 txt(doc,'All 40 numbered references are retained in the main manuscript. Supplementary evidence citations use the same [n] numbering; no separate author-year sequence is introduced.')
 path=MAN/'Physical_AI_Psychiatry_Supplementary_Information_v4.4.docx';doc.save(path);return path

if __name__=='__main__':
 print('manuscript',build_main());print('supplement',build_supp())
