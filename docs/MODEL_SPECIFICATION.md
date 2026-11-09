# Mathematical and operational model specification

## Status and scope

The models are transparent, assumption-driven stress tests. They are not fitted digital twins, causal estimators, clinical prediction models, or validated safety models. All parameters, units, pathway values, ranges, rationales, and calibration status are listed in `config/individual_parameter_dictionary.csv` and `config/service_parameter_dictionary.csv`.

## 1. Individual microsimulation

### 1.1 Indices and state

Participant `i = 1,...,N`, pathway `a`, and week `t = 1,...,12`. The state comprises PHQ-9 `Y_iat`, active status `Z_iat`, previous engagement `E_ia,t-1`, trust `U_iat`, cumulative alerts, crisis weeks, review minutes, downtime, fallback, and physical near-misses. Baseline covariates are shared across pathways in paired replications.

### 1.2 Baseline draws

- `Y_i0 = clip(Normal(15.5, 3.2), 10, 24)`.
- Technology acceptance `A_i ~ Beta(2.4,1.9)`.
- Privacy concern `P_i ~ Beta(2.1,2.4)`.
- Social support `S_i ~ Normal(0,1)`.
- Treatment responsiveness `R_i ~ Normal(0,0.13)` PHQ-9 points/week.
- Initial trust: `U_ia0 = 0.08 H_a + 0.12 A_i - 0.10 P_i`, where `H_a` is the human-verification indicator.
- Initial refusal: `F_ia ~ Bernoulli(rho_a)`; active status is `Z_ia0 = 1-F_ia`.

### 1.3 Availability and fallback

For active participants, downtime `D_iat ~ Bernoulli(d_a)`. Conditional on downtime, screen fallback `B_iat ~ Bernoulli(f_a)`. Availability is `V_iat = (1-D_iat) OR B_iat`. Fallback preserves the content effect but removes the embodiment-specific symptom increment and physical near-miss exposure.

### 1.4 Engagement equation

`logit Pr(E_iat=1 | Z_i,a,t-1=1) = alpha_a + 1.05(A_i-0.5) - gamma_P,a(P_i-0.5) + 0.34 E_i,a,t-1 + 0.13 S_i + U_i,a,t-1 - delta_a(t-1) - 0.025 max(Y_i,a,t-1-15,0)`.

The realized session is engaged only if the Bernoulli engagement draw is positive and the pathway is available.

### 1.5 Symptom equation

`b_i = 0.24 + 0.022 max(Y_i0-14,0)`.

`Q_iat = E_iat [beta_content,a + beta_emb,a (1-B_iat)]`.

`Y_iat = clip(Y_i,a,t-1 - [b_i + Q_iat + R_i] + epsilon_iat, 0, 27)`, with `epsilon_iat ~ Normal(0,0.62)` for active participants. After dropout, the primary analysis uses last observation carried forward.

### 1.6 Crisis, alert, and verification equations

Let worsening `W_iat = Y_iat-Y_i,a,t-1`.

`logit Pr(C_iat=1) = -10.2 + 0.27 Y_iat + 0.42 max(W_iat,0)`.

`Pr(L_iat=1 | C_iat=1)=Se_a`; `Pr(L_iat=1 | C_iat=0)=FPR_a`.

A false alert is escalated with probability 0.12 under human verification and 0.72 without verification. Review burden is initialized at `m_audit,a` and increases by `m_alert,a` for every alert.

Trust updates are: `+0.025` after a true alert, `-0.040` after an escalated false alert, and `-0.075` after a missed crisis; trust is clipped to `[-0.5,0.5]`.

### 1.7 Physical exposure and dropout

A near-miss can occur only during an available, nonfallback embodied session: `N_iat ~ Bernoulli(h_a)`.

Weekly dropout probability is

`p_drop = clip[0.010 + 0.030(1-E_iat) + 0.016 P_i + kappa_a + 0.010 I(W_iat>1.5) - 0.008 E_iat, 0.002, 0.12]`.

New dropout is Bernoulli(`p_drop`) among active participants. Completion is active through week 12. Response is at least 50% PHQ-9 reduction; remission is PHQ-9 <=4.

### 1.8 Pairing and estimands

Within each replication, pathways share baseline covariate seeds but use independent pathway event streams. The primary estimand is the expected paired pathway difference versus the content-matched screen. Positive values favor the robot for response/remission/detection; negative values favor the robot for PHQ-9 change and missed-event measures. Burden directions are stated outcome by outcome.

## 2. Service discrete-event simulation

### 2.1 Horizon, arrivals, and acuity

A replication contains `W=5` warm-up and `D=35` observed working days, each `L=420` minutes. Daily counts are `N_d ~ Poisson(lambda)`, arrival times are ordered Uniform(0,L), and acuity is low/medium/high with probabilities 0.60/0.30/0.10. Paired pathways receive the same arrival, acuity, outage-uniform, service-normal, alert, incompleteness, and abandonment latent draws.

### 2.2 Resource scheduling

Each stage is FIFO. For a job arriving at time `a` with duration `s`, the next available server time is `v_min`, start is `max(a,v_min)`, finish is start plus `s`, and the resource's next availability becomes finish. Intake, fallback, and clinician stages have pathway-specific parallel-server counts. All resource server-availability heaps use consecutive productive working minutes. An arrival at elapsed minute 419 can wait or receive service in subsequent 420-minute blocks; unfinished work **never resets** at a day boundary. Overnight nonworking/calendar hours and scheduled end-of-shift overtime are not modeled. Thus reported wait units are **working minutes**, not wall-clock hours.

### 2.3 Intake and downtime

Day `d` is down when a shared outage uniform is below pathway downtime probability. A digital pathway uses fallback on a down day. Primary intake duration is `max(4, Normal(mu_intake,a, sigma_intake,a))`; embodied pathways add `m_reset,a`. Fallback duration is `max(4, mu_fallback,a + 4z)`. An incomplete digital assessment occurs when its shared uniform is below `q_a` and adds `m_rework,a` on the fallback resource.

### 2.4 Detection and clinician work

For high-acuity arrivals, an alert occurs with probability `Se_a`; otherwise it occurs with probability `FPR_a`. Base clinician minutes are 38/52/72 for low/medium/high acuity. Clinician duration is

`max(base_acuity - s_a, 25) + I(digital) r_a + I(alert)[6 H_a + 10(1-H_a)]`.

### 2.5 Abandonment

Predicted waiting time is the interval from arrival to the later of intake completion and the earliest clinician availability. Abandonment probability is

`p_abandon = min[0.25, logistic(-5.2 + 0.010 max(predicted_wait-120,0))]`.

Abandoned jobs do not enter clinician service. For completed jobs, final wait is clinician start minus arrival.

### 2.6 Outputs and accounting

Outputs include mean and 90th-percentile wait, throughput, abandonment, false alerts, missed high-acuity cases, failover, incomplete rework, clinician utilization and an excess daily workload-to-capacity proxy (historically named overtime), intake workload, and routine physical reset events. For every pathway/replication, `arrivals = completed + abandoned` exactly.

## 3. Uncertainty analysis

Primary simulation uncertainty uses intact replication-level paired resampling, BCa intervals, sign-flip randomization tests, Holm adjustment, paired effect sizes, and Monte Carlo standard errors. Neutral and skeptical scenarios are deterministic parameter sets, not probability distributions.

The primary global sensitivity audit assumes **independently Uniform** input ranges, not calibrated joint parameter distributions. The 1,024-base-point scrambled Sobol/Saltelli A/B/AB/BA design uses matched common-random-number streams within each design row, including nested Poisson-thinned service demand at varying arrival rates. First-order (`S1`) indices use the Saltelli covariance estimator, total-order (`ST`) indices use Jansen squared differences, and pairwise second-order (`S2`) indices use the Saltelli cross-matrix formula. Each design vector averages two stochastic evaluations (350 participants per arm for the patient model or 18 observed service days for intake), and 350 bootstrap resamples of intact design rows provide finite-design uncertainty. Raw estimates are saved without clipping/renormalization; some small S1>ST violations remain and must not be interpreted as exact population sensitivities. The independent uniform assumptions and incomplete interaction precision limit external interpretation.

## 4. Verification, calibration, and validation status

Code verification, deterministic reruns, range/impossible-event checks, shared-stream checks, flow accounting, warm-up sensitivity, and output reconciliation are implemented. Empirical calibration, external predictive validation, stakeholder elicitation, and formal face validation have not been completed. The protocol in `docs/ELICITATION_AND_VALIDATION_PROTOCOL.md` specifies the required next phase.
