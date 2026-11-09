# Model assumptions and limitations

1. All inputs are illustrative unless explicitly replaced by empirical estimates. The package contains no patient-level clinical data.
2. PHQ-9 dynamics are stylized weekly processes, not fitted disease or treatment-response models.
3. High-risk episodes and alert behavior are synthetic stress-test constructs and must not be interpreted as suicide-risk incidence, diagnosis, or validated detection performance.
4. Dropout combines refusal, privacy friction, nonengagement, symptom worsening, and embodied discomfort through simplified probabilities.
5. Physical near-misses and resets represent modeled exposure opportunities, not predicted injury rates.
6. The queue model uses a stylized working-day clock, Poisson arrivals, finite simplified resources, and stylized abandonment behavior for one intake configuration.
7. The individual and service models are conceptually aligned but not dynamically coupled. Patient engagement does not alter service arrivals, and clinic congestion does not feed back into symptoms or retention.
8. The service model omits appointment scheduling, no-shows, downstream treatment capacity, cost accounting, staff learning, maintenance logistics, equity effects, and environmental heterogeneity.
9. BCa intervals estimate uncertainty in the expected simulation output caused by finite independent replications under fixed model assumptions. They do not include empirical parameter uncertainty, structural uncertainty, clinical sampling uncertainty, or external-validity uncertainty.
10. Empirical 2.5th-97.5th percentile ranges of individual replication contrasts describe variation that a finite simulated experiment may exhibit. They are not confidence intervals for the expected mean.
11. The 250 broad parameter draws are stress-test scenarios, not samples from a fitted probability distribution. Their sign proportions and resampling-stability intervals are not posterior probabilities.
12. Paired sign-flip and t-test p-values address model-internal separation under the specified data-generating process. Large replication counts can make small model effects highly precise; statistical separation must not be equated with clinical importance.
13. Holm adjustment is applied within prespecified seven-outcome families for each comparator and model; it does not protect against all exploratory analyses in the repository.
14. Common random numbers reduce avoidable comparison noise but do not remove parameter, conceptual-model, or implementation uncertainty.
15. Threshold outcomes such as response and remission can amplify small changes near cutoff values.
16. Break-even thresholds apply only to tested grids and the modeled clinic configuration; they should not be extrapolated as universal engineering standards.
17. Similar average throughput can coexist with materially different waiting, abandonment, burden, and safety profiles.
18. The novelty assessment is targeted and non-systematic; it is not an exhaustive systematic review or priority opinion.
19. Model-internal bootstrap separation, small adjusted p-values, and large standardized effects do not establish clinical efficacy, safety, causality, cost-effectiveness, regulatory acceptability, or generalizability.
20. The screen and robot pathways are content-matched but differ in multiple implementation parameters. Their primary contrast is a bundled pathway comparison, not a causal effect of embodiment alone.
21. Last observation carried forward is the primary synthetic symptom estimand. Baseline-observation-carried-forward and completer-only analyses are reported as sensitivity analyses because differential attrition changes interpretation.
22. The service field historically named `physical_resets_per_day` counts routine reset work after non-fallback embodied intakes. It is not a stochastic incident, injury, or near-miss rate.
23. The manual service pathway is nominally at its intake-capacity boundary and is a deliberately capacity-constrained contextual benchmark rather than the primary comparator.
