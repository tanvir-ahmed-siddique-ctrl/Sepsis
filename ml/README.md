# ML package — PredictRx Sentinel

## Setup

```powershell
Set-Location "C:\Users\Tanvir Ahmed\Downloads\PredictRx Sentinel 2\PredictRx Sentinel"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ml\requirements.txt -r backend\requirements.txt
pip install -e .\ml
Set-Location ml
```

## Download PhysioNet Challenge 2019 data

1. Create a free PhysioNet account and accept the data use terms for [challenge-2019](https://physionet.org/content/challenge-2019/1.0.0/).
2. Download training sets A and B (or the combined challenge archives).
3. Place extracted patient `.psv` files under:

```
ml/data/raw/training_setA/
ml/data/raw/training_setB/
```

4. Record checksums:

```powershell
python -m predict_rx.data.checksum --root data/raw
```

Raw data is gitignored. Never commit patient files.

## Pipeline commands

```powershell
# Integrity and preflight (the current placeholder parquet files fail closed)
python -m predict_rx.governance.preflight --ml-root . --repo-root .. --report-only

# Explore / sanity-check both source cohorts
python -m predict_rx.data.explore --root data/raw/training_setA --n 20
python -m predict_rx.data.explore --root data/raw/training_setB --n 20

# Build patient-hour feature matrices
python -m predict_rx.features.build --raw data/raw/training_setA --split-config configs/splits.yaml --out data/processed/features_setA.parquet
python -m predict_rx.features.build --raw data/raw/training_setB --holdout --out data/processed/features_setB.parquet

# Structural data/target audit. Dataset B access requires explicit authorization.
python -m predict_rx.audit.data --set-a data/processed/features_setA.parquet --set-b data/processed/features_setB.parquet --authorized-by "Taskin" --authorize-dataset-b "Taskin authorizes this structural Dataset B audit only"

# Preregistered frozen-model/baseline comparison. This is a protected B access.
python -m predict_rx.eval.baselines_setb --authorized-by "Taskin" --authorize-dataset-b "Taskin authorizes this one-time preregistered baseline comparison"

# A-only grouped tabular challenger. Never write into models/latest.
# Laptop budget (~3-5 h). If interrupted, rerun the same command with --resume.
python -m predict_rx.train.challenger --features data/processed/features_setA.parquet --config configs/challenger_tabular_laptop.yaml --out artifacts/challengers/TABULAR-AONLY-01

# Check whether temporal / Graph-Hazard work is allowed to start.
python -m predict_rx.train.challenger_gate --ml-root . --out artifacts/governance/challenger_gate.json

# Freeze a challenger before any Dataset B scoring. Never freeze into latest or run4_frozen.
python -m predict_rx.train.freeze --model-dir artifacts/challengers/TABULAR-AONLY-01

# One-time frozen-challenger Dataset B evaluation. Do not run until the user authorizes it.
python -m predict_rx.eval.run --features data/processed/features_setB.parquet --model-dir artifacts/challengers/TABULAR-AONLY-01 --split holdout --authorized-by "Taskin" --authorize-dataset-b "Taskin authorizes this one-time frozen challenger Dataset B evaluation"

# A-only failure simulation after a locked patient list is available.
python -m predict_rx.eval.trustgate --raw-dir data/raw/training_setA --patient-list configs/locked_robustness_patients.txt --model artifacts/models/run4_frozen/model.joblib --out artifacts/experiments/TRUSTGATE-ROBUSTNESS-01.json

# Locked Dataset A internal comparison. Never reads Dataset B.
python -m predict_rx.eval.compare_internal --features data/processed/features_setA.parquet --challenger artifacts/challengers/TABULAR-AONLY-01 --anchor artifacts/models/run4_frozen --out artifacts/experiments/COMPARE-INTERNAL-01

# TrustGate cohort test at matched sensitivity / alert budget (Dataset A validation).
python -m predict_rx.robustness.trustgate_cohort

# Low-resource (no-lab) fallback: A-only search + refit, locked test untouched.
python -m predict_rx.train.fallback

# GRAPH-HAZARD-01 (needs the CUDA torch build). Ablation ladder, 7 models x 5 folds,
# ~2-3 h on an RTX 4050. Resumable: rerun the same command after an interruption.
python -m predict_rx.temporal.cv
# Refit the selected temporal model (or Run 4 fusion) on train, calibrate on val.
python -m predict_rx.temporal.final
# Second and final locked Dataset A test use (authorized, ledger LOCKED-TEST-REUSE-01).
python -m predict_rx.eval.compare_final

# RESIDUAL-HAZARD-01: Dataset A development only. Nested cross-fitting makes
# this substantially slower; rerun the identical command to resume.
python -m predict_rx.residual_hazard.cv 2>&1 | tee artifacts/residual_hazard_cv.log

# Completed once: final-fit and freeze the selected healthy-residual candidate.
# Do not rerun; the frozen artifact already exists.
python -m predict_rx.residual_hazard.final
python -m predict_rx.train.freeze --model-dir artifacts/challengers/RESIDUAL-HAZARD-01/final

# Completed once and rejected. Never rerun or retune after this result.
python -m predict_rx.residual_hazard.compare_setb --authorized-by "Tanvir Ahmed" --authorize-dataset-b "Tanvir Ahmed authorizes RESIDUAL-HAZARD-SETB-01 one-time frozen candidate comparison"
```

## Design notes

- Patient-level splits only
- Dataset B cannot be used for feature, model, threshold, calibration, or architecture selection
- Fit preprocessing and pseudo-site discovery inside development folds
- Frozen Run 4 remains the primary evidence model unless a challenger passes preregistered gates
- The current model output is a Challenge-compatible early-warning score, not a pure incident-hazard probability
- Incident 1/3/6/12-hour targets censor post-onset rows
- `vitals_only` is a separately selected low-resource family, not an untested subset of the frozen model
- Temporal and Graph-Hazard challengers fail closed until baseline, audit, and optimized-tabular evidence exists

## Data status (2026-09-30)

- Raw PSV present: 20,336 Dataset A and 20,000 Dataset B patients; a random
  300-file sample matches `data/checksums/raw_sha256.txt`
- The previous `features_setA/B.parquet` files were truncated (no Parquet
  footer); they are preserved in `data/processed/corrupt_backup_20260930/`
- `features.build` now streams row groups to `<out>.partial` and renames
  atomically, refuses to overwrite a valid file without `--overwrite`, and
  refuses to change a recorded `*.splits.json`
- Rebuilt Dataset A: 790,215 rows, 677 columns; train/val/test =
  14,235 / 3,050 / 3,051 patients, identical to Run 4
- Frozen Run 4 on the rebuilt internal test: AUROC 0.821337, AUPRC 0.109283,
  high-risk utility 0.243849 (historical: identical utility, ranking metrics
  within 4e-7)

## Evidence status (2026-10-14)

- Data/target audit: clean (`artifacts/experiments/data_target_audit_20260929T204835Z/`)
- Baselines on Dataset B: Run 4 passed the preregistered release rule against
  clinical-rule and logistic baselines (`artifacts/experiments/baselines_setb_20260929T205614Z/`)
- TABULAR-AONLY-01: 36 trials completed; the selected LightGBM lost to Run 4 on
  the locked internal test and was rejected
  (`artifacts/experiments/compare_internal_TABULAR-AONLY-01/`). The freeze and
  Dataset B challenger commands above are therefore **not** to be run for it
- Challenger gate: passed (`artifacts/governance/challenger_gate.json`)
- The Dataset A internal test has now been used for the tabular comparison. One
  more, final use is authorized for the GRAPH-HAZARD-01 challenger only
- TRUSTGATE-COHORT-01: at matched sensitivity the false-alert benefit crosses
  zero (−0.091 to +0.004 per 100 h), so it is not established
- LOWRES-FALLBACK-01: no-lab model, CV utility 0.369; retained as a candidate,
  not deployed
- GRAPH-HAZARD-01: 7 temporal models; TCN was best (CV utility 0.387 against
  the tree's 0.413). The Run 4 + TCN fusion gained AUPRC on the locked test
  (0.117 against 0.109) but not utility (0.243 against 0.244), so it was rejected
  (`artifacts/experiments/compare_final_GRAPH-HAZARD-01/`)
- The Dataset A internal test is now closed for model selection (used twice)
- RESIDUAL-HAZARD-01 completed on Dataset A train+validation only. The selected
  healthy-reference residual candidate improved CV utility from 0.3986 to
  0.4073 and passed its development gate. The combined feature stack failed
  its gate; the nested 1/3/6/12-hour hazard stack increased AUPRC but reduced
  utility by 0.0082 and was rejected. EMA passed the separate development
  policy gate. The selected candidate was final-fit and frozen as
  `residual-healthy-ema-202610141727` (SHA-256
  `7c430b30e66c882a4ddf467a8adbea1c403730f8c9f733f0d4d464b95e6ef33b`).
  Its one-time Dataset B comparison failed every preregistered check
  (candidate utility 0.109 against Run 4 utility 0.238), so it is rejected and
  frozen Run 4 remains primary. Do not rerun or retune it
