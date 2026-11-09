"""Build the v4.2 integrated narrative manuscript and cover letter.

This revision is narrative-only: it consumes the audited v4.1 numerical outputs
and existing publication figures without rerunning either simulation model.
All main and formerly supplementary tables/figures are embedded at their first
substantive discussion and renumbered in one continuous sequence.
"""
from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from individual_microsimulation import ARM_CONFIGS
from service_queue_simulation import CONFIGS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
REVIEW_OUT = OUT / "reviewer_reanalysis"
FIG = ROOT / "figures" / "journal" / "png"
MAN = ROOT / "manuscript"
MAN.mkdir(exist_ok=True)

TITLE = "Reimagining Psychiatric Care with Physical AI: Multiscale Simulation Stress Tests of Benefit, Burden, and Break-Even Conditions"
SHORT_TITLE = "Physical AI in psychiatric care"
VERSION = "4.2"
REVISION_DATE = "30 July 2026"

REFERENCES = [
    "Fiske A, Henningsen P, Buyx A. Your Robot Therapist Will See You Now: Ethical Implications of Embodied Artificial Intelligence in Psychiatry, Psychology, and Psychotherapy. J Med Internet Res. 2019;21(5):e13216. doi:10.2196/13216.",
    "Guemghar I, Pires de Oliveira Padilha P, Abdel-Baki A, Jutras-Aswad D, Paquette J, Pomey MP. Social Robot Interventions in Mental Health Care and Their Outcomes, Barriers, and Facilitators: Scoping Review. JMIR Ment Health. 2022;9(4):e36094. doi:10.2196/36094.",
    "Kling M, Haeussl A, Dalkner N, et al. Social robots in adult psychiatry: a summary of utilisation and impact. Front Psychiatry. 2025;16:1506776. doi:10.3389/fpsyt.2025.1506776.",
    "Jung HW, Park JY, Holoubek T, Kim WJ, Park J. Socially Assistive Robots in Mental Healthcare: Principles and Conceptual Framework for User-Centered Design. Int J Soc Robot. 2025;17:2827-2851. doi:10.1007/s12369-025-01323-5.",
    "Konijn EA, Peeper G, Portegies T, Garnefski N, Kraaij V, Struijs S. Examining the Potential of Social Robots to Increase Adherence in Internet-based CBT. Int J Soc Robot. 2026;18(6):83. doi:10.1007/s12369-026-01417-8.",
    "Deng E, Mutlu B, Mataric MJ. Embodiment in Socially Interactive Robots. Found Trends Robot. 2019;7(4):251-356. doi:10.1561/2300000056.",
    "Rabbitt SM, Kazdin AE, Scassellati B. Integrating socially assistive robotics into mental healthcare interventions: applications and recommendations for expanded use. Clin Psychol Rev. 2015;35:35-46. doi:10.1016/j.cpr.2014.07.001.",
    "Li J. The benefit of being physically present: A survey of experimental works comparing copresent robots, telepresent robots and virtual agents. Int J Hum Comput Stud. 2015;77:23-37. doi:10.1016/j.ijhcs.2015.01.001.",
    "Bainbridge WA, Hart JW, Kim ES, Scassellati B. The Benefits of Interactions with Physically Present Robots over Video-Displayed Agents. Int J Soc Robot. 2011;3(1):41-52. doi:10.1007/s12369-010-0082-7.",
    "Pu L, Moyle W, Jones C, Todorovic M. The Effectiveness of Social Robots for Older Adults: A Systematic Review and Meta-Analysis of Randomized Controlled Studies. Gerontologist. 2019;59(1):e37-e51. doi:10.1093/geront/gny046.",
    "Yu C, Sommerlad A, Sakure L, Livingston G. Socially assistive robots for people with dementia: Systematic review and meta-analysis of feasibility, acceptability and the effect on cognition, neuropsychiatric symptoms and quality of life. Ageing Res Rev. 2022;78:101633. doi:10.1016/j.arr.2022.101633.",
    "Nichol B, McCready J, Erfani G, et al. Exploring the impact of socially assistive robots on health and wellbeing across the lifespan: An umbrella review and meta-analysis. Int J Nurs Stud. 2024;153:104730. doi:10.1016/j.ijnurstu.2024.104730.",
    "Scassellati B, Boccanfuso L, Huang CM, et al. Improving social skills in children with ASD using a long-term, in-home social robot. Sci Robot. 2018;3(21):eaat7544. doi:10.1126/scirobotics.aat7544.",
    "Torous J, Bucci S, Bell IH, et al. The growing field of digital psychiatry: current evidence and the future of apps, social media, chatbots, and virtual reality. World Psychiatry. 2021;20(3):318-335. doi:10.1002/wps.20883.",
    "Torous J, Linardon J, Goldberg SB, et al. The evolving field of digital mental health: current evidence and implementation issues for smartphone apps, generative artificial intelligence, and virtual reality. World Psychiatry. 2025;24(2):156-174. doi:10.1002/wps.21299.",
    "Greenhalgh T, Wherton J, Papoutsi C, et al. Beyond Adoption: A New Framework for Theorizing and Evaluating Nonadoption, Abandonment, and Challenges to the Scale-Up, Spread, and Sustainability of Health and Care Technologies. J Med Internet Res. 2017;19(11):e367. doi:10.2196/jmir.8775.",
    "Kim B, Elstein Y, Shiner B, Konrad R, Pomerantz AS, Watts BV. Use of discrete event simulation to improve a mental health clinic. Gen Hosp Psychiatry. 2013;35(6):668-670. doi:10.1016/j.genhosppsych.2013.06.004.",
    "Monks T, Currie CSM, Onggo BS, Robinson S, Kunc M, Taylor SJE. Strengthening the reporting of empirical simulation studies: Introducing the STRESS guidelines. J Simul. 2019;13(1):55-67. doi:10.1080/17477778.2018.1442155.",
    "Eddy DM, Hollingworth W, Caro JJ, Tsevat J, McDonald KM, Wong JB. Model transparency and validation: a report of the ISPOR-SMDM Modeling Good Research Practices Task Force-7. Med Decis Making. 2012;32(5):733-743. doi:10.1177/0272989X12454579.",
    "Kroenke K, Spitzer RL, Williams JBW. The PHQ-9: Validity of a Brief Depression Severity Measure. J Gen Intern Med. 2001;16(9):606-613. doi:10.1046/j.1525-1497.2001.016009606.x.",
    "Coley RY, Boggs JM, Beck A, et al. Defining Success in Measurement-Based Care for Depression: A Comparison of Common Metrics. Psychiatr Serv. 2020;71(4):312-318. doi:10.1176/appi.ps.201900295.",
    "Vasey B, Nagendran M, Campbell B, et al. Reporting guideline for the early-stage clinical evaluation of decision support systems driven by artificial intelligence: DECIDE-AI. Nat Med. 2022;28(5):924-933. doi:10.1038/s41591-022-01772-9.",
    "Liu X, Cruz Rivera S, Moher D, Calvert MJ, Denniston AK; SPIRIT-AI and CONSORT-AI Working Group. Reporting guidelines for clinical trial reports for interventions involving artificial intelligence: the CONSORT-AI extension. Nat Med. 2020;26(9):1364-1374. doi:10.1038/s41591-020-1034-x.",
    "Morris TP, White IR, Crowther MJ. Using simulation studies to evaluate statistical methods. Stat Med. 2019;38(11):2074-2102. doi:10.1002/sim.8086.",
    "Efron B, Tibshirani RJ. An Introduction to the Bootstrap. New York: Chapman & Hall; 1993.",
    "Desharnais B, Camirand-Lemyre F, Mireault P, Skinner CD. Determination of confidence intervals in non-normal data: application of the bootstrap to cocaine concentration in femoral blood. J Anal Toxicol. 2015;39(2):113-117. doi:10.1093/jat/bku127.",
]


def fmt(x: float, d: int = 2) -> str:
    return f"{float(x):.{d}f}"


def signed(x: float, d: int = 2) -> str:
    return f"{float(x):+.{d}f}"


def interval(row: pd.Series, d: int = 2) -> str:
    return f"{signed(row['mean_difference'], d)} ({fmt(row['bootstrap_ci_low'], d)} to {fmt(row['bootstrap_ci_high'], d)})"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def choose(df: pd.DataFrame, comparator: str, metric: str) -> pd.Series:
    hit = df[(df["comparator"] == comparator) & (df["metric"] == metric)]
    if len(hit) != 1:
        raise RuntimeError((comparator, metric, len(hit)))
    return hit.iloc[0]


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld1, instr, fld2])


def setup_doc(doc: Document) -> None:
    sec = doc.sections[0]
    sec.top_margin = Inches(0.72)
    sec.bottom_margin = Inches(0.72)
    sec.left_margin = Inches(0.78)
    sec.right_margin = Inches(0.78)
    sec.header_distance = Inches(0.25)
    sec.footer_distance = Inches(0.25)
    add_page_number(sec.footer.paragraphs[0])

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.font.size = Pt(9.6)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08

    for style_name, size in [("Title", 17), ("Heading 1", 13.5), ("Heading 2", 11.5), ("Heading 3", 10.5)]:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string("17324D")
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.keep_with_next = True


def add_text(doc: Document, text: str, *, italic: bool = False, align=None, keep_with_next: bool = False) -> None:
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    p.paragraph_format.keep_with_next = keep_with_next
    r = p.add_run(text)
    r.italic = italic


def add_table(doc: Document, number: int, title: str, headers: list[str], rows: list[list[str]], *, font_size: float = 7.3) -> None:
    cap = doc.add_paragraph()
    cap.paragraph_format.keep_with_next = True
    cap.paragraph_format.space_before = Pt(7)
    cap.paragraph_format.space_after = Pt(3)
    r = cap.add_run(f"Table {number}. {title}")
    r.bold = True

    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    hdr = table.rows[0]
    set_repeat_table_header(hdr)
    for i, text in enumerate(headers):
        cell = hdr.cells[i]
        cell.text = str(text)
        set_cell_shading(cell, "D9E6F2")
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for p in cell.paragraphs:
            p.paragraph_format.space_after = Pt(0)
            for rr in p.runs:
                rr.bold = True
                rr.font.name = "Arial"
                rr.font.size = Pt(font_size)
    for row_idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for rr in p.runs:
                    rr.font.name = "Arial"
                    rr.font.size = Pt(font_size)
        if row_idx % 2 == 1:
            for cell in cells:
                set_cell_shading(cell, "F7F9FB")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def add_figure(doc: Document, number: int, title: str, caption: str, filename: str, *, width: float = 6.65) -> None:
    img = FIG / filename
    if not img.exists():
        raise FileNotFoundError(img)
    pimg = doc.add_paragraph()
    pimg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pimg.paragraph_format.space_before = Pt(4)
    pimg.paragraph_format.space_after = Pt(2)
    pimg.paragraph_format.keep_with_next = True
    pimg.add_run().add_picture(str(img), width=Inches(width))

    cap = doc.add_paragraph()
    cap.paragraph_format.space_after = Pt(6)
    cap.paragraph_format.keep_together = True
    rr = cap.add_run(f"Figure {number}. {title}. ")
    rr.bold = True
    cap.add_run(caption)


def get_data():
    ind = pd.read_csv(OUT / "individual_contrast_summary.csv")
    sys = pd.read_csv(OUT / "system_contrast_summary.csv")
    ind_arm = pd.read_csv(OUT / "individual_arm_replication_summary.csv").set_index("arm")
    sys_arm = pd.read_csv(OUT / "system_scenario_summary.csv").set_index("scenario")
    est = pd.read_csv(REVIEW_OUT / "individual_estimand_sensitivity_summary.csv").set_index("metric")
    nested = pd.read_csv(REVIEW_OUT / "individual_parameter_uncertainty_nested_summary.csv").set_index("diagnostic")
    cap = pd.read_csv(REVIEW_OUT / "service_capacity_sensitivity_summary.csv")
    abl = pd.read_csv(REVIEW_OUT / "patient_pathway_bundle_ablation_summary.csv")
    return ind, sys, ind_arm, sys_arm, est, nested, cap, abl


def build_manuscript() -> Path:
    ind, sys, ind_arm, sys_arm, est, nested, cap, abl = get_data()
    gated = ARM_CONFIGS["robot_hitl"].name
    screen = ARM_CONFIGS["screen_agent"].name
    sys_gated = CONFIGS["robot_hitl"].name
    sys_screen = CONFIGS["screen"].name

    r_response = choose(ind, gated, "response_percent")
    r_remission = choose(ind, gated, "remission_percent")
    r_completion = choose(ind, gated, "completion_percent")
    r_change = choose(ind, gated, "mean_phq9_change")
    r_review = choose(ind, gated, "mean_clinician_review_minutes")
    r_near = choose(ind, gated, "physical_near_misses_per_100")
    r_missed = choose(ind, gated, "missed_crises_per_100_crisis_weeks")
    s_wait = choose(sys, sys_gated, "mean_wait_minutes")
    s_throughput = choose(sys, sys_gated, "throughput_per_day")
    s_false = choose(sys, sys_gated, "false_alerts_per_100_arrivals")
    s_missed = choose(sys, sys_gated, "missed_high_acuity_percent")
    s_abandon = choose(sys, sys_gated, "abandonment_percent")
    s_util = choose(sys, sys_gated, "mean_clinician_utilization_percent")

    abstract = (
        "Physical artificial intelligence may increase engagement in psychiatric care, but embodiment also introduces refusal, downtime, physical exposure, and human oversight. "
        "We developed an assumption-driven 12-week microsimulation and psychiatric intake discrete-event model comparing embodied pathways with a content-matched screen. "
        f"Across 200 paired replications, the human-gated robot increased modeled response by {fmt(r_response['mean_difference'])} percentage points and reduced missed high-acuity cases by {fmt(abs(s_missed['mean_difference']))} points, but reduced completion by {fmt(abs(r_completion['mean_difference']))} points, added {fmt(r_review['mean_difference'])} review minutes per participant, and increased mean wait by {fmt(s_wait['mean_difference'])} working minutes. "
        "Attrition-estimand sensitivity preserved the response direction, while component analyses showed that the contrast arose from bundled embodiment, engagement, acceptance, reliability, and oversight assumptions. "
        "These synthetic results do not establish clinical efficacy or safety. They support a dual requirement for empirical evaluation: incremental patient benefit and operational acceptability against a matched screen."
    )

    doc = Document()
    setup_doc(doc)
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(TITLE)
    add_text(doc, "[Insert author names, degrees, affiliations, ORCID identifiers, and corresponding-author email]", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, "Article type: Original Research - Simulation Study", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, f"Short title: {SHORT_TITLE}", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, f"Narrative and integrated-display revision: {REVISION_DATE}", align=WD_ALIGN_PARAGRAPH.CENTER)

    doc.add_heading("Abstract", level=1)
    add_text(doc, abstract)
    add_text(doc, f"Abstract word count: {word_count(abstract)}")
    add_text(doc, "Keywords: physical artificial intelligence; psychiatry; social robotics; microsimulation; discrete-event simulation; implementation science")

    doc.add_heading("Introduction", level=1)
    add_text(doc, "Physical artificial intelligence extends digital psychiatry from software-only interaction to systems that perceive, reason, communicate, and act through a body. Socially assistive robots have been proposed as coaching, companionship, assessment, and structured-intervention interfaces in mental health care [1-7]. Human-robot interaction research also indicates that physical copresence can alter persuasion, trust, personal space, social salience, and task performance relative to screen-displayed agents, although physical presence should not be conflated with embodiment as an isolated mechanism [8,9]. These findings provide a plausible rationale for testing embodied psychiatric interfaces, but they do not establish clinical benefit.")
    add_text(doc, "The empirical evidence remains early and heterogeneous. Mental-health reviews describe small studies spanning different diagnoses, age groups, robots, comparators, and outcomes [2,3]. Broader systematic reviews and meta-analyses report feasibility and occasional improvements in engagement, interaction, mood, or depressive symptoms, but pooled effects on clinical and quality-of-life outcomes are inconsistent and frequently limited by bias, heterogeneity, and short follow-up [10-12]. Longitudinal home deployments demonstrate that sustained interaction is technically possible in selected populations [13], while a recent content-matched comparison in internet-based cognitive behavioral therapy found higher alliance, adherence, and satisfaction for a physically present robot without a significant mood advantage [5]. A matched screen is therefore essential, and even that contrast remains a complete pathway comparison when acceptance, reliability, alerting, and human oversight also differ.")
    add_text(doc, "Digital mental-health scholarship increasingly emphasizes that efficacy signals alone do not determine adoption, scale-up, or sustained value [14-16]. In a physical system, refusal, incomplete assessments, downtime, fallback, verification, false alerts, sanitation, rework, and physical resets can consume capacity and create nonlinear queue effects. Discrete-event simulation has informed mental-health operations [17], but patient-level engagement and symptom stress tests are rarely evaluated alongside service access and hidden labor. We therefore developed a transparent multiscale framework that moves sequentially from patient trajectories, to clinical thresholds and burden, to service consequences, and finally to break-even and robustness analyses. Table 1 defines the four modeled pathways and the interpretation of their comparisons.")

    doc.add_page_break()
    add_table(doc, 1, "Modeled pathways and the incremental comparison.",
              ["Pathway", "Modeled role", "Interpretation"], [
                  ["Usual care or manual", "Human-delivered baseline", "Contextual comparator; no embodiment-specific exposure"],
                  ["Content-matched screen", "Same modeled digital content without a body", "Primary reference for the bundled robot-pathway contrast"],
                  ["Embodied robot", "Physical interface with realistic faults", "Embodiment plus acceptance, downtime, alert, and physical-burden assumptions"],
                  ["Robot plus human gate", "Physical interface with mandatory verification", "Higher modeled detection and fallback plus additional routine review work"],
              ], font_size=7.6)

    doc.add_heading("Results", level=1)
    doc.add_heading("Computational verification and analytic sequence", level=2)
    add_text(doc, "The audited v4.1 outputs were retained without rerunning the simulations for this narrative revision. In the underlying full rerun, deterministic execution completed, all automated tests passed, shared-cohort and shared-demand checks passed, and queue flow accounting reconciled arrivals with completions and abandonment. Numerical CSV and PNG outputs reproduced exactly; SVG and DOCX artifacts were scientifically equivalent but not byte-identical because generated identifiers and package metadata changed between builds.")
    add_text(doc, "With model integrity established, the results are presented in the order implied by the multiscale question: symptom trajectories first, then threshold outcomes and retention, then patient-level safety and labor, followed by service access and detection, and finally sensitivity, break-even, and component analyses.")

    doc.add_heading("Patient trajectories, threshold outcomes, and retention", level=2)
    add_text(doc, "The first question was whether the pathways separated over time at the symptom scale. Mean last-observation-carried-forward PHQ-9 declined in all pathways, with the screen and robot trajectories separating from usual care and the human-gated pathway showing the lowest modeled week-12 mean (Fig. 1). The intervals in this display quantify uncertainty in expected simulation output under fixed assumptions, not uncertainty in an empirical clinical effect.")
    add_figure(doc, 1, "Synthetic symptom trajectories",
               "Mean last-observation-carried-forward PHQ-9 across 12 weeks for four pathways. Lines use distinct markers and line styles; shaded bands are 95% BCa bootstrap intervals for the mean across 200 independent repeated synthetic trials. The intervals describe model-output uncertainty under fixed assumptions.",
               "figure_1_patient_trajectories.png")

    scr = ind_arm.loc[screen]
    rob = ind_arm.loc[gated]
    add_text(doc, f"The trajectory separation translated into higher modeled response and remission, but not into retention non-worsening. Across 200 repeated trials with 1,200 participants per arm, response was {fmt(scr['response_percent_mean'])}% (95% BCa interval {fmt(scr['response_percent_ci_low'])}-{fmt(scr['response_percent_ci_high'])}) for the screen and {fmt(rob['response_percent_mean'])}% ({fmt(rob['response_percent_ci_low'])}-{fmt(rob['response_percent_ci_high'])}) for the human-gated robot. Completion was {fmt(scr['completion_percent_mean'])}% ({fmt(scr['completion_percent_ci_low'])}-{fmt(scr['completion_percent_ci_high'])}) and {fmt(rob['completion_percent_mean'])}% ({fmt(rob['completion_percent_ci_low'])}-{fmt(rob['completion_percent_ci_high'])}), respectively. Figure 2 shows the complete arm-level distributions and makes the benefit-retention divergence visible.")
    add_figure(doc, 2, "Patient-level outcomes",
               "Replication distributions for response, remission, and 12-week completion. Box plots show medians and interquartile ranges, points show individual replication means, and diamonds with error bars show means and 95% BCa bootstrap intervals. The human-gated pathway improves modeled symptom thresholds while completion remains below the screen comparator.",
               "figure_2_patient_endpoints.png")

    add_text(doc, f"Paired contrasts then isolated the complete robot-pathway differences against the content-matched screen. The human-gated pathway increased response by {interval(r_response)} percentage points, increased remission by {interval(r_remission)} points, and improved mean PHQ-9 change by {interval(r_change)} points, while reducing completion by {interval(r_completion)} points (Fig. 3). The two-sided sign-flip Monte Carlo P value was 0.000010 for each contrast and the Holm-adjusted value was 0.000070; these values demonstrate model-internal separation, not clinical significance.")
    add_figure(doc, 3, "Primary patient-level threshold contrasts",
               "Mean paired differences between the human-gated robot and the screen across 200 repeated trials. Error bars are 95% BCa bootstrap intervals obtained by resampling intact paired replication identifiers. Positive values favor the robot for response and remission; negative values favor the screen for completion.",
               "figure_3_patient_contrasts.png")

    doc.add_heading("Patient-level safety burden and hidden labor", level=2)
    add_text(doc, f"The next transition was from symptom benefit to safety and workload. The human-gated pathway reduced expected missed high-risk weeks by {fmt(abs(r_missed['mean_difference']))} per 100 high-risk weeks, but added {interval(r_review)} review minutes per participant and {interval(r_near)} physical near-misses per 100 participants. Figure 4 places these favorable and unfavorable outcomes on a common patient-level burden map. The 2.5th-97.5th percentile range of single-replication missed-high-risk contrasts crossed zero ({fmt(r_missed['replication_p025_difference'],1)} to {fmt(r_missed['replication_p975_difference'],1)}), despite a mean interval excluding zero.")
    add_figure(doc, 4, "Patient-level safety and hidden labor",
               "Replication distributions for false alerts, missed high-risk weeks, clinician review time, and physical near-misses. Box plots and points display the full replication distribution; diamonds and error bars show means and 95% BCa intervals. Nonembodied pathways are structurally unable to generate physical near-misses.",
               "figure_4_patient_safety_labor.png")

    doc.add_heading("Service access, throughput, and detection trade-offs", level=2)
    sc = sys_arm.loc[sys_screen]
    sg = sys_arm.loc[sys_gated]
    add_text(doc, f"Because patient-level gains can be offset by service congestion, the analysis next moved to the discrete-event model. Mean wait was {fmt(sc['mean_wait_minutes_mean'])} working minutes (95% BCa interval {fmt(sc['mean_wait_minutes_ci_low'])}-{fmt(sc['mean_wait_minutes_ci_high'])}) for the screen and {fmt(sg['mean_wait_minutes_mean'])} minutes ({fmt(sg['mean_wait_minutes_ci_low'])}-{fmt(sg['mean_wait_minutes_ci_high'])}) for the human-gated robot. The paired difference was {interval(s_wait)} minutes. Figure 5 shows that the penalty was not an artifact of a small number of extreme replications; the distribution shifted broadly upward.")
    add_figure(doc, 5, "Service waiting-time distributions",
               "Mean working-time waits over 200 paired discrete-event replications after a five-day warm-up. Box plots and points show replication distributions; diamonds and error bars show means and 95% BCa intervals.",
               "figure_5_service_wait.png")

    add_text(doc, f"The access penalty accompanied a detection-workload trade-off. The human-gated pathway reduced missed high-acuity cases by {fmt(abs(s_missed['mean_difference']))} percentage points, while increasing false alerts by {fmt(s_false['mean_difference'])} per 100 arrivals, abandonment by {fmt(s_abandon['mean_difference'])} points, and clinician utilization by {fmt(s_util['mean_difference'])} points (Fig. 6). Each two-sided sign-flip Monte Carlo P value was 0.000010 and each Holm-adjusted value was 0.000070.")
    add_figure(doc, 6, "Service safety and access outcomes",
               "Replication distributions for false alerts, missed high-acuity cases, and abandonment. Box plots and points show paired-replication outputs; diamonds and error bars show means and 95% BCa intervals. Improved modeled detection is accompanied by additional false alerts and operational burden.",
               "figure_6_service_safety_access.png")

    add_text(doc, f"Average throughput appeared similar across the screen and robot pathways, with a human-gated contrast of {interval(s_throughput,3)} assessments per working day. Figure 7 shows why throughput alone is an incomplete operational endpoint: nearly unchanged completions coexisted with much longer waits and higher abandonment.")
    add_figure(doc, 7, "Service throughput distributions",
               "Completed assessments per working day. Box plots and points show 200 replication outputs; diamonds and error bars show means and 95% BCa intervals. Similar throughput conceals large differences in waiting, abandonment, detection, and workload.",
               "figure_s3_service_throughput.png")

    add_text(doc, "The paired service contrasts are assembled in Figure 8, which provides the bridge from individual operational endpoints to the cross-scale synthesis. The large positive wait contrast and small negative throughput contrast demonstrate that capacity stress can be expressed more strongly in delay than in completed volume.")
    add_figure(doc, 8, "Paired service-level contrasts",
               "Mean paired differences versus the screen under common arrival, acuity, and latent random streams. Error bars are 95% BCa bootstrap intervals. Native metric units are retained because waiting time and throughput are operationally distinct quantities.",
               "figure_s4_service_contrasts.png")

    add_text(doc, "Table 2 consolidates the primary human-gated pathway contrasts after the patient and service results have been presented separately. The table makes the dual-gate conclusion explicit: modeled response, remission, and detection favored the robot pathway, whereas completion, review time, waiting, false alerts, and physical exposure did not.")
    primary_rows = []
    for scale, row, outcome, unit, interpretation in [
        ("Patient", r_response, "Response", "percentage points", "Favors robot pathway"),
        ("Patient", r_remission, "Remission", "percentage points", "Favors robot pathway"),
        ("Patient", r_completion, "Completion", "percentage points", "Favors screen"),
        ("Patient", r_change, "Mean PHQ-9 change", "score points", "Negative favors robot pathway"),
        ("Patient", r_review, "Review time", "minutes per participant", "Higher hidden labor"),
        ("Patient", r_near, "Physical near-misses", "per 100 participants", "Robot-only exposure"),
        ("Service", s_wait, "Mean wait", "working minutes", "Favors screen"),
        ("Service", s_false, "False alerts", "per 100 arrivals", "Higher alert burden"),
        ("Service", s_missed, "Missed high-acuity cases", "percentage points", "Negative favors robot pathway"),
    ]:
        primary_rows.append([scale, outcome, interval(row), unit, "0.000070", interpretation])
    add_table(doc, 2, "Primary human-gated pathway contrasts versus the content-matched screen.",
              ["Scale", "Outcome", "Mean difference (95% BCa interval)", "Unit", "Holm-adjusted sign-flip P", "Interpretation"],
              primary_rows, font_size=6.8)

    doc.add_heading("Sensitivity, break-even, and reviewer-motivated analyses", level=2)
    add_text(doc, "After establishing the base-case divergence, the analysis proceeded through four robustness questions: whether patient benefit survived engagement and downtime variation; whether conclusions persisted across multivariable scenarios; whether service non-worsening could be recovered through engineering changes; and whether the findings depended on attrition estimands or bundled parameter assumptions. Table 3 summarizes the sequence before the detailed displays.")
    cap_wait = cap[cap["metric"] == "mean_wait_difference_minutes"].set_index("robot_intake_servers")
    add_table(doc, 3, "Roadmap of robustness questions and findings.",
              ["Question", "Analysis", "Finding", "Interpretation"], [
                  ["Patient benefit under operating variation", "Engagement-by-downtime grid", "Response benefit varied, but no tested cell produced a completion gain", "Clinical threshold benefit did not imply retention non-worsening"],
                  ["Multivariable parameter uncertainty", "250 draws with five inner replications", f"Response positive in {fmt(nested.loc['response_positive','percent_of_scenario_draws'],1)}%; completion negative in 100%", "Proportions apply only to selected stress-test ranges"],
                  ["Operational break-even", "Downtime-by-review grid and warm-up diagnostic", "Wait non-worsening was confined to low review time and zero downtime; ordering survived warm-up choices", "Engineering reliability and oversight duration are joint constraints"],
                  ["Reviewer-motivated alternatives", "Attrition estimands, 2-5 intake stations, and one-block substitution", f"Response direction persisted; wait penalty remained about {fmt(cap_wait.loc[3,'robot_minus_screen_mean'],1)}-{fmt(cap_wait.loc[5,'robot_minus_screen_mean'],1)} min; components drove different outcomes", "Magnitude and attribution require explicit estimands and component designs"],
              ], font_size=7.0)

    add_text(doc, "Because the complete robot-screen contrast changes several implementation blocks at once, Table 4 lists the underlying parameter differences before the sensitivity and decomposition results are interpreted. This table is descriptive: it defines the modeled pathways and does not imply that the parameter values are empirically calibrated.")
    screen_cfg = ARM_CONFIGS["screen_agent"]
    robot_cfg = ARM_CONFIGS["robot_hitl"]
    block_rows = []
    blocks = {
        "Engagement": ["engagement_intercept", "weekly_decay"],
        "Embodiment symptom effect": ["embodiment_effect"],
        "Acceptance friction": ["initial_refusal", "privacy_penalty", "discomfort_dropout"],
        "Reliability and fallback": ["downtime", "fallback_screen_probability"],
        "Detection and oversight": ["crisis_sensitivity", "false_alert_probability", "review_minutes_per_alert", "routine_audit_minutes", "human_verification"],
        "Physical exposure": ["physical_near_miss_per_active_week"],
    }
    for block, fields in blocks.items():
        for field in fields:
            block_rows.append([block, field, str(getattr(screen_cfg, field)), str(getattr(robot_cfg, field))])
    add_table(doc, 4, "Parameter blocks differentiating the screen and human-gated patient pathways.",
              ["Block", "Parameter", "Screen", "Robot plus human gate"], block_rows, font_size=7.1)

    add_text(doc, "The first detailed stress test varied engagement advantage and session-level downtime. Figure 9 shows that response benefit was most favorable when engagement advantage was high and downtime low. The surface also shows why a single base-case contrast is insufficient: the same conceptual pathway can occupy materially different regions of performance as reliability and engagement change.")
    add_figure(doc, 9, "Patient-level response sensitivity",
               "Mean response difference between the human-gated robot and screen as engagement-logit advantage and downtime vary. Open circles mark cells whose 95% bootstrap interval excludes zero in the favorable direction.",
               "figure_s1_response_sensitivity.png")

    add_text(doc, f"The second stress test varied multiple parameters jointly. Across 250 broad scenarios averaged over five first-order replications per draw, response favored the human-gated pathway in {fmt(nested.loc['response_positive','percent_of_scenario_draws'],1)}% (scenario-resampling interval {fmt(nested.loc['response_positive','scenario_resampling_ci_low'],1)}-{fmt(nested.loc['response_positive','scenario_resampling_ci_high'],1)}), whereas completion was lower and review burden higher in 100% of scenarios. Favorable mean PHQ-9 change occurred in {fmt(nested.loc['phq_change_favorable','percent_of_scenario_draws'],1)}%. Figure 10 displays the response-completion trade-off, and Table 5 reports the full scenario-stability summary. These proportions are diagnostics over selected ranges, not posterior probabilities.")
    add_figure(doc, 10, "Nested parameter-scenario uncertainty",
               "Joint response and completion contrasts across 250 broad illustrative parameter draws, each averaged over five first-order replications. The scenario ranges are stress tests and not posterior distributions.",
               "figure_s2_nested_parameter_uncertainty.png")
    nested_rows = []
    for diagnostic, label in [
        ("response_positive", "Response favors robot"),
        ("completion_negative", "Completion favors screen"),
        ("phq_change_favorable", "Mean PHQ-9 change favors robot"),
        ("review_positive", "Review burden higher for robot"),
        ("near_miss_positive", "Physical exposure higher for robot"),
    ]:
        rr = nested.loc[diagnostic]
        nested_rows.append([label, fmt(rr["percent_of_scenario_draws"],1), f"{fmt(rr['scenario_resampling_ci_low'],1)}-{fmt(rr['scenario_resampling_ci_high'],1)}", str(int(rr["scenario_draws"])), str(int(rr["inner_replications_per_draw"]))])
    add_table(doc, 5, "Nested scenario-ensemble stability.",
              ["Diagnostic", "Scenario draws (%)", "Resampling interval (%)", "Draws", "Inner replications"], nested_rows, font_size=7.2)

    add_text(doc, "The third stress test asked where service waiting could reach a strict zero-margin non-worsening condition. Figure 11 shows that favorable or nonpositive wait differences were confined to zero modeled day-level downtime and short review durations. Requiring the upper 95% bootstrap bound to be nonpositive further narrowed the feasible region, illustrating that reliability and human review cannot be optimized independently.")
    add_figure(doc, 11, "Service break-even sensitivity",
               "Difference in mean wait between the human-gated robot and screen as downtime and review time vary. Negative values favor the robot; open circles mark cells whose upper 95% bootstrap bound is nonpositive.",
               "figure_s5_service_break_even.png")

    add_text(doc, "A queue warm-up diagnostic then tested whether the base ordering was a transient initialization artifact. Across zero, two, five, and ten warm-up days, the screen remained faster than the human-gated pathway (Fig. 12). Warm-up changed the absolute estimates modestly but did not reverse the comparison.")
    add_figure(doc, 12, "Queue warm-up diagnostic",
               "Mean waiting time with zero, two, five, and ten warm-up days. Error bars are 95% BCa intervals. Warm-up choice does not reverse pathway ordering.",
               "figure_s6_warmup_diagnostic.png")

    add_text(doc, f"The fourth group of analyses addressed reviewer-motivated alternatives. Differential attrition was examined first because the pathway with better modeled symptom thresholds also completed less often. The response contrast was {fmt(est.loc['response_locf_percent','robot_minus_screen_mean'])} points under last observation carried forward, {fmt(est.loc['response_bocf_percent','robot_minus_screen_mean'])} under baseline observation carried forward, and {fmt(est.loc['response_completers_percent','robot_minus_screen_mean'])} among completers. Figure 13 shows the estimand dependence across response and remission, and Table 6 provides the numerical intervals.")
    add_figure(doc, 13, "Endpoint estimand sensitivity",
               "Robot-screen response and remission contrasts under last observation carried forward, baseline observation carried forward, and completer-only estimands. Error bars are 95% BCa intervals across 200 repeated trials.",
               "figure_s7_estimand_sensitivity.png")
    est_labels = {
        "response_locf_percent": "Response under LOCF, percentage points",
        "response_bocf_percent": "Response under BOCF, percentage points",
        "response_completers_percent": "Response among completers, percentage points",
        "remission_locf_percent": "Remission under LOCF, percentage points",
        "remission_bocf_percent": "Remission under BOCF, percentage points",
        "remission_completers_percent": "Remission among completers, percentage points",
        "mean_change_locf": "Mean PHQ-9 change under LOCF",
        "mean_change_bocf": "Mean PHQ-9 change under BOCF",
        "mean_change_completers": "Mean PHQ-9 change among completers",
    }
    est_rows = []
    for metric, label in est_labels.items():
        rr = est.loc[metric]
        est_rows.append([label, fmt(rr["robot_minus_screen_mean"]), f"{fmt(rr['bootstrap_ci_low'])} to {fmt(rr['bootstrap_ci_high'])}", str(int(rr["replications"]))])
    add_table(doc, 6, "Endpoint estimand sensitivity for the human-gated robot minus screen contrast.",
              ["Estimand", "Mean difference", "95% BCa interval", "Replications"], est_rows, font_size=7.0)

    add_text(doc, f"Service capacity was then varied to test whether the waiting penalty was caused only by fewer embodied intake stations. Increasing the human-gated pathway from two to five stations did not remove the penalty: the mean difference was {fmt(cap_wait.loc[3,'robot_minus_screen_mean'])} minutes with three stations, {fmt(cap_wait.loc[4,'robot_minus_screen_mean'])} with four, and {fmt(cap_wait.loc[5,'robot_minus_screen_mean'])} with five. Figure 14 shows the near-plateau, and Table 7 reports the wait and throughput contrasts. Within this configuration, clinician-stage duration and review burden dominated the intake-station count.")
    add_figure(doc, 14, "Service capacity sensitivity",
               "Mean wait difference between the human-gated robot and screen as the number of embodied intake stations varies. Error bars are 95% BCa intervals across 200 paired replications.",
               "figure_s8_capacity_sensitivity.png")
    wait = cap[cap["metric"] == "mean_wait_difference_minutes"].sort_values("robot_intake_servers")
    throughput = cap[cap["metric"] == "throughput_difference_per_day"].set_index("robot_intake_servers")
    cap_rows = []
    for _, rr in wait.iterrows():
        servers = int(rr["robot_intake_servers"])
        tt = throughput.loc[servers]
        cap_rows.append([str(servers), fmt(rr["robot_minus_screen_mean"]), f"{fmt(rr['bootstrap_ci_low'])} to {fmt(rr['bootstrap_ci_high'])}", fmt(tt["robot_minus_screen_mean"],3), f"{fmt(tt['bootstrap_ci_low'],3)} to {fmt(tt['bootstrap_ci_high'],3)}"])
    add_table(doc, 7, "Service capacity sensitivity.",
              ["Embodied intake stations", "Mean wait difference, min", "95% BCa interval", "Throughput difference/day", "95% BCa interval"], cap_rows, font_size=6.9)

    def ablval(block: str, metric: str) -> float:
        return float(abl[(abl["parameter_block"] == block) & (abl["metric"] == metric)]["mean_difference_vs_screen"].iloc[0])

    add_text(doc, f"Finally, the pathway bundle was decomposed one block at a time. Substituting only the modeled embodiment symptom increment increased response by {fmt(ablval('Embodiment symptom increment only','response_difference_percentage_points'))} points with essentially no completion change, whereas substituting only acceptance-friction assumptions reduced response by {fmt(abs(ablval('Acceptance friction only','response_difference_percentage_points')))} points and completion by {fmt(abs(ablval('Acceptance friction only','completion_difference_percentage_points')))} points. Safety oversight and physical exposure generated most of the additional review and near-miss burden. Figure 15 shows the directional pattern and Table 8 gives the numerical decomposition. This diagnostic is not additive, causal mediation, or attribution of a biological embodiment effect.")
    add_figure(doc, 15, "Pathway bundle decomposition",
               "One-block-at-a-time substitution of human-gated robot parameter blocks into the screen pathway. The analysis is diagnostic and not an additive or causal attribution.",
               "figure_s9_pathway_bundle_ablation.png")
    response = abl[abl["metric"] == "response_difference_percentage_points"].set_index("parameter_block")
    completion = abl[abl["metric"] == "completion_difference_percentage_points"].set_index("parameter_block")
    review = abl[abl["metric"] == "review_minutes_difference"].set_index("parameter_block")
    ab_rows = []
    for block in response.index:
        ab_rows.append([block, fmt(response.loc[block,"mean_difference_vs_screen"]), fmt(completion.loc[block,"mean_difference_vs_screen"]), fmt(review.loc[block,"mean_difference_vs_screen"])])
    add_table(doc, 8, "One-block-at-a-time pathway decomposition.",
              ["Parameter block substituted into screen", "Response difference, points", "Completion difference, points", "Review difference, min"], ab_rows, font_size=7.0)

    doc.add_heading("Discussion", level=1)
    add_text(doc, "This simulation demonstrates a multiscale separation: a modeled patient or detection advantage can coexist with worse retention, human workload, false alerts, physical exposure, and service access. The principal implication is not that a specific robot is effective or unsafe. It is that empirical evaluation should require both incremental patient benefit against a content-matched screen and prespecified operational acceptability, including completion, waiting, verification labor, fallback, and physical-safety workload.")
    add_text(doc, "The result is consistent with, but more operationally qualified than, the human-robot interaction literature. Physical copresence can strengthen behavioral and attitudinal responses relative to screen display [8,9], and the recent matched iCBT study found improved alliance, adherence, and satisfaction without a significant mood advantage [5]. Our framework formalizes the next question: whether such an interaction dividend remains valuable after refusal, downtime, oversight, and service consequences are counted. In the base assumptions, the answer differed by outcome and scale.")
    add_text(doc, "The broader health evidence also supports cautious interpretation. Reviews across mental health, older adults, and dementia report promising feasibility and selected psychosocial effects, but heterogeneous interventions, small samples, mixed pooled estimates, and limited long-term evidence remain common [2,3,10-12]. A month-long home study in autism illustrates the feasibility of sustained autonomous interaction in a selected setting [13], but it does not resolve comparative efficacy, workflow, or generalizability in psychiatric services. Simulation can therefore organize hypotheses and identify measurements; it cannot substitute for clinical evaluation.")
    add_text(doc, "Implementation science provides the appropriate bridge from efficacy to deployment. Digital psychiatry reviews emphasize that the intervention, users, clinical context, and implementation process jointly determine real-world value [14,15], while the NASSS framework highlights nonadoption, abandonment, scale-up, spread, and sustainability as distinct failure modes [16]. The present dual-gate standard operationalizes part of that agenda by treating completion, clinician review, waiting, fallback, and physical work as co-primary deployment concerns rather than post hoc inconveniences.")
    add_text(doc, "The component analysis further limits causal language. The human-gated robot and screen were content-matched but not intervention-identical: their contrast combined embodiment, engagement dynamics, acceptance friction, downtime, fallback, detection sensitivity, review rules, and physical exposure. Favorable response and unfavorable completion arose from different assumption blocks. Empirical studies seeking component effects should use factorial, sequential, or adaptive designs and report human-AI interaction, workflow integration, error handling, and protocol deviations in line with DECIDE-AI and CONSORT-AI principles [22,23].")
    add_text(doc, "Differential attrition is central because the pathway with better modeled symptom thresholds also completed less often. Baseline-observation-carried-forward and completer-only analyses preserved the response direction but changed its magnitude. An empirical trial should prospectively define treatment-policy, while-on-treatment, and hypothetical estimands; collect outcomes after disengagement where feasible; and use missing-data methods appropriate to the causal question rather than rely on last observation carried forward.")
    add_text(doc, "The service model suggests that the waiting penalty is not explained solely by fewer robot stations, because increasing intake capacity produced little improvement while clinician review remained fixed. Nevertheless, this is one finite-capacity clinic configuration. The manual pathway is nominally at its intake-capacity boundary, the abandonment function is stylized, and scheduling, no-shows, downstream treatment capacity, staff learning, maintenance logistics, costs, and equity effects are not represented. Site-specific calibration and face validation are required before operational use.")
    add_text(doc, "All parameters are illustrative. The framework cannot estimate clinical efficacy, real-world safety incidence, cost-effectiveness, regulatory acceptability, or generalizability. Threshold outcomes amplify small distributional shifts; high-risk episodes and physical near-misses are synthetic constructs; the individual and service models are not dynamically coupled; and the broad parameter draws are not a probability distribution over plausible deployments. Narrow bootstrap intervals and small Monte Carlo P values reflect repeated computation under fixed assumptions, not empirical certainty.")
    add_text(doc, "The contribution is therefore methodological and hypothesis-generating: a single reproducible sequence connects patient trajectories, threshold outcomes, retention, hidden labor, queue performance, break-even conditions, and component stress tests. The next scientific step is empirical parameter elicitation, patient and clinician co-design, stakeholder face validation, external validation against observed service data, and prospective comparison with a genuinely content-matched screen.")

    doc.add_heading("Methods", level=1)
    doc.add_heading("Study design and interpretation", level=2)
    add_text(doc, "We constructed an individual microsimulation and a service-level discrete-event simulation. The models share pathway definitions and burden categories but are not dynamically coupled. No patient records, human-subject data, or empirical clinical outcome data were used. Parameters are transparent illustrative assumptions selected to expose trade-offs and generate falsifiable targets. Table 1 summarizes the pathways, and Table 4 identifies the parameter blocks that distinguish the content-matched screen from the human-gated patient pathway.")
    add_text(doc, "The primary reference was a screen pathway delivering the same modeled digital content. The primary estimand was the expected paired difference between each complete robot pathway and the screen under the fixed data-generating process. Because the pathways differ in multiple implementation parameters, this estimand is a bundled pathway contrast and not a causal effect of physical embodiment alone.")

    doc.add_heading("Individual microsimulation", level=2)
    add_text(doc, "The individual model followed synthetic participants for 12 weeks across usual measurement-based care, a screen-based agent, an embodied social robot, and an embodied robot with mandatory human review for risk-relevant alerts. A 5,000-participant-per-arm base cohort supported patient-level audit output. The uncertainty experiment used 200 independent repeated trials with 1,200 participants per arm. Within each replication, all pathways reused the same baseline-cohort seed while pathway event streams were independent.")
    add_text(doc, "Baseline PHQ-9, technology acceptance, privacy concern, social support, and treatment responsiveness were drawn from bounded or parametric distributions. Weekly engagement, refusal, dropout, symptom change, downtime, fallback, alerts, high-risk episodes, review minutes, and physical near-misses followed prespecified transition rules. Response was at least a 50% PHQ-9 reduction and remission was PHQ-9 of 4 or less [20,21]; completion required remaining active through week 12. The primary symptom analysis carried the last observation forward after dropout.")

    doc.add_heading("Service discrete-event simulation", level=2)
    add_text(doc, "The service model compared manual intake, a screen kiosk with clinician review, an embodied robot with realistic faults, and an embodied robot with a human safety gate. Each replication simulated a five-working-day warm-up followed by 35 observed working days; 200 paired replications were used. All pathways within a replication received identical arrival times, acuity labels, outage uniforms, and latent service and event variates.")
    add_text(doc, "Outcomes included mean and 90th-percentile waiting time, throughput, abandonment, false alerts, missed high-acuity cases, failover, rework, clinician utilization, overtime, and routine physical reset workload. Arrival accounting required arrivals to equal completions plus abandonment. The manual pathway has nominal intake capacity of approximately 35 arrivals per day and was retained as a deliberately capacity-constrained contextual benchmark rather than the primary comparator.")

    doc.add_heading("Statistical analysis and reproducibility", level=2)
    add_text(doc, "The independent simulation replication was the uncertainty unit. Paired nonparametric resampling selected intact replication identifiers. Primary mean contrasts used two-sided 95% bias-corrected and accelerated bootstrap intervals with 10,000 resamples. Arm-level endpoints used 5,000 resamples, and weekly trajectories and grid cells used 3,000. All seeds were deterministically derived from analysis labels [24-26].")
    add_text(doc, "Each primary paired contrast was evaluated using a two-sided paired sign-flip randomization test with 100,000 Monte Carlo draws and a plus-one correction. The nominal alpha level was 0.05. Paired t tests were concordance analyses. Holm adjustment controlled family-wise error across seven declared outcomes within each comparator and model. Cohen dz summarized standardized paired separation, and the standard deviation of replication contrasts divided by the square root of 200 provided the Monte Carlo standard error of the mean.")
    add_text(doc, "Confidence intervals quantify precision of expected outputs under fixed model assumptions. Empirical 2.5th-97.5th percentile ranges describe variation across individual synthetic replications. Neither quantity incorporates empirical parameter uncertainty, structural uncertainty, clinical sampling uncertainty, or external validity.")

    doc.add_heading("Sensitivity and reviewer-motivated analyses", level=2)
    add_text(doc, "The original individual grid varied the robot engagement-logit advantage from 0.00 to 0.35 and session-level downtime from 0% to 30%. The service grid varied day-level downtime from 0% to 30% and clinician review from 4 to 24 minutes. A revised 250-draw scenario ensemble varied engagement, downtime, embodiment effect, refusal, dropout, false-alert probability, risk sensitivity, review time, and fallback, with five first-order replications averaged within each parameter draw.")
    add_text(doc, "Post-review analyses compared last-observation-carried-forward, baseline-observation-carried-forward, and completer-only symptom estimands; varied the human-gated pathway from two to five intake stations; and replaced one parameter block at a time in the screen configuration with the corresponding robot-pathway values. The one-block analysis is a diagnostic decomposition, not an additive attribution or causal mediation analysis.")

    doc.add_heading("Software, verification, and reporting", level=2)
    add_text(doc, "The simulations were implemented in Python 3.13 using NumPy, pandas, SciPy, Matplotlib, and python-docx. The repository records fixed seeds, dependency constraints, model parameters, intermediate data, figures, tests, and SHA-256 manifests. Automated checks cover deterministic reruns, shared cohorts and demand streams, ranges, impossible events, queue flow, interval fields, editable SVG text, figure fonts, and manuscript-result reconciliation. The framework follows STRESS and model-transparency principles [18,19]. The command python run_all.py regenerates the primary simulations, reviewer analyses, journal figures, manuscript files, validation checks, and checksums.")

    doc.add_heading("Ethics and use of artificial intelligence", level=2)
    add_text(doc, "Ethics approval and participant consent were not applicable because the study used only synthetic data and computer simulations.")
    add_text(doc, "[Authors to verify and edit before submission] During repository and manuscript revision, OpenAI ChatGPT was used for editorial restructuring, code review, literature-search support, and generation of draft text. All analyses were executed from the repository, numerical outputs were checked against generated files, and the authors take responsibility for the final manuscript.")

    doc.add_heading("Data Availability", level=1)
    add_text(doc, "All synthetic datasets and machine-readable outputs generated for this study are included in the accompanying repository. Before submission, replace this sentence with the name, persistent URL, version, and DOI of the deposited release.")
    doc.add_heading("Code Availability", level=1)
    add_text(doc, "All custom Python code required to reproduce the simulations, analyses, tables, and figures is included in the accompanying repository. Running python run_all.py regenerates the complete workflow. Before submission, deposit the tagged release in a DOI-minting repository, select an open-source license, and insert the persistent citation here.")
    doc.add_heading("Acknowledgements", level=1)
    add_text(doc, "[Insert acknowledgements.] [Insert funding statement here; state either the funder and grant information or that the study received no funding.]")
    doc.add_heading("Author contributions", level=1)
    add_text(doc, "[Insert a CRediT statement naming every author by initials and describing individual contributions.]")
    doc.add_heading("Competing interests", level=1)
    add_text(doc, "[Insert a declaration for every author. If none: All authors declare no financial or non-financial competing interests.]")

    doc.add_heading("References", level=1)
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(-0.22)
        p.paragraph_format.left_indent = Inches(0.22)
        p.paragraph_format.space_after = Pt(2)
        p.add_run(f"{i}. {ref}")

    path = MAN / f"Physical_AI_Psychiatry_Integrated_Manuscript_v{VERSION}.docx"
    doc.save(path)
    return path


def build_cover_letter() -> Path:
    doc = Document()
    setup_doc(doc)
    add_text(doc, "[Date]")
    add_text(doc, "Editor in Chief\nnpj Digital Medicine")
    add_text(doc, f"Re: Submission of an Article entitled {TITLE}")
    add_text(doc, "Dear Editor,")
    add_text(doc, "We submit the enclosed simulation study for consideration as an Article in npj Digital Medicine. The work develops an open, assumption-driven framework that evaluates physical artificial intelligence across two linked decision scales: patient-level benefit, retention, safety, and hidden labor; and service-level waiting, abandonment, detection, and capacity.")
    add_text(doc, "The central contribution is a dual evaluation standard. A physically embodied pathway should not be judged solely by modeled symptom or detection gains; it should also meet prespecified operational and retention criteria against a content-matched screen. In the base scenario, the human-gated robot improved selected model outputs but worsened completion, clinician review burden, waiting, false alerts, and physical exposure. Sensitivity analyses test attrition estimands, nested parameter uncertainty, intake capacity, break-even conditions, and the bundled nature of the comparator.")
    add_text(doc, "For narrative transparency, all tables and figures, including the former supplementary displays, are integrated at the point of first substantive discussion in the manuscript. The manuscript does not claim clinical efficacy or safety, and no patient data were used. All simulations, intermediate outputs, editable vector figures, tests, and build scripts will be released in a DOI-minting repository before publication.")
    add_text(doc, "[Authors must add: confirmation of originality and no concurrent consideration; related manuscripts or preprints; author agreement; corresponding-author affiliation, address, telephone, and email; suggested or opposed reviewers if desired; repository or preprint links; and any special collection information.]")
    add_text(doc, "Sincerely,\n[Corresponding author name, degrees]\n[Affiliation]\n[Email and telephone]")
    path = MAN / f"Cover_Letter_Draft_v{VERSION}.docx"
    doc.save(path)
    return path


def main() -> None:
    for path in [build_manuscript(), build_cover_letter()]:
        print(path)


if __name__ == "__main__":
    main()
