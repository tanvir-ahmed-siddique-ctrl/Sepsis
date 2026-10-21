# Data card — PhysioNet 2019 Sepsis Challenge

## Dataset

- **Name:** Early Prediction of Sepsis from Clinical Data — PhysioNet Computing in Cardiology Challenge 2019  
- **URL:** https://physionet.org/content/challenge-2019/1.0.0/  
- **License:** CC BY 4.0  
- **Approx. size:** ~40,000 ICU stays, hourly records  

## Intended use for PredictRx Sentinel

Train and retrospectively validate an adult ICU early-warning research model
using the official Challenge-compatible label view. The label becomes positive
six hours before defined onset and stays positive afterward; it is not a pure
incident six-hour target.

## Population

- Adult ICU patients from contributing hospitals in the challenge  
- Labels aligned with challenge / Sepsis-3-oriented onset definition  

## Out of scope

- Pediatrics, neonates, maternity, outpatients  
- Identifiable patient data  
- Bangladesh clinical validity claims  

## Splits (locked approach)

| Split | Patients | Septic patients | Role |
|---|---|---|---|
| Dataset A — train (70%) | 14,235 | 1,259 (8.8%) | Fit models; 10% of these patients held back for early stopping |
| Dataset A — validation (15%) | 3,050 | 246 (8.1%) | Choose hyperparameters, fit isotonic calibration, set thresholds |
| Dataset A — internal test (15%) | 3,051 | 285 (9.3%) | Compare training runs and baselines |
| Dataset B — site-held-out public cohort | 19,978 | 1,140 (5.7%) | Geographically distinct public Challenge training set B; frozen model scored once |

Splits are **patient-level** (seed 42). No patient appears in more than one split.  
Patients younger than 18 are excluded. Dataset B was evaluated **only after model freeze** (2026-09-28).  
Hourly rows: 790,215 in Dataset A, 761,246 in Dataset B.

## Variables (illustrative)

Hourly vitals and labs including HR, BP, Resp, Temp, SpO2, WBC, lactate, creatinine, BUN, platelets, bilirubin, and related missingness indicators. Exact feature list is frozen in `ml/src/predict_rx/features/schema.py`.

## Known limitations

- US-centric training distribution ≠ Bangladesh ICUs  
- Missingness patterns differ by hospital; the model relies partly on measurement-frequency features  
- Sepsis is rarer in Dataset B (1.4% of hours vs 2.4% in the Dataset A test split), which lowers AUPRC there  
- No GCS or vasopressor data, so SOFA-lite has no neurological component and a MAP-only cardiovascular component  
- `SepsisLabel` is used for reproducible Challenge-compatible evaluation, but ordinary row-level metrics include post-onset positive hours  
- Separate incident-onset targets for 1/3/6/12 hours censor post-onset rows and are not interchangeable with the historical target  
- Challenge labels are research constructs, not bedside diagnoses  
- Class imbalance is severe; utility / AUPRC matter more than accuracy  

## Handling rules

- Raw data never committed to Git  
- Checksums recorded under `ml/data/checksums/`  
- Preprocessing fit on training fold only  
- Forward-fill only within clinically defined limits  

## Local workspace status

The current files named `features_setA.parquet` and
`features_setB.parquet` are invalid placeholders without Parquet magic bytes,
and the raw PSV files are absent. Historical counts above come from the frozen
evidence/data card; they were not re-derived in this implementation session.
The audit and baseline commands fail closed until genuine data are supplied.

## Ethical notes

De-identified research data under PhysioNet terms. Demo UI uses pseudonymous replay IDs only.
