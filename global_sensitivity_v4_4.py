"""Higher-precision global sensitivity audit, with design-row CRN and reproducible diagnostics.

The study is a stress test of a stochastic, uncalibrated model, not empirical
parameter uncertainty. Scrambled Sobol, Saltelli A/B cross matrices, Jansen's
sum-of-squares total-order estimator, and second-order Saltelli estimates.

Each row (A_i, B_i, AB_ij, BA_ij) uses the same latent patient/cohort or the
same maximal-demand Poisson arrival stream. Service demand is evaluated with
Poisson thinning to preserve CRN when rate is a Sobol input.
"""
from __future__ import annotations
import os, json, time
from pathlib import Path
from dataclasses import replace
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
from global_sensitivity import (Parameter, INDIVIDUAL_PARAMETERS, SERVICE_PARAMETERS,
                                INDIVIDUAL_OUTCOMES, SERVICE_OUTCOMES, saltelli_design,
                                bootstrap_sobol)
from individual_microsimulation import ARM_CONFIGS, simulate_arm, summarize as summarize_individual
from service_queue_simulation import CONFIGS, generate_random_stream, simulate_one_from_stream

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'outputs'/'global_sensitivity_v4_4'
SEED=20261108

def _cfg_ind(x):
    values = {p.name:(int(np.clip(np.rint(v),p.low,p.high)) if p.discrete else float(v)) for p,v in zip(INDIVIDUAL_PARAMETERS,x)}
    scr=ARM_CONFIGS['screen_agent']
    return replace(ARM_CONFIGS['robot_hitl'],
      engagement_intercept=scr.engagement_intercept+values['engagement_logit_advantage'],
      embodiment_effect=values['embodiment_effect'], downtime=values['downtime'],
      initial_refusal=values['initial_refusal'], privacy_penalty=values['privacy_penalty'],
      discomfort_dropout=values['discomfort_dropout'], crisis_sensitivity=values['crisis_sensitivity'],
      false_alert_probability=values['false_alert_probability'],
      review_minutes_per_alert=values['review_minutes_per_alert'],
      fallback_screen_probability=values['fallback_screen_probability'],
      routine_audit_minutes=values['routine_audit_minutes'],
      physical_near_miss_per_active_week=values['physical_near_miss_per_active_week'])

def _cfg_svc(x, days):
    vals={p.name:(int(np.clip(np.rint(v),p.low,p.high)) if p.discrete else float(v)) for p,v in zip(SERVICE_PARAMETERS,x)}
    common=dict(days=days,arrivals_per_day=vals['arrivals_per_day'],clinician_servers=vals['clinician_servers'])
    scr=replace(CONFIGS['screen'],**common)
    robot=replace(CONFIGS['robot_hitl'],**common,
      intake_servers=vals['intake_servers'], intake_minutes_mean=vals['intake_minutes_mean'],
      downtime_day_probability=vals['downtime_day_probability'],
      incomplete_probability=vals['incomplete_probability'],
      clinician_summary_saving_minutes=vals['clinician_summary_saving_minutes'],
      clinician_review_minutes=vals['clinician_review_minutes'],
      false_alert_probability=vals['false_alert_probability'],
      high_acuity_detection_sensitivity=vals['high_acuity_detection_sensitivity'],
      physical_reset_minutes=vals['physical_reset_minutes'])
    return scr,robot

IND_KEYS=list(INDIVIDUAL_OUTCOMES)
SVC_KEYS=list(SERVICE_OUTCOMES)

def _ind_metric(a,b):
    return np.array([
      b['response_percent']-a['response_percent'],
      b['completion_percent']-a['completion_percent'],
      b['mean_phq9_change']-a['mean_phq9_change'],
      b['mean_clinician_review_minutes']-a['mean_clinician_review_minutes'],
      b['missed_crises_per_100_crisis_weeks']-a['missed_crises_per_100_crisis_weeks'],
      b['physical_near_misses_per_100']-a['physical_near_misses_per_100']])

def _svc_metric(a,b):
    return np.array([
      b['mean_wait_minutes']-a['mean_wait_minutes'],
      b['p90_wait_minutes']-a['p90_wait_minutes'],
      b['throughput_per_day']-a['throughput_per_day'],
      b['abandonment_percent']-a['abandonment_percent'],
      b['false_alerts_per_100_arrivals']-a['false_alerts_per_100_arrivals'],
      b['missed_high_acuity_percent']-a['missed_high_acuity_percent'],
      b['mean_clinician_utilization_percent']-a['mean_clinician_utilization_percent']])

def _evaluate_row(task):
    model,i,vectors,n_inner,n_per_arm,days=task
    out=[]
    if model=='individual':
        configs=[_cfg_ind(x) for x in vectors]
        rs=np.zeros((len(vectors),len(IND_KEYS)))
        for rep in range(n_inner):
            ss=SEED+30_000_000+i*1009+rep*1000003
            screen,_=simulate_arm(ARM_CONFIGS['screen_agent'], n=n_per_arm,weeks=12,seed=ss,cohort_seed=ss,event_seed=ss+17)
            s=summarize_individual(screen)
            for j,cfg in enumerate(configs):
                robot,_=simulate_arm(cfg,n=n_per_arm,weeks=12,seed=ss,cohort_seed=ss,event_seed=ss+37)
                rs[j]+=_ind_metric(s,summarize_individual(robot)) / n_inner
    else:
        configs=[_cfg_svc(x,days) for x in vectors]
        rs=np.zeros((len(vectors),len(SVC_KEYS)))
        cache={}
        for rep in range(n_inner):
            ss=SEED+40_000_000+i*1009+rep*1000003
            base=replace(CONFIGS['screen'],days=days,arrivals_per_day=45.0)
            outage,full=generate_random_stream(base,ss)
            # An independent, fixed Bernoulli-uniform for each arrival ensures
            # exact CRN across all values of the Poisson demand-rate input.
            keep=np.random.default_rng(ss+9876543).random(len(full))
            for j,(screen_cfg,robot_cfg) in enumerate(configs):
                demand=screen_cfg.arrivals_per_day
                stream=[row for row,u in zip(full,keep) if u<demand/45.0]
                key=(float(demand),int(screen_cfg.clinician_servers))
                if key not in cache: # cache depends on independent replicate too
                    cache[key]=simulate_one_from_stream(screen_cfg,outage,stream)
                r=simulate_one_from_stream(robot_cfg,outage,stream)
                rs[j]+=_svc_metric(cache[key],r)/n_inner
            cache.clear()
    return i,rs

def main(n_base=1024,inner_replications=2,n_per_arm=350,days=18,workers=4):
    DEST.mkdir(parents=True,exist_ok=True)
    allmain=[]; allsecond=[]
    for model,params,outs in [('individual',INDIVIDUAL_PARAMETERS,INDIVIDUAL_OUTCOMES),('service',SERVICE_PARAMETERS,SERVICE_OUTCOMES)]:
        st=time.time(); d=len(params)
        a,b,ab,ba=saltelli_design(params,n_base,SEED+(1 if model=='individual' else 2))
        matrices=[a,b]+ab+ba
        outcomes=np.empty((len(matrices),n_base,len(outs)))
        tasks=((model,i,[m[i] for m in matrices],inner_replications,n_per_arm,days) for i in range(n_base))
        with ProcessPoolExecutor(max_workers=workers) as pool:
            for done,(i,values) in enumerate(pool.map(_evaluate_row,tasks,chunksize=2),1):
                outcomes[:,i,:]=values
                if done%64==0:print(f'{model} {done}/{n_base}, {round(time.time()-st)} s',flush=True)
        # full matrices saved for independent re-calculation; fixed seeds per row
        raw=DEST/'raw';raw.mkdir(exist_ok=True)
        inf=[];outf=[]
        for m,(x,y) in enumerate(zip(matrices,outcomes)):
            label=('A' if m==0 else 'B' if m==1 else f'AB_{m-1}' if m<2+d else f'BA_{m-1-d}')
            f=pd.DataFrame(x,columns=[p.name for p in params]);f.insert(0,'sample_id',range(n_base));f.insert(0,'matrix',label);inf.append(f)
            f=pd.DataFrame(y,columns=outs);f.insert(0,'sample_id',range(n_base));f.insert(0,'matrix',label);outf.append(f)
        pd.concat(inf,ignore_index=True).to_csv(raw/f'{model}_saltelli_design_inputs.csv',index=False)
        pd.concat(outf,ignore_index=True).to_csv(raw/f'{model}_saltelli_matrix_outputs.csv',index=False)
        tables=[pd.DataFrame(outcomes[j],columns=outs) for j in range(len(matrices))]
        mdf=[];sdf=[]
        for k,outcome in enumerate(outs):
            main,second=bootstrap_sobol(tables[0],tables[1],tables[2:2+d],tables[2+d:],
                                        [p.name for p in params],outcome,n_boot=350,seed=SEED+10000+k)
            main.insert(0,'model',model);main.insert(1,'outcome',outcome)
            main['parameter_label']=main.parameter.map({p.name:p.label for p in params})
            main['outcome_label']=outs[outcome]
            main['S1_gt_ST']=main.S1>main.ST
            main['sum_S1']=main.S1.sum()
            main['S1_estimator']='Saltelli covariance'
            main['ST_estimator']='Jansen squared difference'
            # Formula-based estimator benchmark for finite-sample stability.
            ya=tables[0][outcome].to_numpy();yb=tables[1][outcome].to_numpy()
            var=np.var(np.r_[ya,yb],ddof=1)
            main['S1_Jansen']= [1-0.5*np.mean((yb-tables[2+j][outcome].to_numpy())**2)/var for j in range(d)] if var else np.nan
            second.insert(0,'model',model);second.insert(1,'outcome',outcome)
            second['parameter_1_label']=second.parameter_1.map({p.name:p.label for p in params})
            second['parameter_2_label']=second.parameter_2.map({p.name:p.label for p in params})
            second['outcome_label']=outs[outcome]
            main['n_base']=second['n_base']=n_base
            main['inner_replications']=second['inner_replications']=inner_replications
            mdf.append(main);sdf.append(second)
        allmain.extend(mdf);allsecond.extend(sdf)
        print(f'{model} completed in {round(time.time()-st)} seconds',flush=True)
    main=pd.concat(allmain,ignore_index=True);second=pd.concat(allsecond,ignore_index=True)
    main.to_csv(DEST/'sobol_first_total_indices.csv',index=False)
    second.to_csv(DEST/'sobol_second_order_indices.csv',index=False)
    diagnostics=main.groupby(['model','outcome']).agg(sum_first_order=('S1','sum'),violating_pairs=('S1_gt_ST','sum'),max_s1=('S1','max'),max_total=('ST','max')).reset_index()
    diagnostics.to_csv(DEST/'estimator_diagnostics.csv',index=False)
    metadata={'method':'Scrambled Sobol A/B cross design; Saltelli covariance S1, Jansen ST, Saltelli second-order; CRN synchronized by design row',
              'n_base':n_base,'inner_replications':inner_replications,'participants_per_arm_per_replication':n_per_arm,'observed_service_days':days,
              'seed':SEED,'input_parameter_distributions':'Independent uniform, structural stress-test ranges not posterior uncertainty',
              'service_arrivals':'Single maximum-rate Poisson stream thinned by fixed uniforms per design row to preserve nested arrivals under changing demand',
              'n_evaluations':{'individual':int(n_base*(2+2*len(INDIVIDUAL_PARAMETERS))),'service':int(n_base*(2+2*len(SERVICE_PARAMETERS)))},'bootstrap_resamples':350,
              'disclaimer':'Raw finite-sample estimator values and uncertainty intervals retained without truncation or forced normalization; potentially unstable indices are not interpreted.'}
    (DEST/'analysis_metadata.json').write_text(json.dumps(metadata,indent=2))
    print('ESTIMATOR DIAGNOSTICS',diagnostics.to_string(index=False),flush=True)

if __name__=='__main__':
 import argparse
 ap=argparse.ArgumentParser()
 ap.add_argument('--n-base',type=int,default=1024);ap.add_argument('--inner',type=int,default=2)
 ap.add_argument('--patients',type=int,default=350);ap.add_argument('--days',type=int,default=18);ap.add_argument('--workers',type=int,default=4)
 args=ap.parse_args();main(args.n_base,args.inner,args.patients,args.days,args.workers)
