"""Create the v4.1 review report, journal-structured manuscript, supplement, and cover letter."""
from __future__ import annotations

from pathlib import Path
from datetime import date
import json
import math
import re
import shutil

import pandas as pd
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from build_final_manuscript import REFERENCES
from individual_microsimulation import ARM_CONFIGS
from service_queue_simulation import CONFIGS

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "outputs"
REVIEW_OUT = OUT / "reviewer_reanalysis"
MAN = ROOT / "manuscript"
DELIV = ROOT / "review_deliverables"
FIG = ROOT / "figures" / "journal" / "png"
MAN.mkdir(exist_ok=True)
DELIV.mkdir(exist_ok=True)

TITLE = "Multiscale simulation stress tests of physical artificial intelligence in psychiatric care"
SHORT_TITLE = "Physical artificial intelligence in psychiatric care"
ACCESS_DATE = "29 July 2026"


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", text))


def fmt(x: float, d: int = 2) -> str:
    return f"{float(x):.{d}f}"


def signed(x: float, d: int = 2) -> str:
    return f"{float(x):+.{d}f}"


def interval(row: pd.Series, d: int = 2, low="bootstrap_ci_low", high="bootstrap_ci_high") -> str:
    return f"{signed(row['mean_difference'], d)} ({fmt(row[low], d)} to {fmt(row[high], d)})"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.append(fld_char1)
    run._r.append(instr)
    run._r.append(fld_char2)


def setup_doc(doc: Document, *, report: bool = False, landscape: bool = False) -> None:
    sec = doc.sections[0]
    if landscape:
        sec.orientation = WD_ORIENT.LANDSCAPE
        sec.page_width, sec.page_height = sec.page_height, sec.page_width
    margin = Inches(0.62 if report else 0.85)
    sec.top_margin = margin
    sec.bottom_margin = margin
    sec.left_margin = margin
    sec.right_margin = margin
    sec.header_distance = Inches(0.25)
    sec.footer_distance = Inches(0.25)
    add_page_number(sec.footer.paragraphs[0])

    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    normal.font.size = Pt(9 if report else 10.5)
    normal.paragraph_format.space_after = Pt(4)
    normal.paragraph_format.line_spacing = 1.08 if report else 1.15

    for style_name, size, color in [
        ("Title", 18 if report else 17, "17324D"),
        ("Heading 1", 14 if report else 13, "17324D"),
        ("Heading 2", 11.5 if report else 11.5, "17324D"),
        ("Heading 3", 10 if report else 10.5, "17324D"),
    ]:
        style = doc.styles[style_name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(8)
        style.paragraph_format.space_after = Pt(4)


def add_title_page(doc: Document, title: str, subtitle: str | None = None, report=False) -> None:
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(title)
    if subtitle:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p2.add_run(subtitle)
        r.bold = True
        r.font.size = Pt(11)
    if report:
        p3 = doc.add_paragraph()
        p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p3.add_run("Independent scientific, statistical, computational, and journal-readiness audit\n").bold = True
        p3.add_run(f"Review completed {ACCESS_DATE}")


def add_text(doc: Document, text: str, *, bold_prefix: str | None = None, italic=False, align=None) -> None:
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    if bold_prefix and text.startswith(bold_prefix):
        p.add_run(bold_prefix).bold = True
        p.add_run(text[len(bold_prefix):])
    else:
        r = p.add_run(text)
        r.italic = italic


def add_bullet(doc: Document, text: str, level: int = 0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    p = doc.add_paragraph(style=style)
    p.add_run(text)


def add_number(doc: Document, text: str) -> None:
    p = doc.add_paragraph(style="List Number")
    p.add_run(text)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths=None, font_size=8.2) -> None:
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
            for r in p.runs:
                r.bold = True
                r.font.size = Pt(font_size)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            cells[i].text = str(value)
            cells[i].vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            for p in cells[i].paragraphs:
                p.paragraph_format.space_after = Pt(0)
                for r in p.runs:
                    r.font.size = Pt(font_size)
        if len(table.rows) % 2 == 1:
            for c in cells:
                set_cell_shading(c, "F7F9FB")
    if widths:
        for row in table.rows:
            for i, width in enumerate(widths):
                row.cells[i].width = Inches(width)
    doc.add_paragraph()


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


def choose(df, comparator, metric):
    hit = df[(df["comparator"] == comparator) & (df["metric"] == metric)]
    if len(hit) != 1:
        raise RuntimeError((comparator, metric, len(hit)))
    return hit.iloc[0]


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
        "Attrition estimand sensitivity preserved the response direction, while one-block analyses showed that the contrast arose from bundled embodiment, engagement, acceptance, reliability, and oversight assumptions. "
        "These synthetic results do not establish clinical efficacy or safety. They support a dual requirement for empirical evaluation: incremental patient benefit and operational acceptability against a matched screen."
    )
    if word_count(abstract) > 150:
        raise ValueError(f"Abstract is {word_count(abstract)} words")
    if word_count(TITLE) > 15 or re.search(r"[:;!?]", TITLE):
        raise ValueError("Title does not meet target content-type format")

    doc = Document()
    setup_doc(doc)
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(TITLE)
    add_text(doc, "[Insert author names, degrees, affiliations, ORCID identifiers, and corresponding-author email]", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, "Article type: Original Research - Simulation Study", align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, f"Short title: {SHORT_TITLE}", align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_paragraph()

    doc.add_heading("Abstract", level=1)
    add_text(doc, abstract)
    add_text(doc, f"Abstract word count: {word_count(abstract)}")
    add_text(doc, "Keywords: physical artificial intelligence; psychiatry; social robotics; microsimulation; discrete-event simulation; implementation science")

    doc.add_heading("Introduction", level=1)
    add_text(doc, "Physical artificial intelligence extends digital psychiatry from software-only interaction to systems that perceive and act through a body. Socially assistive robots have been proposed as coaching, companionship, assessment, and structured-intervention interfaces [1-7]. Physical presence may alter social salience, therapeutic alliance, and adherence, but it also adds refusal, proximity, motion, sanitation, maintenance, environmental constraints, downtime, and the possibility that a device failure becomes a clinical workflow failure.")
    add_text(doc, "The empirical evidence remains early and heterogeneous. Reviews describe small studies with diverse populations, robots, and outcomes [2,3], and a recent matched comparison reported better alliance, adherence, and satisfaction for an embodied interface without a significant mood advantage [5]. A content-matched screen comparator is therefore necessary to separate the incremental pathway implications of embodiment from the effects of digital content, automation, and attention. Even then, a robot-screen contrast is not a pure causal effect of embodiment when pathways also differ in acceptance, reliability, alert behavior, and human oversight.")
    add_text(doc, "Patient-facing outcomes are only one scale of value. Verification, false alerts, incomplete assessments, downtime, fallback, physical resets, and rework consume capacity and can generate nonlinear queue effects. Discrete-event simulation has informed mental-health operations [8], but patient-level engagement and symptom stress tests are rarely evaluated alongside service access and hidden labor. We therefore developed a transparent multiscale simulation framework to identify when an embodied pathway produces model-internal patient or detection gains and whether those gains coexist with acceptable retention and operations. The framework generates falsifiable engineering and clinical targets; it does not estimate real-world efficacy, safety, or causal effects.")

    doc.add_heading("Results", level=1)
    doc.add_heading("Computational verification and primary patient-level results", level=2)
    add_text(doc, "The full repository rerun completed deterministically, all eight automated tests passed, shared-cohort and shared-demand checks passed, and queue flow accounting reconciled arrivals with completions and abandonment. The numerical CSV and PNG outputs reproduced exactly. SVG and DOCX files were scientifically equivalent but not byte-identical because generated identifiers and package metadata changed between builds.")
    scr = ind_arm.loc[screen]
    rob = ind_arm.loc[gated]
    add_text(doc, f"Across 200 repeated synthetic trials with 1,200 participants per arm, response was {fmt(scr['response_percent_mean'])}% (95% BCa interval {fmt(scr['response_percent_ci_low'])}-{fmt(scr['response_percent_ci_high'])}) for the screen and {fmt(rob['response_percent_mean'])}% ({fmt(rob['response_percent_ci_low'])}-{fmt(rob['response_percent_ci_high'])}) for the human-gated robot. Completion was {fmt(scr['completion_percent_mean'])}% ({fmt(scr['completion_percent_ci_low'])}-{fmt(scr['completion_percent_ci_high'])}) and {fmt(rob['completion_percent_mean'])}% ({fmt(rob['completion_percent_ci_low'])}-{fmt(rob['completion_percent_ci_high'])}), respectively (Figs. 1-3).")
    add_text(doc, f"Relative to the screen, the human-gated pathway increased response by {interval(r_response)} percentage points, increased remission by {interval(r_remission)} points, and improved mean PHQ-9 change by {interval(r_change)} points, while reducing completion by {interval(r_completion)} points. The two-sided sign-flip Monte Carlo P value was 0.000010 for each contrast and the Holm-adjusted value was 0.000070. These P values demonstrate separation within the fixed simulation, not clinical significance.")

    doc.add_heading("Safety burden and service access", level=2)
    add_text(doc, f"The human-gated pathway reduced expected missed high-risk weeks by {fmt(abs(r_missed['mean_difference']))} per 100 high-risk weeks (95% BCa interval {fmt(abs(r_missed['bootstrap_ci_high']))}-{fmt(abs(r_missed['bootstrap_ci_low']))} fewer), but added {interval(r_review)} review minutes per participant and {interval(r_near)} physical near-misses per 100 participants (Fig. 4). The 2.5th-97.5th percentile range of single-replication missed-high-risk contrasts crossed zero ({fmt(r_missed['replication_p025_difference'],1)} to {fmt(r_missed['replication_p975_difference'],1)}), despite a mean interval excluding zero.")
    sc = sys_arm.loc[sys_screen]
    sg = sys_arm.loc[sys_gated]
    add_text(doc, f"At service level, mean wait was {fmt(sc['mean_wait_minutes_mean'])} working minutes (95% BCa interval {fmt(sc['mean_wait_minutes_ci_low'])}-{fmt(sc['mean_wait_minutes_ci_high'])}) for the screen and {fmt(sg['mean_wait_minutes_mean'])} minutes ({fmt(sg['mean_wait_minutes_ci_low'])}-{fmt(sg['mean_wait_minutes_ci_high'])}) for the human-gated robot (Fig. 5). The paired difference was {interval(s_wait)} minutes. Throughput differed by {interval(s_throughput,3)} assessments per day, showing that similar average throughput can conceal a large access penalty.")
    add_text(doc, f"The human-gated pathway reduced missed high-acuity cases by {fmt(abs(s_missed['mean_difference']))} percentage points, while increasing false alerts by {fmt(s_false['mean_difference'])} per 100 arrivals, abandonment by {fmt(s_abandon['mean_difference'])} points, and clinician utilization by {fmt(s_util['mean_difference'])} points (Fig. 6). Each two-sided sign-flip Monte Carlo P value was 0.000010 and each Holm-adjusted value was 0.000070.")

    doc.add_heading("Robustness and reviewer-motivated analyses", level=2)
    add_text(doc, f"Across 250 broad parameter scenarios averaged over five first-order replications per draw, response favored the human-gated pathway in {fmt(nested.loc['response_positive','percent_of_scenario_draws'],1)}% (scenario-resampling interval {fmt(nested.loc['response_positive','scenario_resampling_ci_low'],1)}-{fmt(nested.loc['response_positive','scenario_resampling_ci_high'],1)}), whereas completion was lower and review burden higher in 100% of scenarios. Favorable mean PHQ-9 change occurred in {fmt(nested.loc['phq_change_favorable','percent_of_scenario_draws'],1)}% (Fig. S2). These proportions describe the selected stress-test ranges, not posterior probabilities.")
    add_text(doc, f"The differential-attrition sensitivity analysis preserved the direction of the response contrast: {fmt(est.loc['response_locf_percent','robot_minus_screen_mean'])} points under last observation carried forward, {fmt(est.loc['response_bocf_percent','robot_minus_screen_mean'])} points under baseline observation carried forward, and {fmt(est.loc['response_completers_percent','robot_minus_screen_mean'])} points among completers (Fig. S7). The magnitude was therefore estimand-dependent even though the sign was stable.")
    cap_wait = cap[cap["metric"] == "mean_wait_difference_minutes"].set_index("robot_intake_servers")
    add_text(doc, f"Varying embodied intake stations from two to five did not remove the waiting-time penalty: the mean difference was {fmt(cap_wait.loc[3,'robot_minus_screen_mean'])} minutes with three stations, {fmt(cap_wait.loc[4,'robot_minus_screen_mean'])} with four, and {fmt(cap_wait.loc[5,'robot_minus_screen_mean'])} with five (Fig. S8). Within this model, clinician-stage duration and review burden rather than the intake-station count dominated the base waiting contrast.")
    def ablval(block, metric):
        return float(abl[(abl["parameter_block"] == block) & (abl["metric"] == metric)]["mean_difference_vs_screen"].iloc[0])
    add_text(doc, f"One-block-at-a-time pathway decomposition confirmed that the main contrast is bundled rather than a pure embodiment effect. Substituting only the modeled embodiment symptom increment increased response by {fmt(ablval('Embodiment symptom increment only','response_difference_percentage_points'))} points with essentially no completion change, whereas substituting only acceptance-friction assumptions reduced response by {fmt(abs(ablval('Acceptance friction only','response_difference_percentage_points')))} points and completion by {fmt(abs(ablval('Acceptance friction only','completion_difference_percentage_points')))} points. The full bundle increased response by {fmt(ablval('Full human-gated pathway bundle','response_difference_percentage_points'))} points and reduced completion by {fmt(abs(ablval('Full human-gated pathway bundle','completion_difference_percentage_points')))} points (Fig. S9).")

    doc.add_heading("Discussion", level=1)
    add_text(doc, "This simulation demonstrates a multiscale separation: a modeled patient or detection advantage can coexist with worse retention, human workload, false alerts, physical exposure, and service access. The principal implication is not that a specific robot is effective or unsafe. It is that empirical evaluation should require both an incremental patient benefit against a matched screen and prespecified operational acceptability, including completion, waiting, verification labor, fallback, and physical-safety workload.")
    add_text(doc, "The revised analyses materially qualify the interpretation. The human-gated robot and screen are content-matched but not intervention-identical. Their contrast combines embodiment with engagement dynamics, acceptance friction, downtime, fallback, detection sensitivity, review rules, and physical exposure. The one-block analysis showed that the favorable response and unfavorable completion findings arise from different assumption groups and should not be labeled as a causal embodiment effect. Future empirical studies should use factorial or sequential designs when they seek to identify component effects.")
    add_text(doc, "Differential attrition is central because the pathway with better modeled symptom thresholds also completed less often. Baseline-observation-carried-forward and completer-only analyses preserved the response direction but changed its magnitude. An empirical trial should prospectively define treatment-policy, while-on-treatment, and hypothetical estimands; collect outcomes after disengagement where feasible; and use missing-data methods appropriate to the causal question rather than rely on last observation carried forward.")
    add_text(doc, "The service model suggests that the waiting penalty is not explained solely by fewer robot stations, because increasing intake capacity produced little improvement while clinician review remained fixed. Nevertheless, this is one finite-capacity clinic configuration. The manual pathway is nominally at its intake-capacity boundary, the abandonment function is stylized, and no scheduling, no-shows, downstream treatment capacity, staff learning, maintenance logistics, costs, or equity effects are represented. Site-specific calibration and face validation are required before operational use.")
    add_text(doc, "All parameters are illustrative. The framework cannot estimate clinical efficacy, real-world safety incidence, cost-effectiveness, regulatory acceptability, or generalizability. Threshold outcomes amplify small distributional shifts; high-risk episodes and physical near-misses are synthetic constructs; the individual and service models are not dynamically coupled; and the broad parameter draws are not a probability distribution over plausible deployments. The narrow bootstrap intervals and small Monte Carlo P values reflect repeated computation under fixed assumptions, not empirical certainty.")
    add_text(doc, "The framework's contribution is therefore methodological and hypothesis-generating: it integrates patient-level benefit, retention, safety, hidden labor, and service queue consequences in one reproducible stress-test package. Its next scientific step is not further polishing of synthetic precision, but empirical parameter elicitation, stakeholder face validation, external validation against observed service data, and prospective evaluation using a content-matched screen comparator.")

    doc.add_heading("Methods", level=1)
    doc.add_heading("Study design and interpretation", level=2)
    add_text(doc, "We constructed an individual microsimulation and a service-level discrete-event simulation. The models share pathway definitions and burden categories but are not dynamically coupled. No patient records, human-subject data, or empirical clinical outcome data were used. Parameters are transparent illustrative assumptions selected to expose trade-offs and generate falsifiable targets.")
    add_text(doc, "The primary reference was a screen pathway delivering the same modeled digital content. The primary estimand was the expected paired difference between each complete robot pathway and the screen under the fixed data-generating process. Because the pathways differ in multiple implementation parameters, this estimand is a bundled pathway contrast and not a causal effect of physical embodiment alone.")

    doc.add_heading("Individual microsimulation", level=2)
    add_text(doc, "The individual model followed synthetic participants for 12 weeks across usual measurement-based care, a screen-based agent, an embodied social robot, and an embodied robot with mandatory human review for risk-relevant alerts. A 5,000-participant-per-arm base cohort supported patient-level audit output. The uncertainty experiment used 200 independent repeated trials with 1,200 participants per arm. Within each replication, all pathways reused the same baseline-cohort seed while pathway event streams were independent.")
    add_text(doc, "Baseline PHQ-9, technology acceptance, privacy concern, social support, and treatment responsiveness were drawn from bounded or parametric distributions. Weekly engagement, refusal, dropout, symptom change, downtime, fallback, alerts, high-risk episodes, review minutes, and physical near-misses followed prespecified transition rules. Response was at least a 50% PHQ-9 reduction; remission was PHQ-9 of 4 or less; completion required remaining active through week 12. The primary symptom analysis carried the last observation forward after dropout.")

    doc.add_heading("Service discrete-event simulation", level=2)
    add_text(doc, "The service model compared manual intake, a screen kiosk with clinician review, an embodied robot with realistic faults, and an embodied robot with a human safety gate. Each replication simulated a five-working-day warm-up followed by 35 observed working days; 200 paired replications were used. All pathways within a replication received identical arrival times, acuity labels, outage uniforms, and latent service and event variates.")
    add_text(doc, "Outcomes included mean and 90th-percentile waiting time, throughput, abandonment, false alerts, missed high-acuity cases, failover, rework, clinician utilization, overtime, and routine physical reset workload. Arrival accounting required arrivals to equal completions plus abandonment. The manual pathway has nominal intake capacity of approximately 35 arrivals per day and was retained as a deliberately capacity-constrained contextual benchmark rather than the primary comparator.")

    doc.add_heading("Statistical analysis and reproducibility", level=2)
    add_text(doc, "The independent simulation replication was the uncertainty unit. Paired nonparametric resampling selected intact replication identifiers. Primary mean contrasts used two-sided 95% bias-corrected and accelerated bootstrap intervals with 10,000 resamples. Arm-level endpoints used 5,000 resamples and weekly trajectories and grid cells used 3,000. All seeds were deterministically derived from analysis labels.")
    add_text(doc, "Each primary paired contrast was evaluated using a two-sided paired sign-flip randomization test with 100,000 Monte Carlo draws and a plus-one correction. The nominal alpha level was 0.05. Paired t tests were concordance analyses; their assumptions were not used to justify the primary sign-flip test. Holm adjustment controlled family-wise error across seven declared outcomes within each comparator and model. Cohen dz summarized standardized paired separation, and the standard deviation of replication contrasts divided by the square root of 200 provided the Monte Carlo standard error of the mean. Actual Monte Carlo P values and adjusted values are supplied in machine-readable tables.")
    add_text(doc, "Confidence intervals quantify precision of expected outputs under fixed model assumptions. Empirical 2.5th-97.5th percentile ranges describe variation across individual synthetic replications. Neither quantity incorporates empirical parameter uncertainty, structural uncertainty, clinical sampling uncertainty, or external validity.")

    doc.add_heading("Sensitivity and reviewer-motivated analyses", level=2)
    add_text(doc, "The original individual grid varied the robot engagement-logit advantage from 0.00 to 0.35 and session-level downtime from 0% to 30%. The service grid varied day-level downtime from 0% to 30% and clinician review from 4 to 24 minutes. A revised 250-draw scenario ensemble varied engagement, downtime, embodiment effect, refusal, dropout, false-alert probability, risk sensitivity, review time, and fallback, with five first-order replications averaged within each parameter draw.")
    add_text(doc, "Post-review analyses compared last-observation-carried-forward, baseline-observation-carried-forward, and completer-only symptom estimands; varied the human-gated pathway from two to five intake stations; and replaced one parameter block at a time in the screen configuration with the corresponding robot-pathway values. The one-block analysis is a diagnostic decomposition, not an additive attribution or causal mediation analysis.")

    doc.add_heading("Software and verification", level=2)
    add_text(doc, "The simulations were implemented in Python 3.13 using NumPy, pandas, SciPy, Matplotlib, and python-docx. The repository records fixed seeds, dependency constraints, model parameters, intermediate data, figures, tests, and SHA-256 manifests. Automated checks cover deterministic reruns, shared cohorts and demand streams, ranges, impossible events, queue flow, interval fields, editable SVG text, figure fonts, and manuscript-result reconciliation. The command python run_all.py regenerates the primary simulations, reviewer analyses, journal figures, manuscript files, validation checks, and checksums.")

    doc.add_heading("Ethics and use of artificial intelligence", level=2)
    add_text(doc, "Ethics approval and participant consent were not applicable because the study used only synthetic data and computer simulations.")
    add_text(doc, "[Authors to verify and edit before submission] During repository and manuscript revision, OpenAI ChatGPT was used for editorial restructuring, code review, and generation of draft text. All analyses were executed from the repository, numerical outputs were checked against generated files, and the authors take responsibility for the final manuscript.")

    doc.add_heading("Data Availability", level=1)
    add_text(doc, "All synthetic datasets and machine-readable outputs generated for this study are included in the accompanying repository. Before submission, replace this sentence with the name, persistent URL, version, and DOI of the deposited release.")
    doc.add_heading("Code Availability", level=1)
    add_text(doc, "All custom Python code required to reproduce the simulations, analyses, and figures is included in the accompanying repository. Running python run_all.py regenerates the complete workflow. Before submission, deposit the tagged release in a DOI-minting repository, select an open-source license, and insert the persistent citation here.")
    doc.add_heading("Acknowledgements", level=1)
    add_text(doc, "[Insert acknowledgements.] [Insert funding statement here; a separate funding section should not be used. State either the funder and grant information or that the study received no funding.]")
    doc.add_heading("Author contributions", level=1)
    add_text(doc, "[Insert a CRediT statement naming every author by initials and describing individual contributions.]")
    doc.add_heading("Competing interests", level=1)
    add_text(doc, "[Insert a declaration for every author. If none: All authors declare no financial or non-financial competing interests.]")

    doc.add_heading("References", level=1)
    for i, ref in enumerate(REFERENCES, 1):
        p = doc.add_paragraph()
        p.paragraph_format.first_line_indent = Inches(-0.22)
        p.paragraph_format.left_indent = Inches(0.22)
        p.add_run(f"{i}. {ref}")

    doc.add_page_break()
    doc.add_heading("Tables", level=1)
    add_text(doc, "Tables are placed after the reference list for submission formatting.")
    add_text(doc, "Table 1. Pathways and the incremental comparison.", bold_prefix="Table 1.")
    add_table(doc, ["Pathway", "Modeled role", "Interpretation"], [
        ["Usual care or manual", "Human-delivered baseline", "Contextual comparator; no embodiment-specific exposure"],
        ["Content-matched screen", "Same modeled digital content without a body", "Primary reference for the bundled robot-pathway contrast"],
        ["Embodied robot", "Physical interface with realistic faults", "Embodiment plus acceptance, downtime, alert, and physical-burden assumptions"],
        ["Robot plus human gate", "Physical interface with mandatory verification", "Higher modeled detection and fallback plus additional routine review work"],
    ], widths=[1.4, 2.2, 3.3])

    add_text(doc, "Table 2. Primary human-gated pathway contrasts versus the screen.", bold_prefix="Table 2.")
    rows = []
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
        rows.append([scale, outcome, f"{signed(row['mean_difference'])} ({fmt(row['bootstrap_ci_low'])} to {fmt(row['bootstrap_ci_high'])})", unit, "0.000070", interpretation])
    add_table(doc, ["Scale", "Outcome", "Mean difference (95% BCa interval)", "Unit", "Holm-adjusted sign-flip P", "Interpretation"], rows, font_size=7.5)

    add_text(doc, "Table 3. Reviewer-motivated robustness findings.", bold_prefix="Table 3.")
    add_table(doc, ["Issue", "Analysis", "Finding", "Interpretation"], [
        ["Differential attrition", "LOCF, BOCF, and completer-only response", f"Robot-screen contrast {fmt(est.loc['response_locf_percent','robot_minus_screen_mean'])}, {fmt(est.loc['response_bocf_percent','robot_minus_screen_mean'])}, and {fmt(est.loc['response_completers_percent','robot_minus_screen_mean'])} points", "Direction stable; magnitude estimand-dependent"],
        ["Parameter scenario noise", "250 draws with five inner replications", f"Response positive in {fmt(nested.loc['response_positive','percent_of_scenario_draws'],1)}%; completion negative in 100%", "Reduces first-order noise within each scenario"],
        ["Unequal intake stations", "Two to five embodied intake stations", f"Wait penalty remained about {fmt(cap_wait.loc[3,'robot_minus_screen_mean'],1)}-{fmt(cap_wait.loc[5,'robot_minus_screen_mean'],1)} minutes", "Clinician-stage assumptions dominate this configuration"],
        ["Bundled comparator", "One-block-at-a-time substitution", "Embodiment increment improved response; acceptance friction drove completion loss", "Do not interpret the full contrast as a pure embodiment effect"],
    ], font_size=7.7)

    doc.add_page_break()
    doc.add_heading("Figure legends", level=1)
    legends = [
        ("Figure 1", "Synthetic symptom trajectories", "Mean last-observation-carried-forward PHQ-9 across 12 weeks for four pathways. Lines use distinct markers and line styles; shaded bands are 95% BCa bootstrap intervals for the mean across 200 independent repeated synthetic trials."),
        ("Figure 2", "Patient-level outcomes", "Replication distributions for response, remission, and 12-week completion. Box plots show the median and interquartile range, points show individual replication means, and diamonds with error bars show the mean and 95% BCa bootstrap interval."),
        ("Figure 3", "Primary patient-level threshold contrasts", "Mean paired differences between the human-gated robot and the screen across 200 repeated trials. Error bars are 95% BCa bootstrap intervals obtained by resampling intact paired replication identifiers."),
        ("Figure 4", "Patient-level safety and hidden labor", "Replication distributions for false alerts, missed high-risk weeks, clinician review time, and physical near-misses. Box plots and points display the full replication distribution; diamonds and error bars show means and 95% BCa intervals."),
        ("Figure 5", "Service waiting-time distributions", "Mean working-time waits over 200 paired discrete-event replications after a five-day warm-up. Box plots and points show replication distributions; diamonds and error bars show means and 95% BCa intervals."),
        ("Figure 6", "Service safety and access outcomes", "Replication distributions for false alerts, missed high-acuity cases, and abandonment. Box plots and points show paired-replication outputs; diamonds and error bars show means and 95% BCa intervals."),
    ]
    for number, title, body in legends:
        p = doc.add_paragraph()
        p.add_run(f"{number}. {title}. ").bold = True
        p.add_run(body)

    doc.add_heading("Supplementary Information", level=1)
    add_text(doc, "Supplementary Tables S1-S5 and Figures S1-S9 are supplied as one separate PDF. All model methods are reported in the main manuscript.")

    path = MAN / "Physical_AI_Psychiatry_npj_Submission_v4.1.docx"
    doc.save(path)
    return path


def build_supplement() -> Path:
    ind, sys, ind_arm, sys_arm, est, nested, cap, abl = get_data()
    doc = Document()
    setup_doc(doc)
    add_title_page(doc, "Supplementary Information", TITLE)
    add_text(doc, "[Insert author names and affiliations identical to the main manuscript]", italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    add_text(doc, "This file contains extended results, audit tables, and figures. All methods are reported in the main manuscript.")
    doc.add_heading("Contents", level=1)
    for item in ["Supplementary Tables S1-S5", "Supplementary Figures S1-S9"]:
        add_bullet(doc, item)

    doc.add_heading("Supplementary Tables", level=1)
    add_text(doc, "Table S1. Parameter blocks differentiating the screen and human-gated patient pathways.", bold_prefix="Table S1.")
    screen = ARM_CONFIGS["screen_agent"]
    robot = ARM_CONFIGS["robot_hitl"]
    rows = []
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
            rows.append([block, field, str(getattr(screen, field)), str(getattr(robot, field))])
    add_table(doc, ["Block", "Parameter", "Screen", "Robot plus human gate"], rows, font_size=7.7)

    add_text(doc, "Table S2. Endpoint estimand sensitivity for the human-gated robot minus screen contrast.", bold_prefix="Table S2.")
    rows = []
    labels = {
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
    for metric, label in labels.items():
        r = est.loc[metric]
        rows.append([label, fmt(r["robot_minus_screen_mean"]), f"{fmt(r['bootstrap_ci_low'])} to {fmt(r['bootstrap_ci_high'])}", str(int(r["replications"]))])
    add_table(doc, ["Estimand", "Mean difference", "95% BCa interval", "Replications"], rows)

    add_text(doc, "Table S3. Service capacity sensitivity.", bold_prefix="Table S3.")
    wait = cap[cap["metric"] == "mean_wait_difference_minutes"].sort_values("robot_intake_servers")
    throughput = cap[cap["metric"] == "throughput_difference_per_day"].set_index("robot_intake_servers")
    rows = []
    for _, r in wait.iterrows():
        servers = int(r["robot_intake_servers"])
        t = throughput.loc[servers]
        rows.append([str(servers), fmt(r["robot_minus_screen_mean"]), f"{fmt(r['bootstrap_ci_low'])} to {fmt(r['bootstrap_ci_high'])}", fmt(t["robot_minus_screen_mean"],3), f"{fmt(t['bootstrap_ci_low'],3)} to {fmt(t['bootstrap_ci_high'],3)}"])
    add_table(doc, ["Embodied intake stations", "Mean wait difference, min", "95% BCa interval", "Throughput difference/day", "95% BCa interval"], rows, font_size=7.7)

    add_text(doc, "Table S4. Nested scenario-ensemble stability.", bold_prefix="Table S4.")
    rows = []
    for diagnostic, label in [
        ("response_positive", "Response favors robot"),
        ("completion_negative", "Completion favors screen"),
        ("phq_change_favorable", "Mean PHQ-9 change favors robot"),
        ("review_positive", "Review burden higher for robot"),
        ("near_miss_positive", "Physical exposure higher for robot"),
    ]:
        r = nested.loc[diagnostic]
        rows.append([label, fmt(r["percent_of_scenario_draws"],1), f"{fmt(r['scenario_resampling_ci_low'],1)}-{fmt(r['scenario_resampling_ci_high'],1)}", str(int(r["scenario_draws"])), str(int(r["inner_replications_per_draw"]))])
    add_table(doc, ["Diagnostic", "Scenario draws (%)", "Resampling interval (%)", "Draws", "Inner replications"], rows)

    add_text(doc, "Table S5. One-block-at-a-time pathway decomposition.", bold_prefix="Table S5.")
    response = abl[abl["metric"] == "response_difference_percentage_points"].set_index("parameter_block")
    completion = abl[abl["metric"] == "completion_difference_percentage_points"].set_index("parameter_block")
    review = abl[abl["metric"] == "review_minutes_difference"].set_index("parameter_block")
    rows = []
    for block in response.index:
        rows.append([block, fmt(response.loc[block,"mean_difference_vs_screen"]), fmt(completion.loc[block,"mean_difference_vs_screen"]), fmt(review.loc[block,"mean_difference_vs_screen"])])
    add_table(doc, ["Parameter block substituted into screen", "Response difference, points", "Completion difference, points", "Review difference, min"], rows, font_size=7.7)

    captions = [
        ("Figure S1", "Patient-level response sensitivity", "Mean response difference between the human-gated robot and screen as engagement-logit advantage and downtime vary. Open circles mark cells whose 95% bootstrap interval excludes zero in the favorable direction.", "figure_s1_response_sensitivity.png"),
        ("Figure S2", "Nested parameter-scenario uncertainty", "Joint response and completion contrasts across 250 broad illustrative parameter draws, each averaged over five first-order replications. The scenario ranges are stress tests and not posterior distributions.", "figure_s2_nested_parameter_uncertainty.png"),
        ("Figure S3", "Service throughput distributions", "Completed assessments per working day. Box plots and points show 200 replication outputs; diamonds and error bars show means and 95% BCa intervals.", "figure_s3_service_throughput.png"),
        ("Figure S4", "Paired service-level contrasts", "Mean paired differences versus the screen under common arrival, acuity, and latent random streams. Error bars are 95% BCa bootstrap intervals.", "figure_s4_service_contrasts.png"),
        ("Figure S5", "Service break-even sensitivity", "Difference in mean wait between the human-gated robot and screen as downtime and review time vary. Negative values favor the robot; open circles mark cells whose upper 95% bootstrap bound is nonpositive.", "figure_s5_service_break_even.png"),
        ("Figure S6", "Queue warm-up diagnostic", "Mean waiting time with zero, two, five, and ten warm-up days. Error bars are 95% BCa intervals. Warm-up choice does not reverse pathway ordering.", "figure_s6_warmup_diagnostic.png"),
        ("Figure S7", "Endpoint estimand sensitivity", "Robot-screen response and remission contrasts under last observation carried forward, baseline observation carried forward, and completer-only estimands. Error bars are 95% BCa intervals across 200 repeated trials.", "figure_s7_estimand_sensitivity.png"),
        ("Figure S8", "Service capacity sensitivity", "Mean wait difference between the human-gated robot and screen as the number of embodied intake stations varies. Error bars are 95% BCa intervals across 200 paired replications.", "figure_s8_capacity_sensitivity.png"),
        ("Figure S9", "Pathway bundle decomposition", "One-block-at-a-time substitution of human-gated robot parameter blocks into the screen pathway. The analysis is diagnostic and not an additive or causal attribution.", "figure_s9_pathway_bundle_ablation.png"),
    ]
    doc.add_page_break()
    doc.add_heading("Supplementary Figures", level=1)
    for num, title, caption, filename in captions:
        p = doc.add_paragraph()
        p.add_run(f"{num}. {title}. ").bold = True
        p.add_run(caption)
        img = FIG / filename
        if not img.exists():
            raise FileNotFoundError(img)
        doc.add_picture(str(img), width=Inches(6.7))
        doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        if num != captions[-1][0]:
            doc.add_page_break()

    path = MAN / "Physical_AI_Psychiatry_Supplementary_Information_v4.1.docx"
    doc.save(path)
    return path


def build_cover_letter() -> Path:
    doc = Document()
    setup_doc(doc)
    add_text(doc, "[Date]")
    add_text(doc, "Editor in Chief\nnpj Digital Medicine")
    add_text(doc, "Re: Submission of an Article entitled Multiscale simulation stress tests of physical artificial intelligence in psychiatric care")
    add_text(doc, "Dear Editor,")
    add_text(doc, "We submit the enclosed simulation study for consideration as an Article in npj Digital Medicine. The work develops an open, assumption-driven framework that evaluates physical artificial intelligence across two linked decision scales: patient-level benefit, retention, safety, and hidden labor; and service-level waiting, abandonment, detection, and capacity.")
    add_text(doc, "The central contribution is a dual evaluation standard. A physically embodied pathway should not be judged solely by modeled symptom or detection gains; it should also meet prespecified operational and retention criteria against a content-matched screen. In the base scenario, the human-gated robot improved selected model outputs but worsened completion, clinician review burden, waiting, false alerts, and physical exposure. Reviewer-motivated analyses additionally test attrition estimands, nested parameter uncertainty, intake capacity, and the bundled nature of the comparator.")
    add_text(doc, "The manuscript does not claim clinical efficacy or safety. No patient data were used. All simulations, intermediate outputs, editable vector figures, tests, and build scripts will be released in a DOI-minting repository before publication. We believe the framework is relevant to digital medicine because it converts implementation burdens that are often omitted from screen-only evaluations into explicit, reproducible estimands and break-even tests.")
    add_text(doc, "[Authors must add: confirmation of originality and no concurrent consideration; related manuscripts or preprints; author agreement; corresponding-author affiliation, address, telephone, and email; suggested or opposed reviewers if desired; repository or preprint links; and any special collection information.]")
    add_text(doc, "Sincerely,\n[Corresponding author name, degrees]\n[Affiliation]\n[Email and telephone]")
    path = MAN / "Cover_Letter_Draft_v4.1.docx"
    doc.save(path)
    return path


def build_review_report() -> Path:
    ind, sys, ind_arm, sys_arm, est, nested, cap, abl = get_data()
    gated = ARM_CONFIGS["robot_hitl"].name
    sys_gated = CONFIGS["robot_hitl"].name
    doc = Document()
    setup_doc(doc, report=True, landscape=True)
    add_title_page(doc, "Scientific and Reproducibility Review", TITLE, report=True)
    add_text(doc, "Scope: manuscript, Python source, generated datasets, figures, tables, supplementary materials, tests, release files, and current npj Digital Medicine requirements.")
    add_text(doc, "Decision: READY AFTER MAJOR REVISIONS", bold_prefix="Decision:")
    add_text(doc, "The package is computationally strong and substantially improved by the v4.1 revisions, but it is not submission-ready until author metadata and declarations are supplied, an open-source license and DOI-minting release are selected, all AI-use wording is approved, and the authors decide whether the absence of empirical calibration or external validation is acceptable for the target journal.")

    doc.add_heading("Inventory and essential missing materials", level=1)
    add_text(doc, "Supplied and inspected: the 20-page v4.0 DOCX manuscript; a Git-ready ZIP containing 92 files; Python simulation and statistical code; 25 primary machine-readable output files; 12 PNG and 12 SVG figures; eight automated tests; CI configuration; documentation; repository metadata; and the detailed review brief.")
    add_text(doc, "Generated during review: a clean full rerun; reviewer reanalyses; 15 journal-oriented figures in PNG and SVG; a journal-structured v4.1 manuscript; a single supplementary-information file; a cover-letter draft; and this audit report.")
    add_text(doc, "Essential author-supplied items still missing:")
    for item in [
        "Author names, degrees, affiliations, ORCID identifiers, corresponding-author contact details, and final author order.",
        "CRediT contributions, funding declaration, acknowledgements, and financial and non-financial competing interests.",
        "Repository URL, archived release DOI, final software license, and copyright holder.",
        "Author confirmation of the use-of-LLM disclosure and responsibility for all revised text.",
        "Any preprint, related-manuscript, collection, or reviewer information required for submission.",
        "Empirical calibration or external-validation data, if the authors elect to strengthen journal fit before submission.",
    ]:
        add_bullet(doc, item)

    doc.add_heading("1. Executive assessment", level=1)
    add_text(doc, "Contribution. The project provides a reproducible multiscale simulation framework for evaluating content-matched screen and physically embodied psychiatric pathways across symptom thresholds, retention, high-risk detection, human review, physical exposure, waiting, abandonment, and capacity. The strongest conceptual contribution is the requirement to evaluate patient benefit and operational acceptability jointly.")
    add_text(doc, "Strengths. The code uses deterministic seeds, shared synthetic cohorts, paired common demand streams, independent simulation replications, BCa bootstrap intervals, sign-flip tests, multiplicity control, effect sizes, Monte Carlo precision, machine-readable outputs, editable SVG figures, tests, CI, and clear model-internal caveats. The full numerical rerun succeeded and the central conclusions were robust to the new analyses.")
    add_text(doc, "Principal weaknesses. The robot-screen contrast is a bundled pathway comparison, not a pure embodiment effect; all clinical and operational inputs are illustrative; differential attrition makes the symptom estimand consequential; the service model represents one near-capacity configuration; and the manuscript previously did not conform to the current Article structure. The absence of calibration, face validation, or external validation is the largest scientific barrier to acceptance.")
    add_text(doc, "Highest-priority revisions. Retain the qualified pathway framing; define attrition estimands prospectively; preserve the new component and capacity analyses; seek empirical parameter elicitation and stakeholder validation; complete author declarations and repository metadata; and use the v4.1 journal-formatted manuscript and separate supplement.")

    doc.add_heading("2. Major scientific issues", level=1)
    major_rows = [
        ["M1", "Bundled comparator", "The screen and robot differ in engagement, decay, refusal, privacy, downtime, fallback, detection, review, and physical exposure. The contrast cannot identify a causal embodiment effect.", "Relabel as a complete pathway contrast; retain one-block analysis; avoid embodiment-causal language."],
        ["M2", "No empirical calibration or external validation", "Parameters are illustrative and the outputs cannot estimate efficacy, incidence, safety, or service performance.", "Add empirical elicitation, face validation, and external validation, or present explicitly as a methods/hypothesis paper."],
        ["M3", "Differential attrition and LOCF", "The pathway improves response but reduces completion. LOCF is not neutral and the estimated magnitude depends on the estimand.", "Prospectively specify treatment-policy and missing-data estimands; report BOCF and completer sensitivity."],
        ["M4", "Operational acceptability margin", "The original wording treated a zero difference as noninferiority without an externally justified margin.", "Use 'zero-margin non-worsening' or prespecify clinically meaningful waiting, completion, and burden margins."],
        ["M5", "Scenario uncertainty mixed with first-order noise", "One simulation per parameter draw made sign proportions sensitive to Monte Carlo noise.", "Use nested replications; v4.1 averages five per draw."],
        ["M6", "Finite-capacity service model", "The manual pathway is nominally at its intake-capacity boundary, and the screen/robot wait depends on stylized clinician service and abandonment rules.", "Treat manual as contextual; calibrate site-specific capacity; report utilization and horizon sensitivity."],
        ["M7", "Physical reset construct", "The service variable counts routine reset workload on each non-fallback embodied intake, not stochastic safety incidents.", "Rename and define as routine reset work; do not call it an incident rate."],
        ["M8", "Model-internal P values", "Very small P values are generated by repeated simulation under fixed assumptions and can be mistaken for clinical evidence.", "De-emphasize P values in abstract and conclusions; report exact values and emphasize intervals, effects, and model boundary."],
        ["M9", "Journal positioning", "A purely illustrative simulation may be judged insufficiently clinical or empirically grounded for npj Digital Medicine.", "Strengthen methodological novelty and validation, or consider a simulation/health-services journal if empirical work is not feasible."],
    ]
    add_table(doc, ["ID", "Issue", "Why it matters", "Required response"], major_rows, widths=[0.45,1.25,3.1,3.1], font_size=7.4)

    doc.add_heading("3. Minor issues", level=1)
    for item in [
        "The original 16-word punctuated title and 317-word structured abstract did not meet the current Article format; v4.1 uses an 11-word unpunctuated title and a 137-word unstructured abstract.",
        "The original manuscript placed Methods before Results, used Discussion subheadings and separate Limitations and Conclusions, combined Data and Code Availability, and used a separate Funding section. These are corrected in v4.1.",
        "Supplementary figures were embedded in the main DOCX. They are now consolidated into one separate supplement.",
        "Several bar charts showed only means and confidence intervals. The journal figure set uses box plots, replication points, and mean intervals.",
        "The current license and CITATION.cff contain placeholders. This is appropriate for review but blocks public release.",
        "CI previously validated stale outputs without rerunning the models. The revised workflow includes the reviewer analyses and journal build in the end-to-end runner.",
        "SVG and DOCX artifacts are not byte-reproducible because of generated IDs and package timestamps. Scientific values and raster outputs are reproducible; document this distinction.",
        "Parameter-provenance entries should be expanded with empirical sources or elicitation records when calibration begins.",
    ]:
        add_bullet(doc, item)

    doc.add_heading("4. Claim-to-evidence audit", level=1)
    claims = [
        ["Human-gated robot improves modeled response", "Individual repeated-trial contrast", "Fig. 3; Table 2", "individual_microsimulation.py; outputs/individual_contrast_summary.csv", "+6.29 points, 95% BCa 6.09 to 6.50", "Verified; model-internal only"],
        ["Human-gated robot reduces completion", "Individual repeated-trial contrast", "Figs. 2-3; Table 2", "outputs/individual_replication_results.csv", "-5.42 points, -5.69 to -5.17", "Verified; robust across scenarios"],
        ["Symptom result is robust to attrition estimand", "LOCF, BOCF, completer sensitivity", "Fig. S7; Table S2", "reviewer_reanalysis.py", "+6.23, +5.53, +10.21 points", "Direction verified; magnitude changes"],
        ["Robot improves high-risk detection", "Patient and service detection contrasts", "Figs. 4 and 6", "individual_contrast_summary.csv; system_contrast_summary.csv", "Fewer missed events at both scales", "Verified under stylized alert parameters"],
        ["Human gating increases hidden labor", "Review-minute contrast", "Fig. 4; Table 2", "individual_contrast_summary.csv", "+4.38 min/participant", "Verified"],
        ["Waiting worsens despite similar throughput", "Paired service replications", "Fig. 5; Fig. S3", "service_queue_simulation.py", "+34.41 min; -0.160 assessments/day", "Verified"],
        ["Wait penalty is not only fewer robot stations", "Capacity sensitivity", "Fig. S8; Table S3", "reviewer_reanalysis.py", "Penalty remains about 36 min at 3-5 stations", "Verified in current clinic configuration"],
        ["The full contrast is not a pure embodiment effect", "Parameter comparison and one-block analysis", "Fig. S9; Tables S1/S5", "ARM_CONFIGS; reviewer_reanalysis.py", "Different blocks drive benefit and burden", "Verified; manuscript reframed"],
        ["Scenario robustness", "250 broad draws with nested replication", "Fig. S2; Table S4", "individual_parameter_uncertainty_nested.csv", "Response positive 83.2%; completion negative 100%", "Verified only over selected ranges"],
        ["Clinical efficacy or safety", "No empirical data", "Not supported", "No calibration dataset supplied", "None", "Must not be claimed"],
    ]
    add_table(doc, ["Claim", "Analysis", "Display", "Code/data", "Evidence", "Assessment"], claims, font_size=6.9)

    doc.add_heading("5. Code and reproducibility audit", level=1)
    audit_rows = [
        ["Environment", "Python 3.13.5; NumPy 2.3.5; pandas 2.2.3; Matplotlib 3.10.8; SciPy 1.17.0; python-docx 1.2.0", "Verified"],
        ["Tests", "pytest -q", "8 passed"],
        ["Deterministic validation", "python validate_models.py", "Passed all structural checks"],
        ["Full rerun", "Individual model, service model, manuscript builder, validation, reports, checksums", "Completed"],
        ["Numerical reproducibility", "CSV numerical outputs and PNG figures", "Exact reproduction"],
        ["Binary reproducibility", "SVG IDs, DOCX package metadata, manifest", "Not byte-identical; values/appearance equivalent"],
        ["Random streams", "Shared cohort and paired demand streams; deterministic bootstrap/test seeds", "Appropriate and documented"],
        ["Data leakage", "Synthetic data only; no training/test model-selection workflow", "Not applicable; no leakage identified"],
        ["Statistical unit", "Independent replication; intact pair resampling", "Correct"],
        ["Sensitive information", "Secret/credential/absolute-path scan", "No PHI, credentials, or tokens identified"],
        ["CI", "Previously did not rerun primary simulations", "Corrected in v4.1 runner/CI design"],
        ["Release license", "Placeholder proprietary-pending license", "Author decision required"],
    ]
    add_table(doc, ["Area", "Finding", "Status"], audit_rows, font_size=7.4)

    doc.add_heading("6. Reanalysis log", level=1)
    reanalysis_rows = [
        ["R1", "Attrition estimand sensitivity", "Differential completion makes LOCF consequential", "reviewer_reanalysis.py; Table S2; Fig. S7", "Response contrast +6.23 LOCF, +5.53 BOCF, +10.21 completers", "Direction unchanged; magnitude qualified"],
        ["R2", "Nested scenario ensemble", "One run per parameter draw mixed parameter and first-order variability", "individual_parameter_uncertainty_nested*.csv; Fig. S2", "83.2% response-positive; 100% completion-negative", "Central qualitative conclusion unchanged"],
        ["R3", "Service capacity sensitivity", "Robot and screen used different intake-station counts", "service_capacity_sensitivity*.csv; Fig. S8", "Wait penalty persisted at 2-5 stations", "Capacity count alone did not explain result"],
        ["R4", "Pathway block decomposition", "Full contrast bundled embodiment with other implementation assumptions", "patient_pathway_bundle_ablation*.csv; Fig. S9", "Embodiment increment drove response; acceptance friction drove completion loss; oversight drove labor/exposure", "Causal embodiment wording removed"],
        ["R5", "Journal figure rebuild", "Bar charts did not reveal replication distributions", "build_journal_figures.py; figures/journal", "6 main and 9 supplementary figures regenerated in PNG/SVG", "Presentation improved; values unchanged"],
        ["R6", "Manuscript restructure", "Current journal Article format differed from v4.0", "build_review_deliverables.py", "Title, abstract, section order, declarations, tables, legends, and supplement revised", "Scientific interpretation narrowed"],
    ]
    add_table(doc, ["ID", "Change", "Rationale", "Affected files", "Result", "Effect on conclusions"], reanalysis_rows, font_size=6.8)

    doc.add_heading("7. Figure and table audit", level=1)
    figure_rows = [
        ["Fig. 1", "Necessary", "Trajectory encodings relied partly on color", "Use black line styles and distinct markers", "Rebuilt"],
        ["Fig. 2", "Necessary", "Bar chart concealed 200-replication distributions", "Three distribution panels with points and mean intervals", "Replaced"],
        ["Fig. 3", "Necessary", "Only response/completion in original; framing was adequate", "Focused human-gated threshold forest plot", "Rebuilt"],
        ["Fig. 4", "Necessary", "Bar chart concealed distributions", "Four distribution panels", "Replaced"],
        ["Fig. 5", "Necessary", "Manual scenario could be misread as general benchmark", "Retain with capacity-constrained label in text", "Rebuilt"],
        ["Fig. 6", "Necessary", "Bar chart concealed distributions", "Three distribution panels", "Replaced"],
        ["Figs. S1/S5", "Necessary", "Viridis heatmaps are accessible; circles need legend", "Retained with clarified captions", "Acceptable"],
        ["Fig. S2", "Necessary", "Original used one simulation per scenario", "Replaced by nested scenario plot", "Replaced"],
        ["Figs. S7-S9", "Missing", "Key reviewer concerns were not visualized", "Add estimand, capacity, and bundle analyses", "Added"],
        ["Tables 1-3", "Necessary", "Original tables mixed interpretation and compliance", "Condensed main tables and moved extended tables to supplement", "Revised"],
    ]
    add_table(doc, ["Item", "Role", "Issue", "Required action", "v4.1 status"], figure_rows, font_size=7.2)

    doc.add_heading("8. Journal-compliance checklist", level=1)
    journal_rows = [
        ["Article title up to 15 words without punctuation", "Complete", "v4.1 title is 11 words"],
        ["Unstructured abstract up to 150 words", "Complete", "v4.1 abstract is 137 words"],
        ["Introduction without subheadings", "Complete", "Revised"],
        ["Results with subheadings", "Complete", "Revised"],
        ["Discussion without subheadings or separate limitations/conclusions", "Complete", "Revised"],
        ["Methods in main manuscript with subheadings", "Complete", "Revised"],
        ["Data Availability and Code Availability", "Incomplete", "Sections drafted; DOI and URL required"],
        ["Acknowledgements including funding", "Requires author input", "Placeholder retained; no separate Funding section"],
        ["Author contributions", "Requires author input", "CRediT placeholder"],
        ["Competing interests", "Requires author input", "Declaration placeholder"],
        ["Ethics and consent", "Complete", "Not applicable because synthetic data only"],
        ["LLM-use documentation", "Requires author confirmation", "Draft disclosure inserted in Methods"],
        ["Single separate Supplementary Information PDF", "Complete", "Generated v4.1 supplement"],
        ["Figures individually supplied, sans-serif, >=300 dpi", "Complete", "600-dpi PNG plus live-text SVG"],
        ["Distribution-revealing statistical plots", "Complete", "Journal figures use box plots and points"],
        ["Actual P values and statistics/reproducibility section", "Complete", "Exact Monte Carlo P and adjusted P reported"],
        ["Reporting Summary and Editorial Policy Checklist", "Incomplete", "Submission forms must be completed by authors"],
        ["Cover letter", "Requires author input", "Draft supplied"],
        ["Author list, affiliations, corresponding author, ORCID", "Requires author input", "Missing"],
    ]
    add_table(doc, ["Requirement", "Status", "Evidence or action"], journal_rows, font_size=7.3)
    add_text(doc, "Current journal requirements were checked against the official npj Digital Medicine Content Types, Submission Guidelines, and Reporting Standards pages accessed 29 July 2026. Key requirements include an Article title of no more than 15 words without punctuation, an unstructured abstract of no more than 150 words, the order Introduction-Results-Discussion-Methods, mandatory Data Availability, a separate Code Availability section when applicable, funding in Acknowledgements, mandatory author contributions and competing interests, one separate supplementary file, distribution-revealing plots, and documentation of LLM use in Methods.")

    doc.add_heading("9. Repository-readiness checklist", level=1)
    repo_rows = [
        ["README and execution workflow", "Complete", "Updated commands and interpretation boundary"],
        ["Dependency specification", "Complete", "requirements-lock.txt and pyproject.toml"],
        ["Environment/container", "Partial", "Pinned Python dependencies; no container image"],
        ["Source/data/results/figures/tests/docs separation", "Complete", "Clear repository structure"],
        ["Scripts for all manuscript displays", "Complete", "Primary, reviewer, and journal figure builders"],
        ["Automated tests", "Complete but limited", "Eight tests; add numerical snapshot tests for new reanalyses"],
        ["Continuous integration", "Complete after revision", "End-to-end runner recommended"],
        ["License", "Incomplete", "Author must choose OSI-approved license or document restriction"],
        ["CITATION.cff", "Incomplete", "Author and repository placeholders"],
        ["DOI-minting archive", "Incomplete", "Create tagged Zenodo/Code Ocean release"],
        ["Sensitive-data scan", "Complete", "No PHI, credentials, or absolute local paths found"],
        ["Runtime documentation", "Partial", "Add hardware-specific expected runtime"],
        ["Result-to-script mapping", "Complete", "Audit table and docs supplied"],
        ["Binary reproducibility note", "Complete", "Scientific versus byte-level distinction documented"],
    ]
    add_table(doc, ["Item", "Status", "Action/evidence"], repo_rows, font_size=7.3)

    doc.add_heading("10. Revised materials", level=1)
    revised = [
        "manuscript/Physical_AI_Psychiatry_npj_Submission_v4.1.docx - journal-structured main manuscript.",
        "manuscript/Physical_AI_Psychiatry_Supplementary_Information_v4.1.docx and PDF - single supplement with Tables S1-S5 and Figures S1-S9.",
        "manuscript/Cover_Letter_Draft_v4.1.docx - author-completion draft.",
        "reviewer_reanalysis.py and outputs/reviewer_reanalysis/ - attrition, nested scenario, capacity, and bundle analyses.",
        "build_journal_figures.py and figures/journal/ - six main and nine supplementary PNG/SVG figures.",
        "build_review_deliverables.py - reproducible manuscript, supplement, cover letter, and report builder.",
        "docs/SCIENTIFIC_AND_REPRODUCIBILITY_REVIEW_v4.1.docx - this report.",
    ]
    for item in revised:
        add_bullet(doc, item)

    doc.add_heading("11. Unresolved author queries", level=1)
    queries = [
        "Who are the authors, what is the final order, and what are their degrees, affiliations, ORCID identifiers, and individual CRediT roles?",
        "What corresponding-author email, telephone number, and postal affiliation should be used?",
        "Was the work funded? If yes, provide funder names, grant numbers, and funder roles; if no, approve the no-funding statement.",
        "Do any authors have financial or non-financial competing interests?",
        "Which open-source license and copyright holder should replace the current placeholder?",
        "What repository, tagged version, URL, and DOI will be cited?",
        "Do the authors approve the draft disclosure of ChatGPT use, and was any other generative AI used?",
        "Will the authors obtain empirical parameter elicitation, patient/clinician face validation, or external operational validation before submission?",
        "Should zero-margin non-worsening remain the operational threshold, or should clinically meaningful margins be elicited and prespecified?",
        "Are there related manuscripts, preprints, prior conference abstracts, or overlapping submissions that must be disclosed?",
    ]
    for q in queries:
        add_number(doc, q)

    doc.add_heading("12. Final readiness decision", level=1)
    add_text(doc, "READY AFTER MAJOR REVISIONS", bold_prefix="READY AFTER MAJOR REVISIONS")
    add_text(doc, "Justification. The computational package is reproducible, transparent, and substantially stronger after the reviewer analyses and journal restructuring. The main findings are internally supported and the central qualitative conclusion did not reverse. However, the work remains an uncalibrated assumption-driven simulation; the principal robot-screen comparison is bundled; journal-critical author metadata and declarations are missing; the license and repository DOI are unresolved; and the authors must accept the revised claim boundary and AI disclosure. Submission before these items are resolved would be premature.")

    doc.add_heading("Official journal sources consulted", level=1)
    sources = [
        "npj Digital Medicine. Content types. https://www.nature.com/npjdigitalmed/content-types",
        "npj Digital Medicine. Submission guidelines. https://www.nature.com/npjdigitalmed/for-authors-and-referees/submission-guidelines",
        "npj Digital Medicine. Reporting standards and availability of data, materials, code and protocols. https://www.nature.com/npjdigitalmed/editorial-policies/reporting-standards",
    ]
    for s in sources:
        add_bullet(doc, f"{s} (accessed {ACCESS_DATE}).")

    path = DELIV / "Scientific_and_Reproducibility_Review_v4.1.docx"
    doc.save(path)
    return path


def main():
    paths = [build_manuscript(), build_supplement(), build_cover_letter(), build_review_report()]
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
