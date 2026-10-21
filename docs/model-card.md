# Model card — PredictRx Sentinel (V1)

## Model details

| Field | Value |
|---|---|
| Name | PredictRx Sentinel sepsis early-warning |
| Version | `v0.2.0-202609281906` (frozen 2026-09-28 20:09 UTC) |
| Model sha256 | `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d` |
| Type | LightGBM (7 leaves, 673 features) + isotonic calibration fitted on validation |
| Model disagreement | Spread of a rejected 5-member patient-bootstrap LightGBM ensemble, display only; not a confidence interval and not used by TrustGate |
| Target | Official Challenge-compatible `SepsisLabel`; positive from six hours before defined onset onward, not a pure incident six-hour hazard |
| Input | Hourly vitals/labs/demographics → rolling windows, deltas, patient-baseline deviation, measurement frequency, missingness, SOFA-lite / qSOFA-lite / SIRS |
| Output | Calibrated Challenge-label score, risk band, model disagreement, TrustGate reliability state, grouped TreeSHAP factors |
| CPU latency | ≈ 5 ms per prediction |

## Intended use

Research / demo decision support for adult ICU sepsis risk scoring.  
**Not** approved for clinical use.

## Out-of-scope uses

- Diagnosis or treatment recommendation  
- Autonomous alerting to patients  
- Pediatric / neonatal / non-ICU use  
- Claims of Bangladesh clinical validity without local validation  

## Training data

PhysioNet Challenge 2019 Dataset A (see data card). Dataset B was untouched until the model was frozen and was scored exactly once.

## Risk bands

| Band | Threshold | How it was chosen (validation patients only) |
|---|---|---|
| Insufficient data | < 4 h observed | No score shown |
| Watch | ≥ 2.36% | Lower of the utility-optimal threshold and the threshold flagging 85% of septic patients before onset |
| High risk | ≥ 8.36% | Best utility with hour-level specificity ≥ 0.95; it interrupts only after TrustGate passes freshness and perturbation-stability checks |

## Evaluation

Internal test = 15% of Dataset A patients held out by patient (3,051 patients, 285 septic).  
Dataset B = public Challenge training set B from a geographically distinct
hospital system, 19,978 adult patients and 1,140 septic patients. It supports
the wording: **Site-held-out retrospective validation on a geographically
distinct public hospital cohort.** It is not the Challenge's secret Hospital C
and is not prospective clinical validation.

### Ranking and calibration

| Metric | Internal validation | Internal test | **Dataset B** |
|---|---|---|---|
| AUROC | 0.829 | 0.821 | **0.808** |
| AUPRC | 0.108 | 0.109 | **0.079** |
| Positive-hour prevalence | 2.05% | 2.41% | 1.43% |
| AUPRC ÷ prevalence | 5.3× | 4.5× | **5.5×** |
| Brier | 0.019 | 0.022 | 0.014 |
| ECE (equal-mass bins) | 0.0006 | 0.0038 | **0.0032** |
| Calibration slope / intercept | 1.00 / — | 0.94 / — | **0.80 / −0.78** |
| Brier skill vs constant prevalence | 0.054 | — | 0.030 |

Dataset B patient-level bootstrap 95% intervals (500 replicates): AUROC
0.797–0.820, AUPRC 0.071–0.090, high-risk utility 0.213–0.263.

AUPRC falls on Dataset B alongside lower positive-hour prevalence. The
AUPRC/prevalence ratio is descriptive and does not establish equivalent
clinical performance. Low ECE hides miscalibration here: a slope of 0.80 means
Dataset B scores are too spread out (overconfident at both ends), so thresholds
and calibration must be re-fitted locally before any use.

### High-risk band (alerting)

| Metric | Internal test | **Dataset B** |
|---|---|---|
| PhysioNet normalized utility | 0.244 | **0.238** |
| Hour-level sensitivity | 0.292 | 0.314 |
| Hour-level specificity | 0.955 | 0.957 |
| Septic patients alerted before onset | 42.5% | 35.7% |
| …alerted 0–12 h before onset | 13.0% | 7.7% |
| Alert precision (alert events followed by sepsis) | 16.9% | 13.2% |
| False alerts / 100 patient-hours | 0.36 | 0.19 |

### Watch band (screening)

| Metric | Internal test | **Dataset B** |
|---|---|---|
| Normalized utility | 0.432 | 0.283 |
| Septic patients flagged before onset | 92.3% | 80.3% |
| Hour-level specificity | 0.735 | 0.839 |
| False alerts / 100 patient-hours | 2.76 | 2.05 |

The Watch band transfers worse than the High-risk band: it catches fewer
septic patients before onset on Dataset B. Historical threshold metrics below
predate TrustGate.

### TrustGate at controlled sensitivity (Dataset A validation, 3,050 patients)

TrustGate halves alert-hours (6,097 to 3,129) and lowers false alerts from 0.39
to 0.19 per 100 patient-hours, but it also lowers sensitivity from 0.34 to 0.20.
The fair comparison is a raw threshold raised to the same sensitivity, which
gives 0.23 false alerts per 100 patient-hours. The paired difference, TrustGate
minus raw, is −0.091 to +0.004 per 100 patient-hours. The interval crosses
zero, so **a reliability benefit is not established**. TrustGate is presented
as a data-quality and safety layer; no percentage false-alert reduction is
claimed. Evidence: `ml/artifacts/experiments/TRUSTGATE-COHORT-01/`.

## Baselines (internal test, utility-optimal threshold)

| Model | AUROC | AUPRC | Utility |
|---|---|---|---|
| Clinical rule score | 0.600 | 0.034 | 0.085 |
| Logistic regression | 0.771 | 0.085 | 0.350 |
| **LightGBM (this model)** | **0.821** | **0.109** | **0.422** |

### Preregistered baseline comparison on Dataset B (run once, 2026-09-29)

Each model uses its own Dataset A-validation-selected high-risk threshold.
The release rule was fixed in `ml/configs/baselines_setb.yaml` before scoring.

| Model | AUROC | AUPRC | High-risk utility |
|---|---|---|---|
| Clinical rule score | 0.657 | 0.028 | 0.053 |
| Logistic regression | 0.714 | 0.047 | 0.124 |
| **LightGBM Run 4 (frozen)** | **0.808** | **0.079** | **0.238** |

Patient-level paired bootstrap (Run 4 minus comparator, 95% CI):

- vs clinical rule: AUPRC +0.043 to +0.062; utility +0.159 to +0.212
- vs logistic: AUPRC +0.025 to +0.040; utility +0.094 to +0.135

**Release rule passed.** Run 4 re-scored within 3e-7 of its historical
Dataset B metrics (parity check), confirming the rebuilt features are
equivalent. Evidence: `ml/artifacts/experiments/baselines_setb_20260929T205614Z/`.

### Challenger search (TABULAR-AONLY-01) — rejected

A preregistered 36-trial search on Dataset A only (24 LightGBM, 6 CatBoost,
6 feature-family ablations; 5 patient-grouped folds) selected a LightGBM
configuration. On the locked Dataset A internal test it lost to Run 4:
challenger minus Run 4 AUROC −0.033 to −0.010, AUPRC −0.046 to −0.014, utility
−0.087 to −0.015 (paired bootstrap), with about twice the false-alert rate. It
was rejected and never scored on Dataset B. Run 4's internal-test estimate is
mildly optimistic (consulted across four runs), which slightly favours Run 4 in
this comparison; the decision is unchanged under the preregistered rule.

### What drives the signal (Dataset A ablations, cross-validated utility)

| Feature family | Utility | AUPRC |
|---|---|---|
| All features | 0.413 | 0.091 |
| Care-process only (missingness, measurement frequency) | 0.367 | 0.080 |
| Physiology + trends | 0.258 | 0.054 |
| Current physiology only | 0.205 | 0.049 |
| Vitals only | 0.165 | 0.045 |
| Clinical scores only (SOFA-lite / SIRS) | 0.084 | 0.036 |

Most of the predictive signal comes from *how clinicians measure* rather than
the measured values. This is a known property of PhysioNet 2019 and a key
transfer risk: a hospital with different ordering habits may see a very
different model. TrustGate's data-quality states and the Readiness Passport
exist because of this.

### Low-resource fallback candidate (LOWRES-FALLBACK-01, not deployed)

This is a separately selected LightGBM that uses no laboratory values. Its 158
features cover vitals, their trends, vital measurement timing and counts, age,
sex, ICU length of stay and hospital-admission time. It scored a
cross-validated utility of 0.369 (AUROC 0.789, AUPRC 0.085), against 0.413 for
the lab-including search winner. On validation, which is in-sample for its own
calibration, the high-risk band gives specificity 0.955, sensitivity 0.278 and
0.74 false alerts per 100 patient-hours. Much of its signal is measurement
timing, so it needs local validation before any low-resource use.

On the locked internal test (descriptive only), it scored AUROC 0.770 and
high-risk utility 0.170, against 0.821 and 0.244 for Run 4.

### Temporal / Graph-Hazard challenger (GRAPH-HAZARD-01) — rejected

Seven temporal models were compared on the same folds as the tabular search:
GRU-D, TCN, a sparse encoder, and Graph-Hazard with organ graph, multi-horizon
hazard, reconstruction and sampling invariance added step by step. None beat
the tree on cross-validated utility (best: TCN 0.387 against 0.413), although
the TCN had higher AUPRC (0.108 against 0.091). The Graph-Hazard additions did
not improve on the plain encoder. A blend of Run 4 and the TCN was the
preselected challenger. On the locked internal test it raised AUPRC from 0.109
to 0.117 (paired +0.000 to +0.016) with the same AUROC, but high-risk utility
was 0.243 against 0.244 (paired −0.011 to +0.008). It failed the preregistered
utility check and was rejected; Run 4 remains the model.

### Residual-Hazard development experiment (RESIDUAL-HAZARD-01)

This experiment used Dataset A train+validation only; it did not access the
closed internal test or Dataset B. Against a freshly trained 7-leaf reference,
healthy-reference next-hour residual features increased five-fold
cross-validated utility from 0.3986 to 0.4073, AUROC from 0.8156 to 0.8174 and
AUPRC from 0.0880 to 0.0895. It passed the preregistered development gate.

The full additive stack did not pass. The nested 1/3/6/12-hour hazard synthesis
raised AUPRC to 0.0930 but reduced utility to 0.3991, so it was rejected. An
EMA alert policy passed its separate development policy gate versus a
separately tuned raw policy (mean utility difference +0.0403; false-alert
difference -0.0358 per 100 patient-hours). These are development-only results,
not evidence that the frozen Run 4 model or deployed alerting has improved.
The selected healthy-residual + EMA candidate was final-fit and frozen, then
compared once with Run 4 on Dataset B. It scored AUROC 0.790, AUPRC 0.064 and
high-risk utility 0.109, against Run 4's 0.808, 0.079 and 0.238. All five
preregistered checks failed, so the candidate was rejected. Run 4 remains the
primary model.

## Subgroups (High-risk band sensitivity)

| Group | Internal test | Dataset B |
|---|---|---|
| Female / male | 0.266 / 0.333 | 0.352 / 0.326 |
| Age 18–44 / 45–64 / 65–79 / 80+ | 0.376 / 0.308 / 0.260 / 0.343 | 0.316 / 0.330 / 0.381 / 0.258 |
| MICU / SICU / unknown | 0.250 / 0.329 / 0.343 | 0.264 / 0.384 / 0.360 |
| Missingness low / medium / high | — | 0.371 / 0.281 / 0.295 |

Gaps above 10 percentage points (disclosed):

- Internal test: age 18–44 vs 65–79 (11.6 pp).
- Dataset B: age 65–79 vs 80+ (12.3 pp); SICU vs MICU (12.0 pp).

The weakest age group differs between the two datasets, so these gaps partly reflect small septic counts per group. Patients aged 80+ and medical-ICU patients on Dataset B are the groups to watch in any pilot.

## Main drivers (global SHAP, internal test)

FiO2 hours-since-measured, ICU length of stay, 6 h max temperature, hours observed, lactate hours-since-measured, 24 h min respiratory rate, unit type, SOFA-lite 24 h rise, hospital-admission time, calcium variability, 12 h min SBP, 24 h max haematocrit.

Several top drivers describe *how often* clinicians measure rather than physiology. These patterns are hospital-specific; they carried over to Dataset B reasonably well, but they must be re-checked at any new site.

## Limitations

- SOFA-lite omits GCS (neurological) and vasopressor dose (cardiovascular uses MAP < 70 only), so it underestimates true SOFA.  
- Labels are the PhysioNet research definition of sepsis onset, not bedside diagnoses.  
- Watch-band sensitivity dropped on Dataset B; thresholds must be recalibrated locally.  
- The internal test set was consulted across four training runs; its estimate is mildly optimistic. Dataset B is the primary performance estimate for this frozen version, but it is public set B rather than blind Hospital C.  
- US ICU data only.
- Ordinary row-level metrics include post-onset/easier positive hours because the label remains positive after onset.
- Calibration slope on Dataset B is 0.80; scores need local recalibration.
- Predictive signal relies heavily on care-process (measurement-pattern) features; see the ablation table.

## Ethical considerations

- Human acknowledgement required for alerts; dismissals require a reason and are audited  
- Subgroup reports by sex, age, ICU type, missingness  
- Sensitivity gaps > 10 pp disclosed above  
- Domain-shift disclaimer always visible  

## Caveats

US ICU data; calibration and thresholds must be re-checked on local data and run silently before any pilot raises live alerts.

The automated readiness passport currently recommends **Retrospective
validation**. This model is not validated for Bangladesh and has no prospective
outcome-improvement evidence.

## Local monitoring during a silent pilot

The pilot cockpit measures this frozen model at a site without changing it.
Local sensitivity, lead time, calibration, alert burden, subgroup slices and
missingness are computed from shadow alerts and chart-review adjudications;
threshold simulation is read-only analysis. Any recalibration or new
threshold would be a new model version with its own evaluation and model card.
Site results are local evidence only and are not added to the PhysioNet
figures above.
