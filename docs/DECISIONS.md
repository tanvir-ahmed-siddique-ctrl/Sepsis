# PredictRx Sentinel — Locked Decisions

Last updated: 2026-09-30

## Product

| Decision | Choice |
|---|---|
| Challenge | PredictRx (HealthSphere AI) |
| Frozen-model target | PhysioNet Challenge-compatible early-warning label; not an exact incident six-hour hazard |
| Challenger targets | Incident onset within 1 / 3 / 6 / 12 hours, post-onset rows censored |
| Product type | Clinical decision support (not diagnosis/treatment) |
| Platform | ICU web dashboard + hospital integration API |
| Congress Day goal | Retrospectively validated, pilot-ready research prototype |

## Scope cuts (V1 vs stretch)

| Item | V1 | Stretch |
|---|---|---|
| Primary model | Frozen LightGBM until preregistered evidence promotes a challenger | GRU-D/TCN/sparse-event and Graph-Hazard only after evidence gates |
| Input format | Normalized JSON observations | Limited FHIR R4 bundle |
| Explainability | Grouped TreeSHAP + versioned non-causal evidence graph | Curated expansion after clinical review |
| Reliability | TrustGate + failure simulator + readiness passport | Cohort-validated shift model after genuine data return |
| Experiment tracking | Append-only ledger + immutable JSON/SQLite bundles | Remote registry only if needed |
| Persistence | SQLite local/offline; PostgreSQL through DATABASE_URL | Managed multi-node HA |
| Live hospital data | No — demo replay of held-out PhysioNet cases | Post-congress silent pilot |
| MIMIC-IV | Not required for V1 | External validation later |

## Why these cuts

- LightGBM on structured ICU features is strong, fast on CPU, and easier to explain/demo than deep sequence models.
- FHIR and RAG are valuable for scoring (scalability / ethics) but must not block a working end-to-end demo.
- MIMIC credentialing would stall the foundation week; PhysioNet Challenge 2019 is enough for a credible held-out story.

## Non-negotiables (never cut)

- Research-prototype disclaimer on every screen
- Human acknowledgement for alerts (no autonomous action)
- Patient-level train/val/test splits (no leakage)
- Calibration + explicitly named model disagreement + per-signal freshness display
- Model card, data card, audit log
- Explicit domain-shift limitation (US training ≠ Bangladesh validity)
- Dataset B never used for model/feature/threshold/calibration selection
- Fragile High Risk scores become Verify data or Abstain, not confident alarms

## Success definition (Congress Day)

1. Frozen reproducible model + honest Dataset B metrics
2. Working ICU dashboard with patient replay
3. Explainable calibrated predictions + alert workflow
4. Safety docs + business model + 3-minute pitch
5. Offline Docker path; direct public deployment is tracked separately
