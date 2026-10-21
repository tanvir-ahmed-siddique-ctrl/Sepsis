# PredictRx Sentinel — adoption plan

This is a hospital/ICU SafeLaunch offer, not a consumer product.

## Customer and buyer

- Customer: hospital, ICU, or quality programme
- Users: ICU clinicians and charge nurses
- Not sold to patients and never used for autonomous patient contact

## Offer

1. **SafeLaunch retrospective / silent validation** (4–8 weeks): schema/unit mapping, Hospital Readiness Passport, threshold review, no interruptive alerts.
2. **Controlled pilot** only if the passport recommends it and local ethics/data-use approval exists.
3. **Subscription** for monitoring, model-version rollback, and audit export after a silent period.

Pricing remains an unvalidated hypothesis in `docs/product-brief.md`.

## How the software enforces the SafeLaunch sequence

- The site starts in `silent` mode (`docker-compose.site.yml`). Bedside staff
  cannot see API-patient risk; alerts are recorded as shadow alerts.
- Admins adjudicate outcomes and collect clinician feedback on the Pilot page.
- A request for live mode is downgraded to `live-disabled` until every
  readiness gate passes, including recorded governance / ethics sign-off.
- Gate thresholds and their rationale are in
  [operations](operations.md#silent-pilot-readiness-gates). They are starting
  points for the local committee, not validated cut-offs.

## Bangladesh / LMIC path

- CPU/on-prem/offline inference is the default
- `vitals_only` is a separately validated fallback family, not a silent subset of the frozen 673-feature model
- Performance without labs must be measured before claiming lab-free deployment
- Clinician-facing copy can switch to Bangla in the dashboard; this is localization, not local clinical validity
- No Bangladesh-validity claim without local retrospective data

## NRB / local collaboration

Seek a named ICU clinician, clinical informatician, biostatistician, or responsible-AI advisor. Record what they reviewed. Do not imply endorsement without written evidence.

Current status: no written advisor review is on file.

## Expansion

AKI, respiratory deterioration, and other complications reuse the observation, TrustGate, and passport platform only after the sepsis evidence remains stable.
