# TrustGate — layer-by-layer

Status: product documentation for the live reliability policy in
`backend/app/trustgate.py`. TrustGate does **not** change the frozen Run 4
probability. It decides whether that probability is safe enough to interrupt a
clinician, needs data verification, or should stay silent.

Live UI: ICU board Trust badges, patient chart, `/alerts`, `/handoff`,
`/presentation`. API field: every prediction carries `trustgate`.

## States (what you see)

| State | Meaning | Interruptive alert? |
|---|---|---|
| `alert` | Score cleared every gate; high-risk band | Yes (when site mode allows) |
| `watch` | Elevated but below interrupt policy / unstable | No |
| `verify_data` | Required vitals stale or incomplete — fix the feed first | No |
| `abstain` | History too short, severe shift, or unsafe to speak | No |

## Layer stack (bottom → top)

### Layer 0 — Frozen model score
- Input: past-only features for the encounter hour.
- Output: calibrated probability + risk band (`stable` / `watch` / `high_risk` / `insufficient_data`).
- TrustGate never edits this number.

### Layer 1 — Minimum history
- If probability is `null` (not enough hours / features): **`abstain`**
  reason `minimum_history_not_met`.

### Layer 2 — Required-vital freshness (availability shift)
- Required signals: **HR, SBP, MAP, O2Sat**.
- `input_shift_score` = transparent mix of missing + >2 h stale fractions
  (not a learned OOD model).
- If any required vital is **>12 h** old → **`abstain`**
  (`required_vitals_over_12h_old`).
- If shift ≥ 0.8 → **`abstain`** (`severe_required_vital_shift`).
- If milder gaps / stale vitals → **`verify_data`**
  (chart the missing cells — see Missing-signal matrix next steps).

### Layer 3 — Perturbation stability
- Small input perturbations are rescored; if the high-risk *decision* flips
  too often, TrustGate refuses interruptive **`alert`** and stays on **`watch`**
  (reason around alert instability).
- `alert_stability` and `perturbation_max_delta` are logged on the prediction.

### Layer 4 — Risk band × TrustGate
- Only when state would be interruptive **and** probability ≥ high-risk
  threshold does TrustGate emit state **`alert`**.
- Engine only raises an open interruptive alert when TrustGate state is `alert`
  and site mode allows interrupts (`demo` / authorized `live`).

### Layer 5 — Site / Transfer Shield (outside TrustGate module, same safety story)
- Silent pilot + readiness gates (incl. **S6 habit fingerprint**) must pass
  before live interrupts on real encounters.
- Quarantine / mapping (S2) happens *before* scoring — bad codes never reach
  TrustGate.
- Clinical context (S8) can modulate presentation; it does not rewrite probability.

## How clinicians should read it

1. **Alert + open banner** → review the patient; one-tap **Seen** or **Quiet 1h**
   on the ICU board; full dismiss still needs a reason on the patient/alerts page.
2. **Verify data** → open Missing-signal matrix; chart or fix the feed for the
   red/empty required cells; score may still show but will not interrupt.
3. **Abstain** → do not treat the number as actionable; fix data or wait for history.
4. **Watch** → elevated; keep monitoring; not an interrupt.

## API / code map

| Piece | Path |
|---|---|
| Policy | `backend/app/trustgate.py` → `assess_prediction` |
| Applied each score | `backend/app/services/engine.py` |
| Offline twin | `ml/src/predict_rx/eval/trustgate.py` |
| Badge UI | `frontend/components/RiskBadge.tsx` |

## What TrustGate is *not*

- Not a second sepsis model.
- Not an EHR write-back / order API.
- Not a guarantee of clinical correctness — local silent evaluation and
  governance remain mandatory before live use.
