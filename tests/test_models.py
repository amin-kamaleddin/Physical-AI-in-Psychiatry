from dataclasses import replace
from pathlib import Path
import json
import re
import zipfile

import numpy as np
import pandas as pd

from individual_microsimulation import ARM_CONFIGS, simulate_arm
from service_queue_simulation import CONFIGS, generate_random_stream, simulate_one
from stats_utils import bootstrap_mean_ci, holm_adjust, paired_contrast_statistics


ROOT = Path(__file__).resolve().parents[1]


def test_individual_is_deterministic_and_shares_baseline():
    a, aw = simulate_arm(ARM_CONFIGS['screen_agent'], n=160, weeks=4, seed=101)
    b, bw = simulate_arm(ARM_CONFIGS['screen_agent'], n=160, weeks=4, seed=101)
    pd.testing.assert_frame_equal(a, b)
    pd.testing.assert_frame_equal(aw, bw)
    robot, _ = simulate_arm(ARM_CONFIGS['robot_hitl'], n=160, weeks=4, seed=101)
    np.testing.assert_allclose(a['baseline_phq9'], robot['baseline_phq9'])


def test_nonembodied_arm_cannot_generate_physical_near_miss():
    screen, _ = simulate_arm(ARM_CONFIGS['screen_agent'], n=300, weeks=6, seed=202)
    assert screen['physical_near_misses'].sum() == 0
    assert screen['week12_phq9_locf'].between(0, 27).all()


def test_queue_accounting_and_common_demand():
    screen = replace(CONFIGS['screen'], days=5, warmup_days=1, arrivals_per_day=10)
    robot = replace(CONFIGS['robot_hitl'], days=5, warmup_days=1, arrivals_per_day=10)
    s = simulate_one(screen, seed=303)
    r = simulate_one(robot, seed=303)
    assert s['arrivals'] == s['completed'] + s['abandoned']
    assert r['arrivals'] == r['completed'] + r['abandoned']
    assert s['arrivals'] == r['arrivals']
    assert generate_random_stream(screen, 303)[1] == generate_random_stream(robot, 303)[1]


def test_bootstrap_and_randomization_are_deterministic():
    x = np.array([1.0, 1.5, 2.0, 0.5, 1.25, 1.75])
    a = bootstrap_mean_ci(x, n_resamples=1_000, seed='unit-test')
    b = bootstrap_mean_ci(x, n_resamples=1_000, seed='unit-test')
    assert a == b
    assert a['bootstrap_ci_low'] < a['mean'] < a['bootstrap_ci_high']
    stats = paired_contrast_statistics(
        x, label='unit-paired', bootstrap_resamples=1_000, permutation_resamples=2_000
    )
    assert stats['sign_flip_pvalue'] > 0
    assert stats['bootstrap_ci_low'] > 0
    adjusted = holm_adjust([0.01, 0.02, 0.2])
    assert np.all(adjusted >= np.array([0.01, 0.02, 0.2]))
    assert np.all(adjusted <= 1)


def test_publication_outputs_and_editable_svgs_exist():
    pngs = sorted((ROOT / 'figures' / 'model_outputs' / 'png').glob('*.png'))
    svgs = sorted((ROOT / 'figures' / 'model_outputs' / 'svg').glob('*.svg'))
    assert len(pngs) == 12
    assert len(svgs) == 12
    for p in svgs:
        text = p.read_text(encoding='utf-8')
        assert '<text' in text
        assert '<image' not in text
        assert "'Arial', 'Arimo'" in text
        sizes = [float(x) for x in re.findall(r'font-size:\s*([0-9.]+)', text)]
        assert sizes and min(sizes) >= 10.0


def test_bootstrap_outputs_and_statistical_fields_exist():
    for filename in ['individual_contrast_summary.csv', 'system_contrast_summary.csv']:
        df = pd.read_csv(ROOT / 'results' / filename)
        required = {
            'bootstrap_ci_low', 'bootstrap_ci_high', 'bootstrap_resamples',
            'paired_t_pvalue', 'sign_flip_pvalue', 'holm_sign_flip_pvalue',
            'cohen_dz', 'mcse_mean_difference', 'replication_p025_difference',
            'bootstrap_seed', 'randomization_seed', 'minimum_monte_carlo_pvalue',
            'paired_t_degrees_of_freedom', 'holm_family_size', 'rng_algorithm',
            'replication_p975_difference',
        }
        assert required.issubset(df.columns)
        assert (df['bootstrap_ci_low'] <= df['mean_difference']).all()
        assert (df['mean_difference'] <= df['bootstrap_ci_high']).all()
        assert (df['holm_sign_flip_pvalue'] >= df['sign_flip_pvalue'] - 1e-15).all()
        assert (df['bootstrap_resamples'] == 10_000).all()
        assert (df['replications'] == 200).all()
        assert (df['holm_family_size'] == 7).all()
        assert (df['minimum_monte_carlo_pvalue'] == 1 / 100_001).all()
        assert (df['alternative'] == 'two-sided').all()

    assert (ROOT / 'results' / 'individual_weekly_bootstrap_summary.csv').exists()
    assert (ROOT / 'results' / 'individual_parameter_uncertainty_summary.csv').exists()
    assert (ROOT / 'results' / 'statistical_analysis_summary.csv').exists()
    assert (ROOT / 'docs' / 'STATISTICAL_METHODS.md').exists()


def test_current_manuscript_contains_main_displays_and_sources():
    docx = ROOT / 'publication' / 'manuscript.docx'
    supplementary = ROOT / 'publication' / 'supplementary_information.docx'
    assert docx.stat().st_size > 100_000
    assert supplementary.stat().st_size > 20_000
    with zipfile.ZipFile(docx) as zf:
        embedded = [name for name in zf.namelist() if name.startswith('word/media/')]
    assert len(embedded) == 6
    from docx import Document
    manuscript = Document(docx)
    text = ' '.join(p.text for p in manuscript.paragraphs)
    assert len(manuscript.tables) == 4
    assert 'bias-corrected and accelerated' in text
    assert 'Holm' in text
    assert 'References' in text
    assert 'patient benefit' in text.lower()


def test_manuscript_key_results_match_generated_contrasts():
    key = json.loads((ROOT / 'results' / 'manuscript_key_results.json').read_text(encoding='utf-8'))
    individual = pd.read_csv(ROOT / 'results' / 'individual_contrast_summary.csv')
    service = pd.read_csv(ROOT / 'results' / 'system_contrast_summary.csv')

    gate = 'Embodied robot + human safety gate'
    response = individual[(individual['comparator'] == gate) & (individual['metric'] == 'response_percent')].iloc[0]
    completion = individual[(individual['comparator'] == gate) & (individual['metric'] == 'completion_percent')].iloc[0]
    wait = service[(service['comparator'] == gate) & (service['metric'] == 'mean_wait_minutes')].iloc[0]

    assert key['individual_replications'] == int(response['replications']) == 200
    assert key['service_replications'] == int(wait['replications']) == 200
    assert key['response_pp']['mean_difference'] == response['mean_difference']
    assert key['response_pp']['p025_difference'] == response['bootstrap_ci_low']
    assert key['completion_pp']['mean_difference'] == completion['mean_difference']
    assert key['mean_wait_minutes']['mean_difference'] == wait['mean_difference']


def test_structural_diagnostics_and_publication_assets_exist():
    review = ROOT / 'results' / 'diagnostics'
    required = [
        'individual_estimand_sensitivity_summary.csv',
        'individual_parameter_uncertainty_nested_summary.csv',
        'service_capacity_sensitivity_summary.csv',
        'patient_pathway_bundle_ablation_summary.csv',
        'structural_sensitivity_summary.json',
    ]
    for name in required:
        assert (review / name).stat().st_size > 0

    est = pd.read_csv(review / 'individual_estimand_sensitivity_summary.csv').set_index('metric')
    assert est.loc['response_locf_percent', 'robot_minus_screen_mean'] > 0
    assert est.loc['response_bocf_percent', 'robot_minus_screen_mean'] > 0
    assert est.loc['completion_percent', 'robot_minus_screen_mean'] < 0

    nested = pd.read_csv(review / 'individual_parameter_uncertainty_nested_summary.csv').set_index('diagnostic')
    assert nested.loc['completion_negative', 'percent_of_scenario_draws'] == 100.0
    assert nested.loc['response_positive', 'inner_replications_per_draw'] == 5

    assert len(list((ROOT / 'figures' / 'individual_displays' / 'png').glob('*.png'))) == 17
    assert len(list((ROOT / 'figures' / 'individual_displays' / 'svg').glob('*.svg'))) == 17
    for path in [
        ROOT / 'publication' / 'source_material/integrated_model_text.docx',
        ROOT / 'publication' / 'manuscript.docx',
        ROOT / 'publication' / 'supplementary_information.docx',
    ]:
        assert path.stat().st_size > 20_000

    active = ROOT / 'publication' / 'manuscript.docx'
    with zipfile.ZipFile(active) as zf:
        embedded = [name for name in zf.namelist() if name.startswith('word/media/')]
        document_xml = zf.read('word/document.xml').decode('utf-8')
    assert len(embedded) == 6
    assert 'Reimagining Psychiatric Care with Physical AI' in document_xml
    for number in range(1, 7):
        assert f'Figure {number}' in document_xml
    for number in range(1, 5):
        assert f'Table {number}' in document_xml


def test_parameter_documentation_and_global_sensitivity_artifacts_exist():
    from dataclasses import fields
    from individual_microsimulation import ArmConfig
    from service_queue_simulation import QueueConfig

    individual_dictionary = pd.read_csv(ROOT / 'config' / 'individual_parameter_dictionary.csv')
    service_dictionary = pd.read_csv(ROOT / 'config' / 'service_parameter_dictionary.csv')

    required_columns = {
        'parameter', 'unit_or_scale', 'functional_role', 'base_case_value_or_distribution',
        'neutral_assumption', 'skeptical_assumption', 'global_range',
        'selection_and_range_rationale', 'ordering_rationale', 'evidence_class',
        'supporting_references', 'calibration_status',
    }
    assert required_columns.issubset(individual_dictionary.columns)
    assert required_columns.issubset(service_dictionary.columns)
    assert {f.name for f in fields(ArmConfig)} - {'name'} <= set(individual_dictionary['parameter'])
    assert {f.name for f in fields(QueueConfig)} - {'name'} <= set(service_dictionary['parameter'])

    for path in [
        ROOT / 'docs' / 'MODEL_SPECIFICATION.md',
        ROOT / 'docs' / 'ELICITATION_AND_VALIDATION_PROTOCOL.md',
        ROOT / 'config' / 'parameter_elicitation_template.csv',
        ROOT / 'results' / 'assumption_stress_tests' / 'neutral_skeptical_contrast_summary.csv',
        ROOT / 'results' / 'global_sensitivity_screening' / 'sobol_first_total_indices.csv',
        ROOT / 'results' / 'global_sensitivity_screening' / 'sobol_second_order_indices.csv',
        ROOT / 'results' / 'global_sensitivity_screening' / 'analysis_metadata.json',
    ]:
        assert path.stat().st_size > 0

    status_text = (ROOT / 'docs' / 'ELICITATION_AND_VALIDATION_PROTOCOL.md').read_text(encoding='utf-8')
    assert 'without empirical calibration' in status_text.lower() and 'prospective' in status_text.lower()
    assert 'face-validation' in status_text.lower()

    global_main = pd.read_csv(ROOT / 'results' / 'global_sensitivity_screening' / 'sobol_first_total_indices.csv')
    global_second = pd.read_csv(ROOT / 'results' / 'global_sensitivity_screening' / 'sobol_second_order_indices.csv')
    assert {'S1', 'ST', 'S1_low', 'S1_high', 'ST_low', 'ST_high'}.issubset(global_main.columns)
    assert {'S2', 'S2_low', 'S2_high'}.issubset(global_second.columns)
    assert set(global_main['model']) == {'individual', 'service'}


def test_sobol_estimators_recover_ishigami_main_total_and_interaction_indices():
    from sobol_design_and_screening import Parameter, saltelli_design, sobol_indices

    parameters = [
        Parameter('x1', 'x1', -np.pi, np.pi, ''),
        Parameter('x2', 'x2', -np.pi, np.pi, ''),
        Parameter('x3', 'x3', -np.pi, np.pi, ''),
    ]
    A, B, AB, BA = saltelli_design(parameters, n_base=4096, seed=123)

    def evaluate(matrix):
        y = (
            np.sin(matrix[:, 0])
            + 7.0 * np.sin(matrix[:, 1]) ** 2
            + 0.1 * matrix[:, 2] ** 4 * np.sin(matrix[:, 0])
        )
        return pd.DataFrame({'y': y})

    main, second = sobol_indices(
        evaluate(A), evaluate(B), [evaluate(x) for x in AB], [evaluate(x) for x in BA],
        [p.name for p in parameters], 'y'
    )
    main = main.set_index('parameter')
    second = second.set_index(['parameter_1', 'parameter_2'])

    assert np.isclose(main.loc['x1', 'S1'], 0.3139, atol=0.01)
    assert np.isclose(main.loc['x2', 'S1'], 0.4424, atol=0.01)
    assert np.isclose(main.loc['x3', 'S1'], 0.0, atol=0.01)
    assert np.isclose(main.loc['x1', 'ST'], 0.5576, atol=0.01)
    assert np.isclose(main.loc['x3', 'ST'], 0.2437, atol=0.01)
    assert np.isclose(second.loc[('x1', 'x3'), 'S2'], 0.2437, atol=0.01)


def test_integrated_manuscript_contains_complete_new_analysis_sequence():
    active = ROOT / 'publication' / 'source_material/integrated_model_text.docx'
    with zipfile.ZipFile(active) as zf:
        embedded = [name for name in zf.namelist() if name.startswith('word/media/')]
        document_xml = zf.read('word/document.xml').decode('utf-8')
    assert len(embedded) == 17
    for number in range(1, 18):
        assert f'Figure {number}.' in document_xml
    for number in range(1, 16):
        assert f'Table {number}.' in document_xml
    assert 'neutral and skeptical assumptions' in document_xml
    assert 'Global interaction-aware sensitivity' in document_xml
    assert 'complete operational specification' in document_xml
    assert 'Empirical calibration' in document_xml
