# Master implementation prompt — PredictRx Sentinel
## Role and required behavior

You are the lead ML engineer, clinical-AI safety engineer, backend engineer, evaluator, and technical product owner for an existing hackathon repository:

    C:\Users\Tanvir Ahmed\Downloads\PredictRx Sentinel 2\PredictRx Sentinel

Work directly in that repository. Inspect the current code, data availability, Git status, documentation, tests, and frozen artifacts before editing. Preserve unrelated/user-authored changes. Do not merely return another plan: implement the next safe phase, run all tests possible locally, document what changed, and give the user exact PowerShell commands for any data-heavy training or evaluation that must be run on the user's machine.

Do not silently skip any requirement in this prompt. Maintain a checklist showing completed, pending, blocked, and deliberately rejected items. If a proposed technique fails experimentally, report it honestly and retain the best validated model.

The current date is 2026-09-30. Congress Day is 2026-12-26. Prefer evidence and a reliable finished system over an overlarge unfinished research architecture.

## Competition context

Project: International AI Builders Congress 2026, Bangladesh, six-month program.

Chosen domain: HealthSphere AI.

Chosen challenge: PredictRx — early prediction of disease, complications, and medication risk.

Specific ask: validated risk reduction with documented safeguards.

Challenge details emphasize predictive ML, knowledge graphs, and explainability.

Judging:

1. Innovation — 20%
2. Technical execution — 20%
3. Business model and global readiness — 20%
4. Real-world impact and ethical AI compliance — 20%
5. Scalability and NRB collaboration — 10%
6. Presentation — 10%

The goal is not merely a high AUROC. The final system needs reproducible modelling, external-site evidence, meaningful AI, calibration, alert-utility evidence, explainability, privacy/safety, honest limitations, adoption readiness, deployment, and a compelling demonstration. Nevertheless, improving the predictive benchmark without overfitting is a primary objective.

## Existing product

PredictRx Sentinel is a research prototype for adult ICU sepsis early warning. It consumes hourly vitals, labs, demographics, and administrative data, produces a calibrated risk score, shows risk bands and SHAP factors, supports clinician alert acknowledgement/dismissal/escalation, and records an audit trail.

Current stack:

- ML: Python, pandas/Polars, LightGBM, scikit-learn, SHAP
- API: FastAPI/Pydantic
- Frontend: Next.js/TypeScript/Tailwind/ECharts
- Deployment: Docker Compose
- Current persistence: SQLAlchemy restart snapshots and append-only audit rows;
  SQLite local/offline, PostgreSQL through `DATABASE_URL`

Research prototype only. It is not approved for clinical use, diagnosis, treatment, prescription, or autonomous patient contact.

## Dataset facts and permitted claims

The project uses PhysioNet/Computing in Cardiology Challenge 2019 v1.0.0, not the PhysioNet 2012 mortality challenge.

The data are longitudinal hourly ICU EHR records with 8 vitals, 26 laboratory variables, and 6 demographic/administrative variables.

Current repository/data-card counts:

- Raw Dataset A: 20,336 patients
- Raw Dataset B: 20,000 patients
- Dataset A adult split:
  - train: 14,235 patients, 1,259 septic
  - validation: 3,050 patients, 246 septic
  - internal test: 3,051 patients, 285 septic
- Dataset B after age exclusion: 19,978 patients, 1,140 septic
- Dataset A hourly rows: 790,215
- Dataset B hourly rows: 761,246
- Eligible Dataset B rows after excluding the first three hours:
  - 761,246 − 19,978 × 3 = 701,312
  - this exactly matches the existing evaluation report

Dataset A and Dataset B come from geographically distinct hospital systems and different EHR environments. Dataset B is a valid site-held-out public cohort, but it is the public Challenge training set B, not the original competition's secret Hospital C.

Use this exact wording:

> Site-held-out retrospective validation on a geographically distinct public hospital cohort.

Do not call Dataset B fully blind external clinical validation. Do not claim prospective validation or clinical outcome improvement.

Raw and processed data are gitignored and may not exist in the agent's environment. Never commit raw patient files. If data are absent, implement the code and tests using synthetic fixtures, then give the user the exact run commands.

MIMIC-IV is also BIDMC-origin and is not automatically a new geographical-hospital validation source. Naively pooling different datasets with mismatched sepsis definitions, units, or workflows is prohibited.

## Frozen evidence model: never overwrite

Current frozen model:

- Version: v0.2.0-202609281906
- Type: LightGBM, 7 leaves, approximately 311 selected iterations, 673 features
- Calibration: isotonic regression fitted on Dataset A validation
- Frozen model SHA-256:
  a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d
- Watch threshold: 0.02364907819453274
- High-risk threshold: 0.08355437665782493

Dataset B metrics:

- AUROC: 0.808395
- AUPRC: 0.079208
- positive-hour prevalence: 0.014285
- Brier: 0.013652
- equal-mass ECE: 0.003202
- high-risk normalized utility: 0.237928
- high-risk sensitivity: 0.313853
- high-risk specificity: 0.956816
- high-risk false alerts per 100 patient-hours: 0.192185
- septic patients alerted before onset: 35.7%
- first alert in the 0–12-hour pre-onset/optimal window: 7.7%
- median warning among early high-risk alerts: 41 hours
- Watch normalized utility: 0.282592
- Watch septic patients flagged before onset: 80.3%
- Watch false alerts per 100 patient-hours: 2.052819

Internal test metrics:

- AUROC: 0.821
- AUPRC: 0.109
- high-risk utility: 0.244
- utility-optimal utility: 0.422

The current internal test was consulted across four model-development runs. Treat its estimate as mildly optimistic. Dataset B is the primary performance estimate for the frozen version.

Before any work, preserve the frozen model in an immutable versioned directory if it is not already preserved. Verify the SHA-256 before and after. Never train into artifacts/models/latest and never overwrite the frozen model, FROZEN.json, metrics.json, or eval_holdout.json.

Create separate directories such as:

    ml/artifacts/models/run4_frozen/
    ml/artifacts/experiments/<run_id>/
    ml/artifacts/challengers/<run_id>/

Do not delete or rewrite the original evidence.

## Claims that are currently forbidden

Do not use any of the following unless new evidence genuinely supports them:

- record-breaking
- state of the art
- clinically validated
- clinically proven risk reduction
- improves mortality
- prevents sepsis
- exact probability of developing sepsis within the next six hours
- validated for Bangladesh
- fully blind external validation

The current output is best described as a calibrated PhysioNet challenge-label early-warning score. PhysioNet SepsisLabel becomes 1 six hours before defined onset and remains 1 afterward, so ordinary row-level AUROC includes post-onset/easier positive hours. It is not a pure incident six-hour hazard probability.

Keep two evaluation views:

1. Official Challenge-compatible label/utility view for reproducible comparison.
2. Clinically aligned incident-onset view that censors post-onset hours and predicts onset within explicit horizons.

Never change the label silently. Document every target definition.

Do not create a leaderboard that directly compares this AUROC against COMPOSER, Sepsis Watch, TREWS, Prenosis, Epic, or other studies with different populations, horizons, labels, biomarkers, snooze/abstention policies, deployment designs, or prospective workflows.

## Important interpretation caveats

- AUROC 0.808 on Dataset B is respectable, not worthless and not record-breaking.
- AUPRC must be interpreted with the 1.43% positive-hour prevalence.
- ECE 0.0032 is not sufficient proof of perfect calibration at low prevalence.
- Existing Brier skill versus a constant-prevalence predictor is only approximately 3%; calculate it exactly and report it.
- Add calibration intercept/slope, reliability curves, confidence intervals, and threshold-specific evidence.
- High-risk sensitivity is only 31.4% at 95.7% specificity.
- The 41-hour median warning and low proportion in the desired 0–12-hour window mean timing policy needs careful analysis.
- Retrospective prediction metrics are not validated clinical risk reduction.

## Current model audit and weaknesses

The current training sweep contains only four LightGBM configurations and primarily changes num_leaves and min_child_samples.

Current defaults include learning rate 0.03, min_child_samples 500, subsample 0.7, colsample_bytree 0.3, reg_lambda 5, scale_pos_weight 1, up to 3,000 estimators, and row-level binary-logloss early stopping.

Weaknesses:

- Early stopping optimizes row-level binary log-loss, not early patient detection, AUPRC, or utility.
- Long-stay patients contribute more rows and can receive disproportionate weight.
- Effective independent sample size is closer to patient count than hourly-row count.
- There are 673 correlated handcrafted features but only 1,259 septic training patients.
- The five-member patient-bootstrap LightGBM ensemble was already attempted and performed worse on validation utility than the single model:
  - single: 0.4017
  - ensemble: 0.3924
- Therefore, do not repeat a same-model averaging ensemble and call it innovation.
- Top SHAP drivers include FiO2_hours_since, lactate time-since-measured, ICU length of stay, unit type, and other care-process/missingness variables.
- The model may partially learn when clinicians order tests rather than only physiology.
- More arbitrary rolling windows or redundant ratios can strengthen site-specific shortcuts.

## Non-negotiable no-leakage and model-selection rules

1. Dataset B must never be used for feature selection, hyperparameter tuning, architecture selection, early stopping, calibration, threshold selection, ensemble weighting, ablation decisions, or deciding which challenger to keep.
2. Do not repeatedly evaluate experimental models on Dataset B.
3. All challenger development is Dataset A only.
4. Splits are patient-level. A patient must never appear in more than one fold/split.
5. Preprocessing, imputation, scaling, feature selection, pseudo-site clustering, and calibration must be fitted only inside the appropriate training/development fold.
6. Log every experiment, seed, config, code commit, dataset hash, split hash, elapsed time, and result.
7. Use a bounded, preregistered experiment budget. Do not perform unlimited validation-set fishing.
8. Do not train on A+B while claiming B as external evidence.
9. A future A+B production model is allowed only after architecture selection and only if a new untouched external cohort is reserved.
10. The user, not the agent, authorizes final Dataset B scoring. The agent must stop and provide the exact command before any new challenger touches B.

## Master execution order

Follow these phases in order. Do not jump to the flashy model before evidence integrity and software defects are handled.

# Phase 0 — preflight, preservation, and reproducibility

Tasks:

1. Inspect Git status and preserve unrelated changes.
2. Read README, ML README, model card, data card, safety/ethics, decisions, architecture, knowledge map, backend engine, schemas, API routes, frontend model/patient/alert screens, tests, train/eval/freeze code, configs, and all current metrics.
3. Verify current frozen model hash.
4. Copy/reference it into an immutable run4_frozen directory without changing bytes.
5. Create an experiment ledger:

    docs/experiment-ledger.md

   Each entry must include run ID, objective, hypothesis, dataset/splits, target, features, model family, config hash, code commit, seed, metrics, confidence intervals, decision, and reason.
6. Strengthen the freeze manifest to include:
   - raw-data checksum manifest hash
   - split manifest hash
   - processed feature-file hash
   - config hash
   - feature-schema/code hash
   - model hash
   - Git commit
   - Python/dependency versions
   - target definition
   - calibration dataset
   - threshold-selection dataset
7. Add an evaluation-access ledger/lock so a model version cannot be accidentally scored repeatedly on Dataset B without an explicit override and recorded reason.
8. Run existing unit tests and report skipped tests explicitly.
9. Correct documentation claims that are ahead of implementation.

Exit criteria:

- Frozen SHA still matches.
- No evidence artifact was overwritten.
- Experiment/freeze/evaluation governance is machine-readable.
- Current tests pass or failures are documented before proceeding.

# Phase 1 — close the current evidence gap: baselines on Dataset B

Implement a small, reproducible baseline evaluation command. Requirements:

- Fit clinical-rule score and logistic regression using Dataset A train only.
- Fit imputers/scalers only on Dataset A train.
- Fit isotonic calibration on Dataset A validation only.
- Select every model's thresholds on Dataset A validation only.
- Apply those frozen transformations, calibration objects, and thresholds to Dataset B.
- Never select thresholds on Dataset B.
- Score clinical rule, logistic regression, and frozen Run 4 on exactly the same eligible Dataset B rows.
- Include both:
  - each model's A-validation-selected operating point
  - matched-specificity or matched-alert-burden comparisons
- Preserve the frozen LightGBM unchanged.

Add:

- AUROC
- AUPRC
- AUPRC divided by prevalence
- Brier score
- exact Brier skill versus constant-prevalence prediction
- ECE with clearly documented binning
- calibration intercept and slope
- reliability plot
- normalized PhysioNet utility
- sensitivity, specificity, PPV, NPV
- false alerts per 100 patient-hours
- alerts per patient-day
- alert-event precision
- septic patients detected before onset
- detected in the desired/optimal timing window
- median warning time
- patient-level paired bootstrap 95% confidence intervals
- paired model-difference confidence intervals where possible
- decision-curve/net-benefit analysis if methodologically valid for the selected horizon/threshold

Write one immutable result bundle containing metrics, plots, data/model/config hashes, timestamp, and command.

Release-rule wording must specify whether “beats both baselines on Dataset B” means ranking, utility, AUPRC, or a matched operating point. Do not move goalposts after seeing B.

If processed/raw data are unavailable to the agent, implement and test the script with synthetic fixtures, then give the user the exact PowerShell command and ask for the complete output/result bundle.

Exit criteria:

- Honest Dataset B baseline comparison complete.
- No B-based tuning occurred.
- Model card and dashboard reflect the new evidence.

# Phase 2 — data, target, feature, and leakage audit

Implement a reproducible audit report.

Check:

- raw file counts and checksum coverage
- adult exclusion counts
- patient uniqueness across train/validation/test/B
- exact row counts and eligible-row calculation
- chronological ordering within each patient
- duplicated hours/records
- units/ranges
- SepsisLabel transition pattern
- derived onset calculation
- target construction
- no use of future rows in rolling windows, deltas, expanding baselines, forward fill, or measurement frequency
- no cross-patient forward fill/imputation
- split assignment before any fitted preprocessing
- feature columns and all-empty columns
- any hidden target proxies or direct leakage
- static variables and missing-value behavior

Create the clinically aligned incident targets:

- onset within 1 hour
- onset within 3 hours
- onset within 6 hours
- onset within 12 hours

For incident-hazard targets:

- use only information available at prediction time
- censor post-onset rows
- clearly define whether the onset hour is included
- retain all non-septic eligible hours as controls, with appropriate weighting/sampling
- preserve a separate official Challenge-compatible head/evaluation

Do not replace the frozen model's historical target. Add a new target version and document it.

Run feature-family ablations using Dataset A only:

1. physiology current values only
2. physiology plus temporal trends
3. missingness/care-process features only
4. clinical scores only
5. physiology plus care-process
6. all 673 features

Determine whether a missingness/process-only model is unexpectedly strong. Report this as a care-process shortcut audit, not as proof of clinical causality.

Exit criteria:

- Data/target audit is reproducible.
- Official and incident-hazard targets cannot be confused.
- Leakage and care-process findings are documented.

# Phase 3 — fix current real-time/backend safety defects

Fix and test every item below:

1. Watch is a passive screening state and must not create the same interruptive alert as High Risk unless product requirements are explicitly changed and re-evaluated.
2. Sparse API timestamps must not compress missing hours into consecutive ICU hours. Preserve the real hourly timeline and gaps.
3. Live API prediction timestamps must come from actual observation/event time, not the fixed demo replay epoch.
4. Validate units and plausible clinical ranges. Reject or quarantine malformed/out-of-range inputs with structured errors and audit events.
5. Respect encounter_id. Do not merge separate encounters for the same patient.
6. Propagate static demographics correctly across later rows without inventing values.
7. Handle duplicated, out-of-order, and late-arriving observations idempotently.
8. Recompute every affected later prediction when late data alter history, without duplicating alerts.
9. Data freshness must not use the freshest one of several vitals as proof that all required vitals are fresh. Expose per-signal freshness and a conservative aggregate.
10. Unknown codes must be auditable rather than silently ignored.
11. Add malformed payload, unit, range, duplicate, gap, late-data, separate-encounter, stale-data, and idempotency tests.
12. Add role-based authentication/authorization for clinician/admin workflows.
13. Replace in-memory audit/patient/alert state with PostgreSQL persistence.
14. Audit records should be append-only/tamper-evident enough for the prototype; include actor, event time, source time, model version/hash, input provenance, prediction, action, and reason.
15. Do not claim encryption, RBAC, PostgreSQL, or full audit persistence as shipped until implemented and tested.
16. Keep replay/demo behavior separated from real ingestion behavior.
17. Add concurrency, restart-persistence, and basic load tests.

Update docs/architecture.md and docs/safety-ethics.md to match reality exactly.

Exit criteria:

- Tests cover all failure modes above.
- Documentation and implementation agree.
- No Watch-alert burden bug.
- Restart does not erase persistent audit data.

# Phase 4 — build a genuinely strong optimized tabular baseline

Do this before the novel deep model.

Create a new A-only development pipeline; never overwrite Run 4.

Required experiments:

1. Patient-balanced row/sample weights so long ICU stays do not dominate solely because they contain more rows.
2. Time-to-onset/utility-aware sample weighting, carefully separated from the official evaluation metric.
3. LightGBM versus CatBoost comparison.
4. Patient-grouped five-fold cross-validation.
5. Missingness-pattern pseudo-site groups created without labels and inside the relevant training fold.
6. Track both mean-fold and worst-pseudo-site performance.
7. Bounded Optuna or equivalent search, approximately 30–50 trials per justified family, with a fixed seed and saved study database.
8. Tune more than leaves:
   - depth/leaves
   - min child constraints
   - learning rate/iterations
   - row/column subsampling
   - L1/L2 regularization
   - class/sample weighting
   - max bin or equivalent only if justified
9. Early stopping/model selection must consider AUPRC and utility, not only binary log-loss.
10. Run the feature-family ablations from Phase 2.
11. Perform fold-wise feature importance/stability analysis.
12. Prune redundant/unstable/site-specific feature families only inside development folds.
13. Do not add hundreds of arbitrary rolling windows or ratios.
14. Allowed informative candidates include acceleration/slope change, cross-organ temporal lag, persistent-abnormality duration, measurement-value-mask-time tuples, organ trajectory, and robust patient-baseline deviation.

Store:

- out-of-fold predictions
- trial database
- configs
- fold assignments
- calibration objects
- thresholds
- metrics and CIs
- runtime/memory/CPU inference benchmark
- feature/ablation reports

The internal A test may be used once for the final tabular challenger comparison, not after every trial.

Promotion requires a credible paired improvement in AUPRC and/or utility, no material AUROC regression, acceptable calibration, improved sensitivity near the current 95.7% specificity, and improved worst-pseudo-site performance.

# Phase 5 — new model innovation: Sentinel Graph-Hazard

Implement a challenger called Sentinel Graph-Hazard:

> A sampling-invariant, organ-graph, multi-horizon temporal sepsis model.

This must not be a generic Transformer with a new name. Its novelty must be demonstrated through architecture, objective, ablations, and cross-site evidence.

## 5A. Required baselines before the novel model

Implement and compare A-only:

- optimized tabular LightGBM
- CatBoost
- physiology-only LightGBM
- GRU-D or an equivalent missingness-aware recurrent baseline
- a TCN baseline if feasible
- STraTS-style sparse event encoder or a carefully justified equivalent

Do not claim the novel architecture wins unless it beats these fairly.

## 5B. Sparse event representation

Use raw/normalized observation events represented as:

- variable ID
- measured value
- ICU/event time
- time since that variable was last measured
- observed/missing mask
- optional source/unit metadata when available

Fit normalization on training folds only. Do not depend on the full 673-column engineered matrix for the temporal branch.

## 5C. Organ-system knowledge graph inside the model

Create a versioned graph with variables mapped to:

- cardiovascular
- respiratory
- renal
- hepatic
- coagulation
- inflammatory/perfusion
- acid-base/metabolic
- contextual/care-process nodes kept clearly separate

Use graph/message-passing or graph attention to model cross-organ interaction. The graph must influence representation/prediction, not merely decorate the UI.

Version every edge/node and cite its source/provenance. Keep learned associations separate from curated clinical relationships. Do not claim graph edges are causal.

## 5D. Multi-horizon dynamic hazard heads

Predict incident onset within:

- 1 hour
- 3 hours
- 6 hours
- 12 hours

Censor post-onset rows for incident-hazard training. Maintain a separate official Challenge-compatible head or mapping so the model can be evaluated with the official utility protocol without misrepresenting the deployment probability.

## 5E. Sampling-invariance and robustness

Prevent the model from relying excessively on a hospital's test-ordering policy:

- random clinically plausible lab-drop augmentation
- time-delay augmentation
- value masking
- consistency loss between original and corrupted views
- pseudo-site grouping by measurement patterns
- regularized worst-group/Group-DRO-style optimization if validated

Do not force invariance so strongly that clinically meaningful missingness is erased. Run ablations and report the trade-off.

## 5F. Auxiliary self-supervised/clinical tasks

Evaluate auxiliary heads for:

- next-hour SOFA-lite organ components
- next-observed vital/lab range or masked-event reconstruction
- worsening versus stable organ trajectory

These tasks should regularize the encoder and exploit unlabeled hours. Remove any auxiliary task that does not improve locked A-only validation or robustness.

## 5G. Utility-aligned objective

Use a transparent composite objective such as:

- incident-hazard classification/survival loss
- time-to-onset or PhysioNet-utility-inspired weighting
- auxiliary reconstruction/trajectory loss
- sampling-consistency loss
- optional worst-group loss

Log every coefficient and conduct ablations. Do not optimize a non-differentiable test metric through test-set iteration.

## 5H. Heterogeneous fusion

Do not average five near-identical models.

Fuse:

- optimized aggregate-feature tree model
- Graph-Hazard temporal model

Use out-of-fold predictions to fit a small regularized meta-model or a preregistered weighted blend. Learn weights on A development data only. Calibration and alert thresholds come from A validation only.

Required ablation table:

1. optimized LightGBM
2. sparse temporal encoder
3. temporal + organ graph
4. plus multi-horizon heads
5. plus auxiliary tasks
6. plus sampling invariance
7. final tree-temporal fusion

Report mean and worst-fold/pseudo-site metrics, parameters, latency, and calibration.

## 5I. Overfitting controls

- fixed experiment budget
- patient-grouped folds
- no B access
- early stopping
- weight decay/dropout
- limited model size appropriate to roughly 14k training patients
- fold-contained preprocessing
- no architecture selection from A test
- no hidden manual selection based on pretty curves
- patient-level paired bootstrap
- negative results retained in experiment ledger

Promotion is evidence-based. If Graph-Hazard underperforms the optimized tree model, keep the tree model as primary and report Graph-Hazard honestly as an unsuccessful challenger. Do not promote it for novelty alone.

# Phase 6 — freeze the winning challenger and request one-time Dataset B run

Before Dataset B:

1. Select exactly one final challenger using A-only evidence.
2. Freeze weights, preprocessing, graph, calibration, thresholds, fusion weights, target, and code.
3. Generate the strengthened freeze manifest.
4. Record the model hash and command.
5. Produce a preregistered comparison specification against Run 4 and both baselines.
6. Stop and ask the user to run the final B command. Do not run it automatically.

Compare on identical patients/eligible rows:

- AUROC
- AUPRC and AUPRC/prevalence
- utility
- sensitivity at approximately the same specificity/alert burden
- calibration/Brier/Brier skill
- false alerts
- early patient detection
- timing-window detection
- subgroup and pseudo-site/missingness robustness
- patient-level paired bootstrap differences

A change from 0.808 to 0.812 is not automatically meaningful. The paired uncertainty and operational metrics decide.

If the challenger fails on B, do not tune on B and retry. Retain frozen Run 4 as the primary externally evidenced model. Develop a new version only with a new preregistered external cohort.

# Phase 7 — TrustGate product innovation on top of the selected primary model

After the primary predictive model is chosen, implement PredictRx Sentinel TrustGate:

> The sepsis AI that knows when not to alert.

TrustGate is not a replacement name for the same score. It is a measurable reliability and deployment layer.

## 7A. Patient-level reliability gate

For each prediction expose:

- calibrated risk
- model disagreement/uncertainty, correctly named and validated
- per-signal data freshness
- out-of-distribution/shift score
- alert stability under plausible perturbations
- final state:
  - Alert
  - Watch
  - Verify data
  - Abstain

The current bootstrap ensemble spread is only model disagreement. Do not call it a validated confidence interval until evaluated.

If a high-risk score flips under plausible missing/delayed-data scenarios, do not silently treat it as a reliable alert. Route to review/verification according to a preregistered policy.

## 7B. Data Failure Simulator

Replay and test:

- vital delays of 2/6/12 hours
- missing lactate or lab groups
- duplicate observations
- late-arriving observations
- out-of-order observations
- implausible values/units
- hospital-specific measurement frequency
- sensor/lab dropout

Measure:

- alert flip rate
- unstable alerts
- retained sensitivity
- false-alert change
- timing change
- coverage/abstention

Do not claim prevented harm; claim retrospective alert-stability improvement only.

## 7C. Hospital Readiness Passport

Create an automated site report with:

- discrimination
- calibration
- prevalence
- alert burden
- missingness/measurement shift
- age/sex/unit/missingness subgroup evidence
- threshold transfer
- data-schema/unit readiness
- recommended mode:
  - Do not deploy
  - Retrospective validation
  - Silent pilot
  - Controlled pilot candidate

Use the current evidence honestly: Dataset B high-risk utility transferred relatively well, while Watch sensitivity/threshold behavior degraded. The passport should be capable of recommending local recalibration/silent mode without retraining the model blindly.

## 7D. Evidence knowledge graph

Replace the static dictionary/stub with a versioned, queryable graph:

    Observation
      → temporal change
      → organ system
      → dysfunction concept
      → model contribution
      → evidence source
      → safeguard/review action

Separate:

- what influenced the model
- curated clinical context
- data provenance
- safeguards

Never present SHAP or graph paths as causal treatment recommendations.

## 7E. TrustGate validation

Primary retrospective claim template:

> At the same sensitivity or fixed alert budget, TrustGate reduced false or unstable alerts by X% while preserving Y hours of warning on the evaluated cohorts.

Do not fill X or Y until measured.

Metrics:

- false alerts per 100 patient-hours
- sensitivity at fixed alert budget
- alert-event precision
- alert flip rate
- prediction coverage
- abstention rate
- median warning time
- utility
- subgroup effects

# Phase 8 — product workflow, Bangladesh readiness, and business differentiation

Implement a memorable workflow, not a generic dashboard:

1. ICU command center prioritizes beds.
2. Patient page shows incident-horizon risk, trajectory, reliability state, and data freshness.
3. Explanation separates model influence from clinical knowledge.
4. Fragile prediction becomes Verify data or Abstain, not a confident alarm.
5. Only the appropriate alert state interrupts clinicians.
6. Clinician acknowledges, dismisses with reason, or escalates.
7. Every step is audited.
8. Hospital Readiness Passport gates deployment.

Bangladesh/LMIC path:

- CPU/on-prem/offline-capable inference
- low-resource vital-only fallback model, separately validated
- explicit performance degradation when labs are absent
- Bangla/localized clinician-facing copy where useful
- no claim of Bangladesh validity without local data
- retrospective local validation
- 4–8 week silent pilot
- threshold recalibration
- controlled prospective evaluation
- institutional ethics/data-use approval

Business model:

- sell a SafeLaunch/silent-validation service before a live-alert subscription
- customer is hospital/ICU/quality program, not patient
- readiness report and monitoring lower adoption risk
- expand the safety/evidence platform to AKI, respiratory deterioration, and other complications only after sepsis evidence is stable

NRB/local collaboration:

- seek an ICU clinician, clinical informatician, biostatistician, or responsible-AI advisor
- record what they reviewed
- do not imply endorsement without written evidence
- include structured usability/clinical feedback and resulting changes

# Phase 9 — deployment and engineering completion

Complete:

- PostgreSQL persistence
- RBAC
- environment/secret handling
- migrations
- Docker production/offline backup
- CI for Python tests, frontend lint/build, schema checks, and artifact-integrity checks
- public demo such as Hugging Face Space only if patient data/artifact licensing and privacy are safe
- load/performance tests
- model-version rollback
- health/readiness endpoints
- limited FHIR R4 adapter only after normalized ingestion is correct
- no RAG treatment assistant
- evidence citations can be retrieved/displayed, but LLM text must never alter the risk score

# Phase 10 — documentation, presentation, and final evidence pack

Update:

- README
- model card
- data card
- safety/ethics
- architecture
- knowledge graph documentation
- API/data contract
- deployment guide
- experiment ledger
- validation report
- threat/failure-mode report
- business/adoption plan
- demo script

Final pitch:

> PredictRx Sentinel is not another sepsis score. It combines a sampling-robust, organ-aware temporal hazard model with a deployment gate that tests whether an alert is reliable at this patient and this hospital before interrupting care.

Only use this pitch if both the model and TrustGate are actually implemented and evaluated.

The final evidence hierarchy:

1. frozen model and reproducibility hashes
2. Dataset A development and ablations
3. internal locked comparison
4. Dataset B one-time site-held-out comparison
5. baseline comparison
6. calibration and alert-utility analysis
7. robustness/failure simulation
8. subgroup analysis
9. software tests/security/audit evidence
10. partner/usability evidence

## Required command workflow

The agent must verify the final CLI after implementing scripts. The intended PowerShell workflow is below; adjust module names only when implementation requires it and document the change.

From repository root:

    Set-Location "C:\Users\Tanvir Ahmed\Downloads\PredictRx Sentinel 2\PredictRx Sentinel"
    py -3.11 -m venv .venv
    ./.venv/Scripts/Activate.ps1
    python -m pip install --upgrade pip
    pip install -r ml/requirements.txt -r backend/requirements.txt
    pip install -e ./ml

Data checks:

    Set-Location ml
    python -m predict_rx.data.checksum --root data/raw
    python -m predict_rx.data.explore --root data/raw/training_setA --n 20
    python -m predict_rx.data.explore --root data/raw/training_setB --n 20

Feature builds:

    python -m predict_rx.features.build --raw data/raw/training_setA --split-config configs/splits.yaml --out data/processed/features_setA.parquet
    python -m predict_rx.features.build --raw data/raw/training_setB --holdout --out data/processed/features_setB.parquet

Existing tests:

    pytest -q tests
    Set-Location ../backend
    pytest -q

Frontend:

    Set-Location ../frontend
    npm ci
    npm run lint
    npm run build

The new agent must create and document exact commands for:

- data/leakage audit
- Dataset B baseline evaluation
- bootstrap confidence intervals/calibration plots
- optimized tabular A-only search
- tabular final A test
- GRU-D/TCN/STraTS baselines
- Graph-Hazard A-only training
- Graph-Hazard ablations
- fusion training
- challenger freeze
- final one-time Dataset B evaluation
- TrustGate robustness evaluation
- demo case export
- Docker/CI run

Suggested stable CLI names:

    python -m predict_rx.audit.data --set-a data/processed/features_setA.parquet --set-b data/processed/features_setB.parquet --authorized-by "Taskin" --authorize-dataset-b "Taskin authorizes this structural Dataset B audit only"
    python -m predict_rx.eval.baselines_setb --set-a data/processed/features_setA.parquet --set-b data/processed/features_setB.parquet --model-dir artifacts/models/run4_frozen --authorized-by "Taskin" --authorize-dataset-b "Taskin authorizes this one-time preregistered baseline comparison"
    python -m predict_rx.train.challenger --features data/processed/features_setA.parquet --config configs/challenger_tabular.yaml --out artifacts/challengers/<run_id>
    python -m predict_rx.train.challenger_gate --ml-root . --out artifacts/governance/challenger_gate.json
    # Graph-Hazard has no training CLI until this gate passes; do not bypass it.
    python -m predict_rx.eval.compare_internal --features data/processed/features_setA.parquet --challenger artifacts/challengers/<run_id> --anchor artifacts/models/run4_frozen
    python -m predict_rx.train.freeze --model-dir artifacts/challengers/<run_id>
    python -m predict_rx.eval.run --features data/processed/features_setB.parquet --model-dir artifacts/challengers/<run_id> --split holdout
    python -m predict_rx.robustness.failures --raw-dir data/raw/training_setA --patient-list configs/locked_robustness_patients.txt --model artifacts/models/run4_frozen/model.joblib --out artifacts/experiments/TRUSTGATE-ROBUSTNESS-01.json

These new module names are requirements to implement or replace with equally clear documented CLIs. The final Dataset B challenger command must not be executed by the agent without explicit user authorization.

## Required progress reports to the user

After each phase, report:

- what changed
- files changed
- tests run and results
- evidence produced
- unresolved risks
- exact next command for the user
- what output the user should send back
- whether Dataset B was accessed

Never say “done” when data-heavy evaluation was not run. Say “implementation complete; empirical result pending user run.”

## Stop/go decision rules

Stop and keep Run 4 if:

- challenger only improves a repeatedly used development split
- B improvement is absent or operational metrics worsen
- calibration fails
- result depends on leakage/post-onset inflation
- graph/Transformer adds complexity without evidence
- external robustness worsens

Promote a challenger only if:

- A-only development was clean
- locked comparison supports it
- one-time B comparison supports it
- utility/AUPRC/sensitivity-calibration trade-off is better
- paired confidence intervals make the gain credible
- latency/deployment remain practical

TrustGate is promoted only if it demonstrates an explicit reliability/alert-burden benefit at a controlled sensitivity or alert budget.

## Final “do not miss” checklist

- Preserve Run 4 and SHA.
- Complete B clinical-rule and logistic baselines.
- Add patient-level paired bootstrap CIs.
- Add calibration slope/intercept, reliability curve, Brier skill, and justified net benefit.
- Audit raw/split/processed/config/code/model hashes.
- Enforce/record Dataset B access.
- Audit label and build separate incident-hazard targets.
- Audit feature leakage and care-process shortcuts.
- Patient-balance long stays.
- Properly optimize LightGBM/CatBoost on A only.
- Use grouped CV and worst pseudo-site performance.
- Implement temporal baselines before claiming Graph-Hazard superiority.
- Put the knowledge graph inside the model and version its provenance.
- Implement multi-horizon heads.
- Implement sampling-invariance augmentations/ablation.
- Implement auxiliary tasks only if useful.
- Use heterogeneous out-of-fold fusion.
- Freeze before final B.
- Never tune on B after failure.
- Fix Watch alert behavior.
- Fix missing-hour compression.
- Fix live timestamps.
- Validate units/ranges.
- Respect encounter IDs.
- Fix demographic propagation.
- Handle duplicate/late/out-of-order data idempotently.
- Fix freshness calculation.
- Add RBAC/PostgreSQL/persistent audit.
- Test malformed and late-arriving data.
- Implement TrustGate reliability states.
- Implement failure simulator.
- Implement Hospital Readiness Passport.
- Replace static knowledge-map stub with a real evidence graph.
- Keep SHAP/clinical context/non-causality separate.
- Add low-resource fallback and Bangladesh silent-pilot protocol.
- Complete Docker, public demo if safe, CI, and offline backup.
- Align every claim with implemented evidence.
- Do not claim clinical risk reduction from retrospective prediction alone.
- Record negative experiments.
- Give the user exact commands and wait for outputs at every empirical gate.

Begin with Phase 0 and Phase 1. Do not start Graph-Hazard implementation until the evidence pipeline, baseline-B command, data audit, and critical backend correctness defects have a tested foundation.

