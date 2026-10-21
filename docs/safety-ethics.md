# Safety & ethics — PredictRx Sentinel

Aligned with WHO AI-health principles: autonomy, safety, transparency, accountability, equity, sustainability.

## Safeguards shipped in V1

1. Persistent disclaimer: research prototype, not clinical use  
2. Human acknowledgement / dismiss / escalate for every alert  
3. No treatment generation, no automated clinical action  
4. Calibrated score + per-signal freshness + transparent TrustGate state  
5. `Verify data` or `Abstain` instead of a confident alarm when reliability checks fail  
6. SQL-backed append-only, hash-chained audit events and restart snapshots  
7. Signed JWT role guards (clinician / nurse / admin / metadata-only operator / integration); demo headers only in demo mode  
8. Pseudonymous demo records only  
9. Unit/range validation, quarantine, unknown-code auditing, and encounter isolation  
10. No raw dataset in Git; versioned model + preprocessing and frozen-artifact hashes  
11. Model card + data card + known limitations  
12. Domain-shift notice: US training ≠ Bangladesh validity  
13. TreeSHAP model influence separated from curated, non-causal clinical context  
14. Watch is passive; only a TrustGate-passed High Risk state can interrupt  
15. Physician-documented patient context (`clinical-context/v1`) around the frozen model  
16. Patient-free, HMAC-signed fleet heartbeat; the vendor console rejects any non-allowlisted field  

## Patient context the model cannot see

The model learned population patterns from about 40,000 US ICU stays. It has
no input for chronic disease, goals of care, pregnancy, immunosuppression or a
rare diagnosis. A doctor or hospital admin documents these on the bedside chart.
The probability is never changed; a fixed, versioned policy acts after scoring:

| Context | Effect | Why |
|---|---|---|
| CKD/dialysis, chronic liver disease, chronic respiratory failure, haematological malignancy | Drivers such as creatinine, bilirubin, SpO2 or counts are labelled "may be chronic baseline" | Prevents misreading a chronic value as new deterioration. The alert is **not** suppressed: acute-on-chronic illness is common. |
| Immunosuppression, rate control (beta-blocker, pacemaker) | Warning that a low score may be falsely reassuring | Fever, leukocytosis and tachycardia may not appear, so the model may under-call. |
| Pregnancy or within 6 weeks postpartum | Alerts become shadow-only | Outside the validated population; the obstetric early-warning pathway applies. |
| Comfort-focused care | Alerts become shadow-only; open alerts are superseded | Interruptions must match documented goals of care. |
| Limited escalation | Alerts continue, with a ceiling-of-care reminder | The team still needs to know; the response is theirs to align. |
| Other condition not in the model | Caution plus a subgroup flag | Rare or undiagnosed disease is recorded for subgroup evaluation, not guessed. |

Safeguards: nurses can view but not set context; the platform operator cannot
read it; each change is audit-logged with reason and author; every entry has a
review deadline (1–168 hours) after which any suppression lapses and standard
alerting resumes; context codes are stored with every prediction record so
local validation can report performance per subgroup. Whether any future model
should use these signals is decided offline, by validation, never by live
retraining.

The displayed zero spread from the frozen single-member model is not a
validated confidence interval and is not used to gate alerts. The current
`input_shift_score` is an interpretable required-vital availability proxy, not
a learned out-of-distribution probability.

TLS termination, managed key storage, penetration testing, multi-worker
coordination, and disaster recovery depend on the eventual deployment
environment and are not claimed as shipped.

## Post-hackathon hospital path

1. Ethics / DUA / institutional approval  
2. Map local EHR → observation schema  
3. Retrospective local validation  
4. Recalibrate thresholds only under a prespecified local protocol (do not blindly retrain)  
5. Silent mode 4–8 weeks  
6. Controlled prospective pilot  
7. Regulatory / institutional clearance before clinical use  

## Sepsis definition

Labels and clinical framing follow Sepsis-3 concepts as used by the PhysioNet challenge. Product copy must not claim bedside diagnosis.

The frozen model predicts the Challenge-compatible label view, which becomes
positive six hours before defined onset and stays positive afterward. It is
not an exact incident six-hour hazard probability. Separate incident 1/3/6/12
hour target builders censor post-onset rows; the incident targets are built
and audited but no challenger trained on them has been validated yet.

## Current evidence limits

- Dataset B wording: **Site-held-out retrospective validation on a
  geographically distinct public hospital cohort.**
- No prospective validation, Bangladesh validation, clinical outcome
  improvement, prevented-sepsis, or mortality claim.
- Run 4 beat clinical-rule and logistic baselines on Dataset B in a
  preregistered one-time comparison, but its calibration slope there is 0.80;
  local recalibration is required.
- Most predictive signal comes from measurement-pattern (care-process)
  features, which are hospital-specific. This is a transfer risk, not a
  clinical insight.
- TrustGate failure simulation on 500 Dataset A validation patients shows zero
  alert flips from duplicate, late, or out-of-order data; no claim is made that
  TrustGate reduces clinical harm.
- The current Hospital Readiness Passport recommends **Retrospective
  validation**, not deployment.
