"""Create six high-resolution, vector-editable, multi-panel journal display figures.
All figures use Arimo (Arial-metric fallback), >=10 pt at final 6.8-inch width.
"""
from pathlib import Path
from matplotlib import pyplot as plt, patches
import matplotlib as mpl
import numpy as np
import pandas as pd
from figure_utils import save_figure
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results'; FIG=ROOT/'figures'/'main'; FIG.mkdir(exist_ok=True)
NAVY='#183655'; TEAL='#007C83'; PURPLE='#6750A4'; ORANGE='#B65A17'; GRAY='#59656F'; LIGHT='#EBF2F5'; GREEN='#437B76'; RED='#9A4450'
PALETTE=[GRAY,TEAL,PURPLE,NAVY]
m=mpl.rcParams
m.update({'font.family':'sans-serif','font.sans-serif':['Arial','Arimo','Liberation Sans'], 'font.size':10.3,'axes.titlesize':11,'axes.labelsize':10.3,
          'xtick.labelsize':10,'ytick.labelsize':10,'legend.fontsize':10,'axes.spines.right':False,'axes.spines.top':False,
          'axes.linewidth':0.8,'lines.linewidth':1.7,'lines.markersize':5,'svg.fonttype':'none','pdf.fonttype':42,'savefig.dpi':600})
def df(file):return pd.read_csv(OUT/file)
def finish(fig, stem):
    fig.patch.set_facecolor('white');save_figure(fig,FIG,stem)
def styl(ax,grid='x'):
    ax.grid(axis=grid,color='#D8E1E5',alpha=.7,linewidth=.65);ax.set_axisbelow(True)
def panel(ax, letter, title):
    ax.set_title(f'{letter}  {title}',loc='left',weight='bold',color=NAVY,pad=9)
def short_arm(x):
    if 'Usual' in x:return 'Usual care'
    if 'Screen' in x:return 'Screen'
    if 'human safety' in x:return 'Robot + gate'
    if 'Embodied' in x:return 'Robot'
    if 'Manual' in x:return 'Manual'
    return x

def draw_architecture():
    fig,ax=plt.subplots(figsize=(6.8,3.65));ax.set_xlim(0,10);ax.set_ylim(0,6);ax.axis('off')
    def box(x,y,w,h,title,detail,fc,ec):
        ax.add_patch(patches.FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.10,rounding_size=.12',lw=1.3,ec=ec,fc=fc))
        ax.text(x+w/2,y+h-.35,title,weight='bold',color=ec,ha='center',va='center',fontsize=10.8)
        ax.text(x+w/2,y+h/2-.24,detail,ha='center',va='center',fontsize=10,linespacing=1.4)
    box(.16,1.95,2.32,2.63,'Four pathways','Usual / manual\nMatched screen\nRobot\nRobot + gate',LIGHT,TEAL)
    box(3.10,3.55,3.45,1.72,'Patient model','12-week monitoring\nSymptoms · retention · alerts','#EEF1F8',PURPLE)
    box(3.10,1.34,3.45,1.72,'Clinic intake model','35 observed workdays\nQueues · access · workload','#E8F3F2',TEAL)
    box(7.53,1.95,2.27,2.63,'Dual-gate test','Patient benefit\nAND\nacceptable access\nand work','#F8F3E9',ORANGE)
    for y1,y2 in [(3.66,4.3),(2.86,2.2)]:
        ax.annotate('',xy=(2.99,y2),xytext=(2.60,y1),arrowprops=dict(arrowstyle='-|>',lw=1.6,color=GRAY))
    for y1,y2 in [(4.24,3.66),(2.19,2.83)]:
        ax.annotate('',xy=(7.40,y2),xytext=(6.66,y1),arrowprops=dict(arrowstyle='-|>',lw=1.6,color=GRAY))
    ax.text(5,5.72,'Complementary care evaluation architecture',ha='center',fontsize=11.5,weight='bold',color=NAVY)
    ax.text(5,.95,'Independent models · shared pathway definitions',ha='center',fontsize=10,color=GRAY,style='italic')
    ax.text(5,.43,'Calibration priorities: engagement · clinician workload · intake demand',ha='center',color=GRAY,fontsize=10)
    finish(fig,'Figure_1_model_architecture')

def draw_patient():
    w=df('individual_weekly_bootstrap_summary.csv'); a=df('individual_arm_replication_summary.csv'); c=df('individual_contrast_summary.csv')
    fig,axs=plt.subplots(2,2,figsize=(6.8,5.65),gridspec_kw={'height_ratios':[1,1]},layout='constrained')
    ax=axs[0,0];panel(ax,'a','12-week symptom trajectories')
    for idx,(arm,g) in enumerate(w.groupby('arm',sort=False)):
        color=PALETTE[idx]; g=g.sort_values('week');ax.plot(g.week,g.mean_phq9_locf_mean,label=short_arm(arm),color=color,marker=['o','s','^','D'][idx],markersize=3,markevery=3)
        ax.fill_between(g.week,g.mean_phq9_locf_ci_low,g.mean_phq9_locf_ci_high,color=color,alpha=.13)
    ax.set_xlabel('Week');ax.set_ylabel('PHQ-9');ax.set_xticks([0,3,6,9,12]);ax.legend(fontsize=10,loc='lower left',ncol=1,frameon=False);styl(ax,'y')
    ax=axs[0,1];panel(ax,'b','Patient outcomes by pathway')
    endpoints=['response_percent','remission_percent','completion_percent']; elabs=['Response','Remission','Completion']
    for j,metric in enumerate(endpoints):
        for i,(arm,r) in enumerate(a.iterrows()):
            y=j+(i-1.5)*.16;mean=r[f'{metric}_mean'];low=r[f'{metric}_ci_low'];high=r[f'{metric}_ci_high']
            ax.errorbar(mean,y,xerr=[[mean-low],[high-mean]],color=PALETTE[i],marker=['o','s','^','D'][i],capsize=2.1,ls='none',markersize=4)
    ax.set_yticks(range(3),elabs);ax.invert_yaxis();ax.set_xlabel('Participants (%)');ax.set_xlim(0,82);styl(ax)
    ax=axs[1,0];panel(ax,'c','Paired patient contrasts')
    gated='Embodied robot + human safety gate'; metrics=['response_percent','remission_percent','completion_percent']; labels=['Response','Remission','Completion']
    for i,(metric,lab) in enumerate(zip(metrics,labels)):
        row=c[(c.comparator==gated)&(c.metric==metric)].iloc[0];v=row.mean_difference
        ax.errorbar(v,i,xerr=[[v-row.bootstrap_ci_low],[row.bootstrap_ci_high-v]],fmt='o',markersize=5,color=TEAL if v>0 else PURPLE,capsize=3)
    ax.axvline(0,color=GRAY,ls='--',lw=1);ax.set_yticks(range(3),labels);ax.invert_yaxis();ax.set_xlabel('Robot + gate minus screen (pp)');ax.set_xlim(-7,9);styl(ax)
    ax=axs[1,1];panel(ax,'d','Safety and oversight contrasts');ax.axis('off')
    rows=[('Review', 'mean_clinician_review_minutes','min / participant'),('Near-misses','physical_near_misses_per_100','per 100 participants'),('Missed risk weeks','missed_crises_per_100_crisis_weeks','per 100 risk weeks')]
    for j,(lab,metric,unit) in enumerate(rows):
        r=c[(c.comparator==gated)&(c.metric==metric)].iloc[0]
        y=.8-j*.32
        ax.text(.02,y,lab,transform=ax.transAxes,weight='bold',color=NAVY,fontsize=10,va='center')
        ax.text(.98,y,f'{r.mean_difference:+.2f}\n({r.bootstrap_ci_low:+.2f} to {r.bootstrap_ci_high:+.2f})\n{unit}',transform=ax.transAxes,color=PURPLE if r.mean_difference>0 else TEAL,ha='right',va='center',fontsize=10)
        if j<2:ax.plot([.02,.98],[y-.16,y-.16],color='#D8E1E5',transform=ax.transAxes)
    finish(fig,'Figure_2_patient_results')

def draw_service():
    s=df('system_replication_results.csv'); a=df('system_scenario_summary.csv'); c=df('system_contrast_summary.csv');fig,axs=plt.subplots(2,2,figsize=(6.8,5.7),layout='constrained')
    order=['Manual intake','Screen kiosk + clinician review','Embodied robot (realistic faults)','Embodied robot + human safety gate']
    ax=axs[0,0];panel(ax,'a','Working-time wait distribution')
    data=[s[s.scenario==k].mean_wait_minutes.to_numpy() for k in order]
    b=ax.boxplot(data,vert=True,showfliers=False,patch_artist=True,positions=np.arange(1,5),widths=.5)
    for p,col in zip(b['boxes'],PALETTE):p.set_facecolor(col);p.set_alpha(.22);p.set_edgecolor(col)
    for i,v in enumerate(data):ax.scatter(np.repeat(i+1,len(v))+np.random.default_rng(192+i).uniform(-.16,.16,size=len(v)),v,s=2,color=PALETTE[i],alpha=.15,rasterized=False)
    ax.set_xticks(range(1,5),['Manual','Screen','Robot','Robot +\ngate']);ax.set_ylabel('Mean wait (work min)');styl(ax,'y')
    ax=axs[0,1];panel(ax,'b','Mean waiting time')
    for i,name in enumerate(order):
        r=a[a.scenario==name].iloc[0];v=r.mean_wait_minutes_mean;l=r.mean_wait_minutes_ci_low;h=r.mean_wait_minutes_ci_high
        ax.errorbar(v,i,xerr=[[v-l],[h-v]],marker='o',color=PALETTE[i],ls='none',capsize=3,markersize=5)
    ax.set_yticks(range(4),['Manual','Screen','Robot','Robot + gate']);ax.invert_yaxis();ax.set_xlabel('Working minutes');styl(ax)
    ax=axs[1,0];panel(ax,'c','Paired safety contrasts')
    gated='Embodied robot + human safety gate'; metrics=['missed_high_acuity_percent','false_alerts_per_100_arrivals','abandonment_percent']
    labels=['Missed high acuity (pp)','False alerts (/100)','Abandonment (pp)']
    for j,(metric,lab) in enumerate(zip(metrics,labels)):
        r=c[(c.comparator==gated)&(c.metric==metric)].iloc[0]
        ax.errorbar(r.mean_difference,j,xerr=[[r.mean_difference-r.bootstrap_ci_low],[r.bootstrap_ci_high-r.mean_difference]],color=TEAL if r.mean_difference<0 else ORANGE,marker='o',capsize=3)
    ax.axvline(0,color=GRAY,ls='--');ax.set_yticks(range(3),labels);ax.invert_yaxis();ax.set_xlabel('Robot + gate minus screen\n(native units, see labels)');ax.set_xlim(-13,6);styl(ax)
    ax=axs[1,1];panel(ax,'d','Throughput across pathways')
    for i,name in enumerate(order):
        r=a[a.scenario==name].iloc[0];v=r.throughput_per_day_mean;l=r.throughput_per_day_ci_low;h=r.throughput_per_day_ci_high
        ax.errorbar(v,i,xerr=[[v-l],[h-v]],marker='D',color=PALETTE[i],ls='none',capsize=3,markersize=5)
    ax.set_yticks(range(4),['Manual','Screen','Robot','Robot + gate']);ax.invert_yaxis();ax.set_xlabel('Completed assessments / day');ax.set_xlim(32,36);styl(ax)
    finish(fig,'Figure_3_service_results')

def heat(ax,d,x,y,z,xlab,ylab):
    xp=np.sort(d[x].unique());yp=np.sort(d[y].unique());mat=d.pivot(index=y,columns=x,values=z).reindex(index=yp,columns=xp).values
    im=ax.pcolormesh(np.arange(len(xp)+1)-.5, np.arange(len(yp)+1)-.5, mat, cmap='cividis', shading='flat', rasterized=False)
    ax.set_xlim(-.5,len(xp)-.5);ax.set_ylim(-.5,len(yp)-.5)
    idx=np.arange(0,len(xp),2) if len(xp)>7 else np.arange(len(xp))
    ax.set_xticks(idx,[f'{xp[k]:g}' for k in idx],fontsize=10);ax.set_yticks(range(len(yp)),[f'{p:.0%}' for p in yp],fontsize=10)
    ax.set_xlabel(xlab);ax.set_ylabel(ylab)
    return im

def draw_robustness():
    ass=df('assumption_stress_tests/neutral_skeptical_contrast_summary.csv');igs=df('individual_sensitivity_grid.csv');ss=df('system_sensitivity_grid.csv')
    nested=df('diagnostics/individual_parameter_uncertainty_nested.csv')
    fig,axs=plt.subplots(2,2,figsize=(6.8,6.5),layout='constrained')
    ax=axs[0,0];panel(ax,'a','Neutral and skeptical stress tests')
    for i,name in enumerate(['neutral','skeptical']):
        for j,(metric,label) in enumerate([('response_percent','Response'),('completion_percent','Completion')]):
            row=ass[(ass.scenario.str.contains(name))&(ass.metric==metric)].iloc[0];y= i*2+j
            v=row.mean_difference
            ax.errorbar(v,y,xerr=[[v-row.bootstrap_ci_low],[row.bootstrap_ci_high-v]],color=TEAL if metric=='response_percent' else PURPLE,marker='o',capsize=3)
    ax.set_yticks(range(4),['Neutral · response','Neutral · completion','Skeptical · response','Skeptical · completion']);ax.invert_yaxis();ax.axvline(0,color=GRAY,ls='--');ax.set_xlabel('Robot + gate minus screen (pp)');styl(ax)
    ax=axs[0,1];panel(ax,'b','Patient response breakpoints')
    im=heat(ax,igs,'engagement_logit_advantage','robot_downtime','response_difference_percentage_points','Engagement logit advantage','Session downtime');cb=fig.colorbar(im,ax=ax,fraction=.05,pad=.03,label='Response difference (pp)');cb.solids.set_rasterized(False)
    ax=axs[1,0];panel(ax,'c','Service waiting breakpoints')
    im=heat(ax,ss,'clinician_review_minutes','robot_downtime','wait_difference_vs_screen_minutes','Review time (min)','Day-level downtime');cb=fig.colorbar(im,ax=ax,fraction=.05,pad=.03,label='Wait difference (min)');cb.solids.set_rasterized(False)
    ax=axs[1,1];panel(ax,'d','Nested parameter ensemble')
    cols=list(nested.columns)
    rx=next((x for x in cols if 'response' in x and 'difference' in x),None)
    cy=next((x for x in cols if 'completion' in x and 'difference' in x),None)
    if rx and cy:
        ax.scatter(nested[rx],nested[cy],s=10,alpha=.28,color=TEAL,edgecolors='none');ax.axvline(0,color=GRAY,ls='--');ax.axhline(0,color=GRAY,ls='--');ax.set_xlabel('Response difference (pp)');ax.set_ylabel('Completion difference (pp)');styl(ax,'both')
    else:
        ax.axis('off');ax.text(.1,.5,'Scenario matrix retained\nin supplementary data',transform=ax.transAxes,color=NAVY)
    finish(fig,'Figure_4_robustness')

def draw_sobol():
    f=OUT/'global_sensitivity'/'sobol_first_total_indices.csv'; g=OUT/'global_sensitivity'/'sobol_second_order_indices.csv'
    main=pd.read_csv(f); second=pd.read_csv(g)
    fig,axs=plt.subplots(2,2,figsize=(6.8,6.85),layout='constrained')
    cases=[('individual','response_difference_pp','Patient response'),('individual','completion_difference_pp','Patient completion'),('service','mean_wait_difference_minutes','Service waiting')]
    for idx,(model,out,label) in enumerate(cases):
        ax=axs.flat[idx];panel(ax,'abc'[idx],f'Total-order: {label}')
        sub=main[(main.model==model)&(main.outcome==out)].nlargest(5,'ST').sort_values('ST')
        y=np.arange(len(sub));x=sub.ST.to_numpy();lo=sub.ST_low.to_numpy();hi=sub.ST_high.to_numpy()
        ax.errorbar(x,y,xerr=np.vstack([np.maximum(0,x-lo),np.maximum(0,hi-x)]),fmt='o',color=TEAL if idx<2 else PURPLE,capsize=3)
        ax.set_yticks(y,sub.parameter_label.str.replace(' probability','',regex=False).str.replace('Embodiment ','',regex=False).str.replace('symptom increment','symptom gain',regex=False).str.replace('dropout increment','dropout',regex=False),fontsize=10)
        ax.set_xlabel('Total-order index (ST)');ax.set_xlim(min(-.07,lo.min()-.04),max(.75,hi.max()+.05));ax.axvline(0,color=GRAY,ls='--');styl(ax)
    ax=axs.flat[3];panel(ax,'d','Exploratory pairwise interactions')
    sub=second[(second.model=='service')&(second.outcome=='mean_wait_difference_minutes')].copy()
    sub['strength']=sub.S2.abs()
    sub=sub.nlargest(5,'strength').sort_values('S2')
    yl=[f'{r.parameter_1_label}\n× {r.parameter_2_label}' for r in sub.itertuples()]
    y=np.arange(len(sub));v=sub.S2.to_numpy();l=sub.S2_low.to_numpy();h=sub.S2_high.to_numpy()
    ax.errorbar(v,y,xerr=np.vstack([np.maximum(0,v-l),np.maximum(0,h-v)]),fmt='o',color=ORANGE,capsize=3)
    ax.set_yticks(y,yl,fontsize=10);ax.axvline(0,color=GRAY,ls='--');ax.set_xlabel('Second-order index (S2)');styl(ax)
    finish(fig,'Figure_5_global_sensitivity')

def draw_diagnostics():
    est=df('diagnostics/individual_estimand_sensitivity_summary.csv');cap=df('diagnostics/service_capacity_sensitivity_summary.csv')
    abl=df('diagnostics/patient_pathway_bundle_ablation_summary.csv');w=df('system_warmup_diagnostic.csv')
    fig,axs=plt.subplots(2,2,figsize=(6.8,6.6),layout='constrained')
    ax=axs[0,0];panel(ax,'a','Response estimands')
    for i,m in enumerate(['response_locf_percent','response_bocf_percent','response_completers_percent']):
        r=est[est.metric==m].iloc[0];v=r.robot_minus_screen_mean
        ax.errorbar(v,i,xerr=[[v-r.bootstrap_ci_low],[r.bootstrap_ci_high-v]],fmt='o',capsize=3,color=TEAL)
    ax.set_yticks(range(3),['LOCF','BOCF','Completers']);ax.invert_yaxis();ax.axvline(0,color=GRAY,ls='--');ax.set_xlabel('Robot + gate minus screen (pp)');styl(ax)
    ax=axs[0,1];panel(ax,'b','Intake station sensitivity')
    d=cap[cap.metric=='mean_wait_difference_minutes'].sort_values('robot_intake_servers')
    ax.errorbar(d.robot_intake_servers,d.robot_minus_screen_mean,yerr=np.vstack([d.robot_minus_screen_mean-d.bootstrap_ci_low,d.bootstrap_ci_high-d.robot_minus_screen_mean]),marker='o',capsize=3,color=PURPLE)
    ax.axhline(0,color=GRAY,ls='--');ax.set_xticks(d.robot_intake_servers);ax.set_xlabel('Embodied intake stations');ax.set_ylabel('Wait difference (min)');styl(ax,'y')
    ax=axs[1,0];panel(ax,'c','Pathway component diagnostics')
    d=abl[abl.metric=='response_difference_percentage_points'].copy();d=d[~d.parameter_block.str.contains('Full',case=False)];d=d.sort_values('mean_difference_vs_screen').tail(5)
    ax.errorbar(d.mean_difference_vs_screen,np.arange(len(d)),xerr=np.vstack([d.mean_difference_vs_screen-d.bootstrap_ci_low,d.bootstrap_ci_high-d.mean_difference_vs_screen]),color=TEAL,marker='o',capsize=3,ls='none')
    ax.set_yticks(range(len(d)),d.parameter_block.str.replace(' only','',regex=False),fontsize=10);ax.axvline(0,color=GRAY,ls='--');ax.set_xlabel('Response difference (pp)');styl(ax)
    ax=axs[1,1];panel(ax,'d','Queue warm-up sensitivity')
    for i,(scenario,dat) in enumerate(w.groupby('scenario')):
        dat=dat.sort_values('warmup_days'); # summary data columns
        mn=dat.mean_wait_mean if 'mean_wait_mean' in dat else dat[[c for c in dat if 'mean_wait' in c and 'mean' in c][0]]
        ax.plot(dat.warmup_days,mn,marker='o',label=short_arm(scenario),color=[TEAL,PURPLE][i%2])
    ax.set_xticks([0,2,5,10]);ax.set_xlabel('Warm-up (days)');ax.set_ylabel('Mean wait (work min)');ax.legend(frameon=False,fontsize=10);styl(ax,'y')
    finish(fig,'Figure_6_diagnostics')

if __name__=='__main__':
    draw_architecture();draw_patient();draw_service();draw_robustness();draw_sobol();draw_diagnostics(); print('Figures complete',list((FIG/'svg').glob('*.svg')))
