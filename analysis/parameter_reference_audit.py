"""Remove misleading automated evidence references and normalize finite precision.
References are explanatory context only; no simulation coefficient is claimed
empirically estimated from a source unless it truly is a scale anchor.
"""
from pathlib import Path
import pandas as pd, re
ROOT=Path(__file__).resolve().parents[1]
FILES=[ROOT/'config'/'individual_parameter_dictionary.csv', ROOT/'config'/'service_parameter_dictionary.csv']
ANCHORS={
 'baseline_phq9':'[20,31]',
 'phq9_bounds':'[20,31]',
 'response_definition':'[20,21]',
 'remission_definition':'[20,21]',
 'engagement_intercept':'[2,3,8,9,39] (mechanism only; coefficient hypothetical)',
 'embodiment_effect':'[2,3,5,8,9] (mechanism only; increment hypothetical)',
 'weekly_decay':'[27-30] (adherence direction only)',
 'initial_refusal':'[27-30] (engagement/attrition context only)',
 'discomfort_dropout':'[27-30] (dropout context only)',
 'downtime':'[2,3,39] (risk category only)',
 'downtime_day_probability':'[2,3,39] (risk category only)',
 'false_alert_probability':'[40] (alert-burden context only)',
 'review_minutes_per_alert':'[17,40] (workflow context; minutes assumed)',
 'clinician_review_minutes':'[17,40] (workflow context; minutes assumed)',
 'arrivals_per_day':'[17] (simulation context; rate assumed)',
 'physical_near_miss_per_active_week':'[1,2] (risk class only; rate placeholder)',
 'physical_reset_minutes':'[2,39] (workflow context; duration assumed)',
 'clinician_summary_saving_minutes':'[17] (workflow context; saving assumed)',
 'crisis_sensitivity':'No empirical calibration; scenario assumption',
 'high_acuity_detection_sensitivity':'No empirical calibration; scenario assumption',
 'service_time_distribution':'[17-19] (method class only)',
}
def round_long_literals(s):
  def sub(m):
    x=float(m.group(0));return f'{x:.5f}'.rstrip('0').rstrip('.')
  return re.sub(r'(?<![A-Za-z0-9])[-+]?\d+\.\d{11,}',sub,str(s))
for path in FILES:
    df=pd.read_csv(path,dtype=str,keep_default_na=False)
    for i,r in df.iterrows():
        p=r['parameter'];
        ref=ANCHORS.get(p,'Not parameter-specific: uncalibrated structural or operational assumption')
        df.at[i,'supporting_references']=ref
        # Avoid broad class of literature named as validation of numeric magnitude.
        df.at[i,'calibration_status']=r['calibration_status'] if r['calibration_status'] else 'Not empirically calibrated'
        for col in df.columns:
            if col not in ['supporting_references']:
                df.at[i,col]=round_long_literals(r[col]).replace('Not varied in current global analysis','Not varied in global sensitivity analysis')
    df.to_csv(path,index=False)
    side=('Individual' if 'individual_' in path.name else 'Service')
    out=ROOT/'publication'/('supplementary_data_patient_parameters.csv' if side=='Individual' else 'supplementary_data_service_parameters.csv')
    out.parent.mkdir(exist_ok=True)
    df.to_csv(out,index=False)
    print(path.name,len(df),'rows; evidence repaired; released',out.relative_to(ROOT))
