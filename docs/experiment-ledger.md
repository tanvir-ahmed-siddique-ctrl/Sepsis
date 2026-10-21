# PredictRx Sentinel experiment ledger

This ledger is append-only. Negative experiments remain visible. Dataset B is
never used for feature selection, model selection, calibration, threshold
selection, architecture selection, ensemble weighting, or ablation decisions.

Machine-recorded Dataset B access lives in
`ml/artifacts/governance/evaluation_access.json`.

## Required fields

Every new entry records:

- run ID and timestamp
- objective and preregistered hypothesis
- dataset, patient-level splits, and target definition
- feature families and model family
- config, data, split, code, and artifact hashes
- code commit or an explicit `unavailable` reason
- random seed and experiment budget
- discrimination, calibration, utility, alert-burden, timing, and robustness metrics
- patient-level confidence intervals where data are available
- decision (`promote`, `retain`, `reject`, or `inconclusive`) and reason
- whether Dataset B was accessed

---

## RUN4-FROZEN — reconstructed historical entry

- **Run ID:** `v0.2.0-202609281906`
- **Status:** retained primary evidence model
- **Entry provenance:** reconstructed from surviving immutable artifacts on
  2026-09-30; this is not a claim that all historical run metadata survived
- **Objective:** improve the Dataset A validation utility of an adult-ICU sepsis
  early-warning model while retaining calibration and CPU inference
- **Hypothesis:** a strongly regularized, shallow LightGBM using causal
  handcrafted temporal features will outperform clinical-rule and logistic
  baselines on Dataset A
- **Dataset and splits:** PhysioNet Challenge 2019 Dataset A; patient-level
  train/validation/internal-test split, seed 42
- **Target:** official Challenge-compatible `SepsisLabel`; positive from six
  hours before defined onset onward; not a pure incident six-hour hazard
- **Features:** 673 numeric current-value, missingness, measurement-frequency,
  temporal, baseline-deviation, ratio, and SOFA-lite/SIRS-derived features
- **Model family:** LightGBM, 7 leaves, approximately 311 selected iterations;
  isotonic calibration on Dataset A validation
- **Config:** `ml/configs/train_lightgbm.yaml`
- **Code commit:** unavailable — this workspace was received without Git history
- **Seed:** 42
- **Frozen model SHA-256:**
  `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d`
- **Internal test:** AUROC 0.821338; AUPRC 0.109283; high-risk utility
  0.243849; utility-optimal utility 0.422436
- **Dataset B:** AUROC 0.808395; AUPRC 0.079208; prevalence 0.014285;
  Brier 0.013652; equal-mass ECE 0.003202; high-risk utility 0.237928;
  sensitivity 0.313853; specificity 0.956816; false alerts 0.192185 per
  100 patient-hours; 35.7% of septic patients flagged before onset; 7.7% in
  the desired 0–12-hour window; median warning 41 hours
- **Confidence intervals:** not produced in the historical result bundle
- **Decision:** retain
- **Reason:** respectable site-held-out discrimination and stable high-risk
  utility, but baseline-B comparisons, patient-level confidence intervals,
  calibration slope/intercept, and clinically aligned incident targets remain
  open. The internal test was consulted across four runs and is mildly
  optimistic.
- **Dataset B accessed:** yes, once for this frozen version on 2026-09-28
- **Evidence:** `ml/artifacts/models/latest/metrics.json`,
  `ml/artifacts/models/latest/eval_holdout.json`, and
  `ml/artifacts/models/run4_frozen/MANIFEST.v2.json`

## Rejected same-family ensemble

- **Run ID:** `RUN4-BOOTSTRAP-ENSEMBLE`
- **Objective:** test whether a five-member patient-bootstrap LightGBM ensemble
  improves validation utility
- **Dataset:** Dataset A only
- **Result:** single-model validation utility 0.401692; ensemble utility
  0.392444
- **Decision:** rejected
- **Reason:** lower validation utility. Do not repeat same-family averaging and
  present it as innovation.
- **Dataset B accessed:** no for this decision

## DATA-REBUILD-01 — feature matrices rebuilt from raw PSV

- **Date:** 2026-09-30
- **Objective:** replace truncated `features_setA/B.parquet` (no Parquet footer)
  without changing any historical split or model
- **Raw data:** 20,336 Dataset A and 20,000 Dataset B PSV files; a random
  300-file sample matches `ml/data/checksums/raw_sha256.txt`
- **Builder change:** streaming row-group writer to `<out>.partial` with atomic
  rename; refuses to overwrite valid files or change a recorded split map
- **Dataset A:** 790,215 rows, 677 columns; train/val/test 14,235 / 3,050 /
  3,051 patients; split map identical to Run 4
- **Dataset B:** 19,978 adult patients, 761,246 rows, 701,312 eligible rows
  (matches the preregistered count in `configs/baselines_setb.yaml`)
- **Run 4 parity on rebuilt internal test:** AUROC 0.821337, AUPRC 0.109283,
  Brier 0.022377, high-risk utility 0.243849; utility identical, ranking
  metrics within 4e-7 of the historical bundle
- **Consequence:** `baselines_setb` parity tolerance set to exact rows/patients
  and 1e-5 for continuous metrics, fixed before any new Dataset B access
- **Dataset B accessed:** structural row/patient counts only; no labels,
  scores, or metrics were computed

## TRUSTGATE-ROBUSTNESS-01 — A-only failure simulation

- **Date:** 2026-09-30
- **Model:** frozen Run 4 `v0.2.0-202609281906`, high-risk threshold 0.0836
- **Patients:** 500 locked Dataset A **validation** patients (150 septic,
  350 non-septic; seed 20260930) in `ml/configs/locked_robustness_patients.txt`.
  Validation, not internal test, so any later TrustGate policy tuning stays
  off the locked test split
- **Result:** duplicate, late-arriving, and out-of-order data produce zero
  alert flips (idempotent canonical timeline). Hour-level alert flip rate is
  1.2–3.3% for vital delays, missing labs, sparse labs, and sensor dropout.
  Removing lactate reduces baseline alerts by 11% (2,913 to 2,589) and
  positive-hour sensitivity from 0.336 to 0.307
- **Interpretation:** the frozen model partly uses lactate availability, a
  care-process signal. This motivates the `vitals_only` and
  `care_process_only` ablations; it is not evidence of clinical harm or benefit
- **Decision:** retain TrustGate Verify-data / Abstain states; no policy change
  from this run alone
- **Evidence:** `ml/artifacts/experiments/TRUSTGATE-ROBUSTNESS-01.json`
- **Dataset B accessed:** no

## TABULAR-AONLY-01 — preregistered executed budget

- **Registered:** 2026-09-30, before any trial ran
- **Config:** `ml/configs/challenger_tabular_laptop.yaml` (24 LightGBM, 6
  CatBoost, 6 feature-family ablations; 5 grouped folds on Dataset A
  train+validation only). Same search space and selection rule as
  `challenger_tabular.yaml`, except bagging is actually enabled
  (`subsample_freq: 1`) and CatBoost depth/iterations are bounded
- **Why reduced:** measured ~3 min per 5-fold LightGBM trial on a 12-thread
  laptop CPU; the full plan would take more than 10 hours
- **Selection:** mean normalized utility, then mean AUPRC; worst pseudo-site
  AUPRC reported as a safety floor
- **Next locked step:** `predict_rx.eval.compare_internal` refits the selected
  configuration on train, calibrates and thresholds on validation, and scores
  the locked internal test once
- **Dataset B accessed:** no

## DATA-TARGET-AUDIT-01 — leakage, integrity, and incident-target audit

- **Run ID:** `data_target_audit_20260929T204835Z`
- **Authorized by:** Tanvir (structural Dataset B audit only; ledger
  `setb-4a1c8a8ad790`)
- **Feature SHA-256:** A `4427d518…2cbb68`, B `1d360d48…58f732`
- **Result:** zero duplicate or non-chronological patient-hours, zero label
  reversions, zero adult-exclusion violations, zero static-field
  inconsistencies, zero A/B patient-ID overlap, no negative-shift,
  centered-window, or backfill patterns in feature code. Raw checksum manifest
  present (20,337 A / 20,001 B entries, 0 malformed). EtCO2 and all derived
  EtCO2 features are entirely empty in Dataset A
- **Incident targets written:** `data/processed/incident_targets_v1.parquet`
  (1/3/6/12 h horizons, post-onset rows censored); not yet used for training
- **Decision:** data accepted for evaluation
- **Dataset B accessed:** yes, structural counts and label integrity only; no
  model scores

## BASELINES-SETB-01 — preregistered baseline comparison

- **Run ID:** `baselines_setb_20260929T205614Z`
- **Authorized by:** Tanvir (one-time preregistered comparison)
- **Release rule (fixed before scoring):** on Dataset B, frozen Run 4 must
  exceed both baselines in AUPRC and normalized utility at each model's
  Dataset A-validation-selected high-risk threshold
- **Parity:** Run 4 re-scored on rebuilt Dataset B within 3e-7 (AUROC),
  exact rows/patients/utility — pass
- **Dataset B results:**

  | Model | AUROC | AUPRC | High-risk utility | Calibration slope |
  |---|---|---|---|---|
  | Clinical rule | 0.657 | 0.028 | 0.053 | 1.68 |
  | Logistic | 0.714 | 0.047 | 0.124 | 0.17 |
  | Run 4 | 0.808 | 0.079 | 0.238 | 0.80 |

- **Run 4 95% CI (patient bootstrap, 500):** AUROC 0.797–0.820, AUPRC
  0.071–0.090, utility 0.213–0.263
- **Paired differences (Run 4 minus comparator):** vs rule AUPRC
  +0.043…+0.062, utility +0.159…+0.212; vs logistic AUPRC +0.025…+0.040,
  utility +0.094…+0.135
- **Decision:** release rule passed; Run 4 retained as primary evidence model
- **Caveat:** calibration slope 0.80 and intercept −0.78 on Dataset B; local
  recalibration required
- **Dataset B accessed:** yes, once, recorded in the machine ledger

## TABULAR-AONLY-01 — executed result

- **Search:** 36 trials completed (24 LightGBM, 6 CatBoost, 6 ablations),
  5 patient-grouped folds on Dataset A train+validation; config SHA
  `5e1fce2a…78a6be`
- **Selected:** trial 16, LightGBM all features (23 leaves, depth 6,
  lr 0.02, colsample 0.35, lambda 5); CV utility 0.413, AUPRC 0.091, worst
  pseudo-site AUPRC 0.079. Best CatBoost (trial 28) had higher AUPRC 0.099 but
  lower utility 0.408, so it lost under the preregistered primary criterion
- **Ablations (CV utility / AUPRC):** care-process only 0.367 / 0.080;
  physiology + care-process 0.399 / 0.087; physiology temporal 0.258 / 0.054;
  physiology current 0.205 / 0.049; vitals only 0.165 / 0.045; clinical scores
  only 0.084 / 0.036
- **Locked internal test (`compare_internal_TABULAR-AONLY-01`, one score):**

  | Model | AUROC | AUPRC | High-risk utility | False alerts / 100 h |
  |---|---|---|---|---|
  | Run 4 | 0.821 | 0.109 | 0.244 | 0.36 |
  | Challenger | 0.800 | 0.082 | 0.191 | 0.73 |

  Paired bootstrap (challenger minus Run 4): AUROC −0.033…−0.010, AUPRC
  −0.046…−0.014, utility −0.087…−0.015
- **Decision:** reject. Not frozen, never scored on Dataset B
- **Interpretation:** a broader search did not beat a strongly regularized
  7-leaf model; Run 4's internal-test figure is mildly optimistic, which
  favours it slightly, but all intervals exclude zero. The ablations show the
  signal is dominated by measurement-pattern features, which is the main
  transfer risk and the motivation for TrustGate and the Readiness Passport
- **Dataset B accessed:** no

## CHALLENGER-GATE-01

- **Date:** 2026-09-30
- **Result:** passed (`ml/artifacts/governance/challenger_gate.json`) — valid
  Dataset A, baseline bundle, data audit, tabular challenger, and backend
  TrustGate tests all present
- **Meaning:** temporal or Graph-Hazard work may enter bounded Dataset A-only
  development. It must beat Run 4 on the locked internal test before any
  Dataset B request, and must use the incident targets rather than claim a
  six-hour hazard from the Challenge label

## TRUSTGATE-COHORT-01 — alert burden at controlled sensitivity

- **Date:** 2026-09-30
- **Question (master plan 7E):** does the backend TrustGate policy reduce false
  alerts more than simply raising the raw threshold to the same sensitivity?
- **Data:** all 3,050 Dataset A **validation** patients (117,419 hours,
  108,269 eligible); frozen Run 4; backend policy SHA `67cda6c3…`
- **Rule (fixed before scoring):** benefit only if, at matched sensitivity,
  TrustGate false alerts per 100 patient-hours are lower than a raw threshold
  with a paired patient-bootstrap interval excluding zero
- **Result:**

  | Policy | Alert-hours | Sensitivity | False alerts / 100 h | Alert precision | Patients flagged before onset |
  |---|---|---|---|---|---|
  | Raw threshold 0.0836 | 6,097 | 0.342 | 0.392 | 0.132 | 42.3% |
  | TrustGate alert | 3,129 | 0.196 | 0.185 | 0.211 | 28.0% |
  | Raw at matched sensitivity (0.148) | 2,182 | 0.168 | 0.228 | 0.209 | 27.6% |
  | Raw at matched alert budget (0.125) | 2,971 | 0.212 | 0.275 | 0.202 | 30.5% |

  Paired difference, TrustGate minus raw at matched sensitivity: false alerts
  −0.091…+0.004 per 100 h; sensitivity −0.006…+0.061 (500 replicates)
- **Decision:** inconclusive. The point estimates favour TrustGate, but the
  interval crosses zero, so the reliability benefit is **not established**.
  TrustGate stays a safety and data-quality layer; no "X% fewer false alerts"
  claim is made
- **Negative finding recorded:** suppressed raw alerts had a positive rate of
  0.116 against 0.147 for kept alerts; 1,951 of 6,097 raw alerts were unstable
  under missing-data perturbation. Any revised policy must be tuned on
  different data from this evaluation
- **Evidence:** `ml/artifacts/experiments/TRUSTGATE-COHORT-01/result.json`
- **Dataset B accessed:** no. **Internal test accessed:** no

## LOWRES-FALLBACK-01 — low-resource vitals-first fallback

- **Date:** 2026-09-30
- **Objective:** a model usable when routine labs are unavailable, with its
  own validation-derived thresholds rather than a silent subset of Run 4
- **Features (158):** `low_resource_vitals` family: the 8 vitals, their
  temporal summaries, their missingness / hours-since / count features, plus
  Age, Gender, ICULOS, HospAdmTime. No laboratory values
- **Search:** 10 LightGBM trials, the same 5 grouped folds and selection rule as
  TABULAR-AONLY-01 (`ml/configs/fallback_low_resource.yaml`, SHA `1d7efc03…`)
- **Selected:** trial 9 (15 leaves, min child 500, lr 0.03, colsample 0.35);
  CV AUROC 0.789, AUPRC 0.085, utility 0.369. For reference, the lab-including
  tabular winner scored 0.413 CV utility
- **Refit:** train patients (10% early stopping), isotonic calibration and
  thresholds on validation: high risk 0.1027, watch 0.0315. Validation
  (in-sample for calibration): AUROC 0.789, AUPRC 0.080, high-risk utility
  0.216, sensitivity 0.278, specificity 0.955, 0.74 false alerts per 100 h
- **Caveat:** much of this signal is vital-sign measurement timing and ICU
  length of stay, the same care-process pattern that shifted on Dataset B. It
  needs local validation before any low-resource use
- **Locked test (descriptive, inside `compare_final_GRAPH-HAZARD-01`):**
  AUROC 0.770, AUPRC 0.074, high-risk utility 0.170, specificity 0.956,
  0.77 false alerts per 100 h, 62.5% of septic patients flagged before onset.
  Below Run 4 on utility (paired −0.107…−0.040); it cannot be promoted from
  that run
- **Decision:** retain as a documented fallback candidate, not deployed
- **Evidence:** `ml/artifacts/fallback/LOWRES-FALLBACK-01/`
- **Dataset B accessed:** no

## LOCKED-TEST-REUSE-01 — authorization

- **Date:** 2026-09-30. **Authorized by:** Tanvir
- **Scope:** one additional, final score of the Dataset A internal test for a
  single preselected challenger (GRAPH-HAZARD-01 output) against frozen Run 4.
  The low-resource fallback and the temporal-only component are reported
  descriptively in the same run
- **Disclosure:** this is the second use of that split after
  TABULAR-AONLY-01, and Run 4 was developed with repeated internal-test
  consultation. Any win on this split is therefore weaker than external evidence
  and still requires the one-time Dataset B comparison

## GRAPH-HAZARD-01 — preregistered temporal / Graph-Hazard challenger

- **Registered:** 2026-09-30, before any full-ladder run
- **Config:** `ml/configs/temporal_graph_hazard.yaml`; its hash is recorded
  in `run_identity.json` and checked again at refit
- **Knowledge graph:** `knowledge/organ_graph.v1.json` (7 organ systems plus
  care-process and context nodes, 11 curated edges); structure only, not causal
- **Inputs:** hourly per-variable (value, measured-this-hour mask) for 34
  vitals and labs; carry-forward values and hours-since-measurement are
  recomputed inside the model, so augmented views stay consistent. Static: Age,
  Gender, Unit1, Unit2, HospAdmTime
- **Ablation ladder (same folds, calibration split, weights, isotonic,
  threshold rule, and metrics as TABULAR-AONLY-01):** GRU-D baseline, causal
  TCN baseline, sparse temporal encoder, + organ graph, + monotone 1/3/6/12 h
  incident-hazard head, + next-hour reconstruction, + sampling-invariance
  augmentation and consistency loss (full Graph-Hazard)
- **Tests:** a causality test for every architecture (future inputs cannot
  change earlier outputs). Incident targets match
  `incident_targets_v1.parquet` exactly
- **Disclosed pilot:** one fold-0 run of `plus_organ_graph` before the ladder.
  16k-token batches (~30 steps per epoch) underfit (utility 0.244, AUPRC
  0.061). With 3k-token batches, patience 6 and at most 30 epochs: utility 0.320,
  AUPRC 0.094, AUROC 0.762 against the tree's fold-0 values of 0.412 / 0.096 /
  0.822. Only the training schedule was changed after the pilot
- **Selection:** best mean CV utility, then AUPRC, then worst pseudo-site
  AUPRC. Fusion with the tree model (cross-fitted logistic regression on the
  logits) becomes the final challenger only if its CV utility gain is at least
  0.005 over the best temporal model
- **Refit (`predict_rx.temporal.final`):** train patients (10% early
  stopping), isotonic calibration and thresholds on validation. The fusion
  blend with frozen Run 4 is fit on validation
- **Locked-test rule (`predict_rx.eval.compare_final`, fixed now):** advance
  to a Dataset B request only if a paired 95% lower bound for AUPRC or utility
  is above zero, the AUROC point drop is at most 0.01, and the utility point
  estimate is not worse than Run 4's. Otherwise reject, and Run 4 stays primary
- **Status:** executed 2026-09-30 (result below)
- **Dataset B accessed:** no

## GRAPH-HAZARD-01 — executed result

- **CV ladder (5 grouped folds, Dataset A train+validation):**

  | Model | CV utility | AUPRC | AUROC | Worst pseudo-site AUPRC |
  |---|---|---|---|---|
  | Tree reference (TABULAR trial 16) | 0.413 | 0.091 | — | 0.079 |
  | GRU-D baseline | 0.363 | 0.097 | 0.793 | 0.075 |
  | **TCN baseline (selected)** | **0.387** | **0.108** | **0.801** | **0.085** |
  | Sparse temporal encoder | 0.368 | 0.104 | 0.795 | 0.065 |
  | + organ graph | 0.363 | 0.094 | 0.793 | 0.064 |
  | + multi-horizon hazard | 0.350 | 0.089 | 0.766 | 0.037 |
  | + reconstruction | 0.347 | 0.093 | 0.784 | 0.065 |
  | Full Graph-Hazard (+ invariance) | 0.353 | 0.097 | 0.781 | 0.056 |
  | Tree + TCN fusion (cross-fitted) | 0.433 | 0.126 | — | — |

- **Negative findings:** the organ graph, the hazard head, the reconstruction
  objective and the invariance objective each failed to improve CV utility over
  the plain sparse encoder, and the simplest model (TCN) ranked best. The
  multi-horizon head does learn incident onset (6 h incident AUROC about
  0.76–0.81 where it was trained), but at a small cost in Challenge-label utility
- **Fusion selected:** its CV utility gain over the TCN (+0.046) exceeded the
  preregistered 0.005 margin
- **Refit (`GRAPH-HAZARD-01/final`):** TCN on train patients (best epoch 8);
  blend on validation: intercept 0.257, logit(Run 4) 0.819, logit(TCN) 0.244;
  high-risk threshold 0.0758
- **Locked internal test (`compare_final_GRAPH-HAZARD-01`, second and final
  use):**

  | Model | AUROC | AUPRC | High-risk utility | Sensitivity | False alerts / 100 h | Septic flagged before onset |
  |---|---|---|---|---|---|---|
  | Run 4 (frozen) | 0.821 | 0.109 | 0.244 | 0.292 | 0.36 | 42.5% |
  | Run 4 + TCN fusion | 0.823 | 0.117 | 0.243 | 0.292 | 0.37 | 39.3% |
  | TCN only (descriptive) | 0.780 | 0.087 | 0.193 | 0.246 | 0.78 | 39.6% |
  | No-lab fallback (descriptive) | 0.770 | 0.074 | 0.170 | 0.219 | 0.77 | 62.5% |

  Paired bootstrap, fusion minus Run 4 (1,000 replicates): AUROC
  −0.001…+0.005, AUPRC +0.000…+0.016, utility −0.011…+0.008
- **Rule outcome:** credible AUPRC gain (lower bound just above zero), AUROC not
  worse, but utility point estimate −0.001, so the utility check fails
- **Decision:** reject. Frozen Run 4 stays primary; nothing is frozen, and no
  Dataset B request is made. The fusion improves ranking slightly but not
  alerting at the operating threshold
- **Interpretation:** temporal sequence models beat the tree on CV AUPRC but not
  on utility. They carry complementary signal (fusion AUPRC gain on the test),
  but this is too small to change bedside alert decisions. The locked test
  has now been used twice and is closed for model selection
- **Dataset B accessed:** no

## RESIDUAL-HAZARD-01 — preregistered additive physiology stack

- **Registered:** 2026-10-14, before implementation or execution
- **Reason:** the locked Dataset A test is closed after two challenger
  comparisons. This experiment is development-only and cannot establish a new
  deployment claim without fresh external evidence
- **Data:** Dataset A train+validation only; the existing patient-grouped fold
  assignments are reused. Dataset A test and Dataset B are prohibited
- **Reference:** a newly trained fold-wise LightGBM using the conservative
  7-leaf Run 4 recipe. It is named `run4_recipe_reference`; it is not the
  frozen Run 4 artifact
- **Additive feature candidates:** synchronized sparse-hour dynamics;
  fold-fitted healthy-reference next-hour residuals; fold-fitted ridge
  residualisation of physiology against care-process variables; and their
  additive union (`safe_stack`)
- **Hazard stage:** separate constrained 1/3/6/12-hour incident LightGBMs with
  post-onset censoring. Meta-training predictions are produced by inner
  patient-grouped cross-fitting; synthesis uses regularized logistic
  regression on the reference logit, hazard logits and adjacent logit
  differences
- **Decision-policy stage:** raw threshold, EMA, hysteresis and persistence
  policies are selected on a dedicated policy-tuning half of the outer
  calibration patients, disjoint from the half used for early stopping and
  isotonic calibration, and evaluated on the outer fold. An acute-surge
  bypass is evaluated rather than presumed useful
- **Primary metric:** mean normalized Challenge utility. Secondary/safety:
  AUPRC, AUROC, calibration, sensitivity, false alerts and worst pseudo-site
  AUPRC
- **Promotion within development:** utility gain at least 0.005, AUROC and
  AUPRC drops no more than 0.005, and worst pseudo-site AUPRC drop no more than
  0.01. Otherwise the simpler reference wins
- **Config:** `ml/configs/residual_hazard.yaml`; its SHA-256 is recorded when
  the run starts and resume is refused after any change
- **Claim limits:** zero-parameter transforms are not called overfit-proof;
  ridge residuals are not causal disentanglement; healthy-reference residuals
  are not patient counterfactuals; sparse hourly coupling is not transfer
  entropy; no expected performance lift is claimed
- **Implementation status:** complete; 53 ML tests pass. A 1,000-patient,
  one-fold smoke run exercised feature generation, nested hazard stacking and
  policy selection. Smoke metrics are diagnostic only and are not evidence
- **Dataset B accessed:** no

### Executed result — 2026-10-14

- **Scope:** completed all five patient-grouped development folds on Dataset A
  train+validation. Dataset A test and Dataset B were not accessed
- **Fresh reference:** AUROC 0.8156, AUPRC 0.0880, normalized utility 0.3986,
  worst pseudo-site AUPRC 0.0753
- **Selected additive candidate:** `plus_healthy_residual`, with AUROC 0.8174,
  AUPRC 0.0895, utility 0.4073 and worst pseudo-site AUPRC 0.0763. Relative to
  the fresh reference, the differences were +0.0018 AUROC, +0.0015 AUPRC,
  +0.0087 utility and +0.0010 worst pseudo-site AUPRC; it passed the
  preregistered development gate
- **Other feature findings:** sparse dynamics and OrthoBio each passed their
  individual development gates, but the combined `safe_stack` did not
  (utility gain +0.0031, below the required +0.005) and was rejected
- **Hazard finding:** the nested 1/3/6/12-hour stack raised AUROC by 0.0010 and
  AUPRC by 0.0035 over `plus_healthy_residual`, but lowered utility by 0.0082.
  It failed the primary utility check and was rejected
- **Policy finding:** EMA was selected in all five folds. Against a separately
  tuned raw policy on held-out outer folds, its mean utility difference was
  +0.0403, sensitivity difference +0.0533 and false-alert difference -0.0358
  per 100 patient-hours, passing the preregistered development policy gate.
  This is policy-level development evidence, not a frozen deployable policy or
  a prospective false-alert claim
- **Decision:** retain `plus_healthy_residual` as a development candidate and
  retain the EMA result for future policy work. Do not promote the hazard
  stack or combined safe stack. Frozen Run 4 remains the primary model because
  the internal test is closed and no fresh external validation exists.
  RESIDUAL-HAZARD-SETB-01 later rejected the frozen candidate on Dataset B
- **Artifacts:** `ml/artifacts/challengers/RESIDUAL-HAZARD-01/result.json`;
  config SHA-256
  `5dd641978ceb015b159a7722643a0a062b250d2fea10a1399e4fea914837a983`
- **Frozen-model integrity:** Run 4 `model.joblib` remains
  `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d`
- **Dataset B accessed:** no

## RESIDUAL-HAZARD-SETB-01 — preregistered one-time external comparison

- **Registered:** 2026-10-14, before final fitting, freezing or candidate access
  to Dataset B
- **Reason:** eICU is not currently available. The selected residual candidate
  has never seen Dataset B, so one frozen comparison can provide limited
  site-held-out evidence. Dataset B is not fresh to the overall project because
  frozen Run 4 has already been evaluated there; this limitation must be stated
- **Selection fixed from development:** `plus_healthy_residual`. The combined
  safe stack and multi-horizon hazard stage are prohibited. EMA with alpha 0.7
  is fixed because it was selected in four of five held-out development folds
- **Final fit:** HealthyResidualProjector and the fixed 7-leaf LightGBM use
  Dataset A train only, with 10% of train patients held out for early stopping.
  Isotonic calibration and raw/EMA operating thresholds use Dataset A
  validation only. Dataset A test remains prohibited and closed
- **External comparison:** frozen candidate system (healthy-residual risk score
  plus EMA high-risk policy) versus frozen Run 4, using each system's
  Dataset-A-validation-selected operating threshold and 500 paired
  patient-bootstrap replicates on Dataset B
- **Promotion rule:** candidate high-risk utility point estimate must not be
  below Run 4; at least one paired 95% interval lower bound for utility or AUPRC
  must be above zero; AUROC point drop must be at most 0.005; sensitivity point
  drop at most 0.02; and false-alert increase at most 0.05 per 100 patient-hours.
  All checks must pass
- **Fail-closed rule:** any failed check keeps frozen Run 4 primary. No
  post-result tuning, architecture change, recalibration or second Dataset B
  attempt is allowed
- **Authorization:** Tanvir Ahmed explicitly requested this one-time comparison
  on 2026-10-14. The protected access ledger must record the authorization
  before the command loads Dataset B. The assistant must not execute that
  command; the user runs it locally
- **Config:** `ml/configs/residual_hazard_setb.yaml`
- **Final-fit result:** `residual-healthy-ema-202610141727`, trained on Dataset A
  train and calibrated on Dataset A validation. The final model stopped at
  iteration 233. Its validation AUPRC was 0.0850; the EMA high-risk operating
  point had utility 0.2354 and 0.665 false alerts per 100 patient-hours. These
  validation figures are in-sample for calibration and threshold selection and
  are not external performance estimates
- **Frozen candidate SHA-256:**
  `7c430b30e66c882a4ddf467a8adbea1c403730f8c9f733f0d4d464b95e6ef33b`

### Executed result — 2026-10-14

- **Authorization:** Tanvir Ahmed ran the one-time command locally. Access
  ledger entry `setb-14836f6bc211` was recorded before Dataset B was loaded
- **Dataset B, frozen Run 4:** AUROC 0.8084, AUPRC 0.0792, high-risk utility
  0.2379, sensitivity 0.3139, false alerts 0.192 per 100 patient-hours
- **Dataset B, candidate system:** AUROC 0.7902, AUPRC 0.0639, high-risk utility
  0.1092, sensitivity 0.1420, false alerts 0.319 per 100 patient-hours
- **Dataset B, candidate raw score:** AUROC 0.7926, AUPRC 0.0632, high-risk
  utility 0.1124. The EMA policy did not rescue the candidate
- **Paired candidate-minus-Run-4 95% interval lower bounds:** utility −0.1487
  and AUPRC −0.0245. Point differences were utility −0.1287, AUROC drop 0.0182,
  sensitivity −0.1719 and false alerts +0.1269 per 100 patient-hours
- **Decision:** all five preregistered checks failed. The candidate is rejected.
  Frozen Run 4 remains the primary model. No retuning, recalibration,
  architecture change or second Dataset B attempt is permitted
- **Artifact:**
  `ml/artifacts/challengers/RESIDUAL-HAZARD-01/final/compare_setb.json`

