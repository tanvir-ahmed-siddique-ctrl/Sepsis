# Data Protection Impact Assessment — PredictRx Sentinel (site deployment)

Template completed for the product as designed; the installing hospital's
data-protection owner reviews, adapts and signs it before go-live (sign-off
block left blank deliberately). Framing follows Bangladesh's Personal Data
Protection Ordinance 2025 as referenced in `docs/operator-guide.md`: the
hospital is the data controller; the vendor is not a holder of patient data.

## 1. What is processed, where, and why

| Data | Where it lives | Purpose | Leaves the hospital? |
|---|---|---|---|
| ICU observations (vitals, labs, timestamps, bed/encounter identifiers) | Hospital server's site database only | Risk scoring, TrustGate data-quality states, clinician display | No |
| Predictions, explanations, TrustGate states | Site database | Decision support display; silent-pilot evaluation | No |
| Alert actions (acknowledge/dismiss/escalate + reason) | Site database, hash-chained audit | Accountability, KPI measurement | No |
| Staff accounts, roles, unit assignments | Site database | Access control | No |
| Clinician-documented patient context (e.g. pregnancy, comfort care) | Site database | Alerting policy modulation; audited, time-limited | No |
| Fleet heartbeat (versions, model hash, gate status, counts) | Vendor fleet console | Fleet safety/operations monitoring | **Yes — metadata only**: HMAC-signed, allowlisted fields; the console rejects non-allowlisted fields |
| Backups | Hospital-controlled media (3-2-1, `infra/backup.sh`) | Recovery | Only where the hospital puts them; vendor holds none |

No patient data is processed on the public demo stack: it contains only
de-identified PhysioNet 2019 replay records (CC BY 4.0) and labelled
synthetic commissioning feeds.

## 2. Necessity and proportionality

- Scoring needs bedside observations; it does not need names for the model.
  Display identifiers exist for clinical workflow and are access-controlled
  by role and unit scope.
- The vendor's operational need (is the site up, on the right model, with
  gates passing?) is fully met by the metadata heartbeat; that is why the
  architecture makes patient-data transfer to the vendor impossible rather
  than merely contractual.
- The metadata-only `operator` role is technically refused every patient
  route (verified by `infra/judge_e2e_check.py`, 50/50 checks on the public
  deployment, 2026-10-23).

## 3. Principal risks and mitigations

| Risk | Mitigation in the product | Residual / owner |
|---|---|---|
| Insider misuse of patient views | Role + unit scopes; every action in a hash-chained audit; access reviews are the hospital's duty | Hospital admin reviews audit routinely |
| Vendor-side breach exposing patients | Vendor holds no patient data; fleet heartbeat is signed, allowlisted, patient-free | Fleet console compromise exposes operations metadata only |
| One hospital's breach affecting others | Per-hospital isolated data plane; no shared patient database | By design; a site incident is contained to that site |
| Model silently changed or re-fit | Frozen artefact; SHA-256 verified at start-up; no training code path in production | Server-admin access control is the hospital's duty |
| Audit tampering | Hash chain + recorded audit head in every backup; `verify-audit` in ops tooling | Hospital alerts if chain verification fails |
| Scores presented on bad data | Quarantine for unknown codes/units and implausible values; `Verify data`/`Abstain` states; nine readiness gates before interruptive alerts | Residual clinical risk owned by site governance |
| Retention beyond need | Backups under hospital control; decommissioning erases site data and issues a certificate (`ops_cli decommission`) | Retention schedule itself is set by hospital policy — record it here at install: ______ |

## 4. Data-subject and patient rights

Requests (access, correction, erasure) are the hospital-controller's duty
under its own policies; the product supports them through role-scoped
patient views, the audit trail, pseudonymised pilot exports, and certified
erasure at offboarding. PredictRx staff have no standing access: vendor
support occurs only in a hospital-opened, logged session
(`docs/operator-guide.md` §8).

## 5. Cross-border and sub-processor position

A standard site deployment has no cross-border patient-data flow: the data
plane is the hospital's own server. The optional mapping-copilot LLM is
on-premises by default; an external LLM endpoint is refused outside demo
mode unless the hospital sets `COPILOT_EXTERNAL_LLM_APPROVED=true`, and even
then only field names and units — never patient values — are sent. If a
hospital enables that option, the hospital records the provider as its own
sub-processor decision here: ______ (provider, date, approver).

## 6. Review triggers

Re-run this assessment when: a new data source is connected; the copilot
LLM option is enabled; the fleet heartbeat field list changes (allowlist
change requires updating both the sender and the console, and this DPIA);
a new model version is evaluated; or an incident occurs.

## Sign-off (completed by the hospital at install)

| Role | Name | Signature | Date |
|---|---|---|---|
| Hospital data-protection owner | | | |
| Clinical safety owner | | | |
| IT/security owner | | | |
| Vendor representative (design facts only) | | | |
