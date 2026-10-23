# Frontend how-to (founder / demo operator)

Short map of what to click. Details for TrustGate: `docs/trustgate-layers.md`.
Commercial/legal EHR path: `docs/business/ehr-partnership-and-commercial-strategy.md`.

## Connection Ladder & Integration Hub

| Want | Go to | Do |
|---|---|---|
| See L0–U2 story | `/connection` | Live soft-landing / habit / SMART status when signed in |
| CSV / HL7 / Vendor Adapter / habit baseline | `/integration` (admin) | Upload files; record S6 baseline; toggle L5 soft-landing |
| SMART / CDS sandbox | `/v1/ehr/smart/metadata`, `/v1/ehr/cds-services` | Standards surfaces — not Epic Showroom listing |

## Missing-signal matrix

Patient chart → **Missing-signal matrix**. Empty required cells → follow **What to do next** (chart / fix feed / Hub).
TrustGate will not interrupt until freshness recovers. Fixing feeds is a **paid service SKU** (see business model §3b).

## Feedback

1. Patient page → bedside workflow → submit usefulness.
2. Stored in DB (`feedback_records`).
3. See rows: **Silent pilot → Clinician feedback inbox**.
4. Aggregates also on pilot metrics; included in pseudonymised export.

## Alerts under emergency load

ICU board card with open alert → **Seen** or **Quiet 1h** (no need to open the patient first).
Full dismiss with reason remains on patient / `/alerts`. Voice is optional later — not required for Dec.

## Shift roster

Nav strip shows who is on the *current* shift. Edit: `/admin/shift-roster` (CSV or manual). Not payroll attendance.

## Mapping copilot

Integration Hub bottom panel — suggests LOINC/target for local lab codes. Proposal only.

## Hospital database connection

PredictRx does **not** write into the HIS DB. Hospital connects *out* to us via CSV drop, HL7, FHIR, or Vendor Adapter JSON on the hospital LAN (on-prem install). Soft-landing = we are the ICU UI; HIS keeps billing/ADT.
