# Build schedule — PredictRx Sentinel

Today: **2026-09-30**. Congress Day is 2026-12-26. Preliminary video/slides are owned by the team, not this codebase.

| Window | Focus | Status / exit criteria |
|---|---|---|
| Sep 26–30 | Foundation + evidence integrity | Done: frozen SHA preserved, data rebuilt, audit, Dataset B baselines with CIs, tabular challenger rejected, TrustGate cohort test (benefit not established), no-lab fallback candidate |
| Sep 30 | GRAPH-HAZARD-01 ladder | Done: TCN best temporal model; fusion rejected on the locked test (utility −0.001); no Dataset B request |
| Oct 1–15 | External data (optional) | eICU credentialing + demo-based conversion pipeline; A+B training with eICU as external test |
| Oct 16–31 | Preliminary-ready demo | Replay, TrustGate banners, passport, model card, Bangla clinician copy |
| Nov | Reliability evidence | TrustGate V2 policy tuned on data other than TRUSTGATE-COHORT-01; fallback in backend if still useful |
| Dec 1–18 | Hardening | Passport update, Docker backup, claim review |
| Dec 19–25 | Congress prep | Offline demo, frozen artefacts |
| Dec 26 | Live demo | Held-out replay + honest metrics |

## Immediate next actions for the team

1. Apply for eICU credentialed access and download the open eICU demo
2. Keep video, slides, and public deploy outside the engineering pass
