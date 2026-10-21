# PredictRx Sentinel — production operating model

## The decision

PredictRx will be sold as an **ICU workflow, data-quality and governed
evaluation product that connects to the hospital's existing systems**. It is
not a replacement HIS/EHR and it is not an autonomous sepsis-treatment system.

The target architecture is hybrid:

- a **hospital data plane** runs once per hospital (or hospital group) and
  contains identifiable patients, encounters, observations, predictions,
  users and audit records;
- a future **PredictRx control plane** contains tenant directory, deployment
  version, licence, non-PHI health telemetry, connector status and support
  tickets;
- the hospital data plane initiates an outbound encrypted connection to the
  control plane. No patient observations, names, MRNs or prediction details
  leave the hospital unless a separate, explicit agreement permits a defined
  export.

The current repository implements the hospital data plane. It is single-site,
not multi-tenant. A founder control plane and platform-super-admin account are
not implemented yet.

## Who signs in where

### PredictRx platform operator

The founder/support team will sign in to the future control plane to:

- create and suspend a hospital tenant;
- issue a one-time site-enrolment token;
- see deployed version, backup/health heartbeat and connector failures;
- manage licence/support status and signed software releases;
- request time-limited support access.

Platform administration must not grant unrestricted access to patient records.
Exceptional support access requires hospital approval, a reason, expiry,
least-privilege scope and an immutable audit event.

### Hospital administrator

The first site administrator is bootstrapped during installation. That
administrator signs in to the hospital-local URL and:

- changes the temporary password and enables TOTP;
- creates named staff accounts and assigns role/unit scope;
- configures ICU/ward units and verifies bed identifiers;
- approves connector mappings and reviews quarantine/feed health;
- disables or removes staff and resets credentials.

### Clinical and integration identities

- Doctors and nurses use named accounts, hospital OIDC/SSO where available, or
  local password + optional TOTP. A personal short-lived PIN may unlock a
  shared hospital-managed tablet.
- Connectors never use a staff password. Each feed receives its own scoped,
  revocable integration key.

## How patients appear

PredictRx never searches the internet for patients and never invents an
identity. A patient appears through one of these approved routes:

1. the HIS/EHR sends admission/transfer/discharge and identifiers;
2. an authorised user admits/transfers/discharges the encounter in the bedside
   chart;
3. an approved retrospective file creates encounters for evaluation.

Names are display-only. Matching uses the hospital's patient namespace plus
encounter/visit ID. Unknown or ambiguous identities are quarantined rather
than guessed.

## Integration ladder

Use the highest available rung; lower rungs remain supported fallbacks.

1. **FHIR R4 / Bangladesh Core FHIR** — preferred when the HIS exposes an
   authorised API. Use Encounter and Observation profiles and LOINC-coded
   laboratory results. The Bangladesh guide is currently trial-use and still
   has documented transaction/search gaps, so vendor testing remains required.
2. **HL7 v2 through an interface engine** — ADT for encounters and ORU for
   observations. A hospital-specific mapping profile is still required.
3. **Central monitor gateway** — receive the monitor vendor's authorised HL7
   IHE PCD/ORU feed through the durable on-site MLLP relay. Do not scrape a
   bedside screen or bypass vendor/network controls.
4. **Scheduled CSV/file exchange** — valid for retrospective validation,
   laboratory batch import, commissioning and approved low-frequency
   workflows. It is not equivalent to a reliable real-time feed.
5. **Manual bedside charting** — valid for paper-first sites and downtime, with
   offline store-and-forward and later reconciliation.

There is no safe universal plug-and-play connector. Standards define the
envelope, but each source still has local codes, units, timestamps, correction
rules, encounter identifiers and sometimes paid interface licences.

## What the model receives

The frozen ICU model's source contract contains:

- vitals: HR, SpO2, temperature, SBP, MAP, DBP, respiratory rate and EtCO2;
- laboratories/respiratory variables: base excess, bicarbonate, FiO2, pH,
  PaCO2, SaO2, AST, BUN, ALP, calcium, chloride, creatinine, direct/total
  bilirubin, glucose, lactate, magnesium, phosphate, potassium, troponin I,
  haematocrit, haemoglobin, PTT, WBC, fibrinogen and platelets;
- context: age, sex/unit context, hospital-admission offset and ICU length of
  stay.

The connector maps source observations into this canonical contract, converts
approved units, retains provenance and quarantines unknown codes. The engine
builds past-only trends, missingness and freshness features over a 24-hour
window. It needs at least four observed ICU hours before scoring and updates
when a new source hour arrives. Vitals are carried forward for at most two
hours and labs for at most 24 hours; missing values remain explicit. TrustGate
requires fresh HR, SBP, MAP and SpO2 before an interruptive alert can qualify.

Missing every possible lab does not trigger automatic fabrication. It produces
weaker data quality, Verify data or Abstain. The current frozen model is not a
separately validated vitals-only model.

## Training and hospital data

Predictions and training are separate:

- deployment uses the same frozen, versioned model at every site;
- the model does not retrain before each prediction or learn from clicks;
- a hospital's data is not owned by PredictRx merely because the software
  processed it;
- any de-identified research export, model development or cross-site training
  needs a separate purpose, agreement, ethics/legal determination and test
  plan;
- a future model is trained offline, independently validated, versioned and
  approved before deployment. It never silently replaces the current model.

## If there are no partner data or 28 days before a deadline

Three deliverables are still honest and sellable:

1. **Congress/product demonstration** — synthetic and held-out replay,
   integration simulator and security/admin workflow.
2. **Paid readiness and commissioning** — source inventory, network/deployment
   setup, mapping workshop, synthetic acceptance tests and staff training.
3. **Workflow/research installation** — flowsheet, ADT, handoff, feed quality,
   audit and retrospective imports, with model scores silent.

A 24–72 hour synthetic commissioning can prove that software and routes work.
It cannot prove local clinical validity. A 28-day silent period is calendar
observation at the hospital, not 28 days of founder attendance; the system
runs while dashboards collect feed and workflow evidence.

Until local validation and governance are complete, proposals must say
“research/workflow evaluation” and must not claim live sepsis detection,
clinical effectiveness or approval.

## Product build sequence

### Release A — repeatable single-hospital package

- signed installer/config bundle and one-time admin bootstrap;
- site-enrolment manifest, environment validation and upgrade/rollback;
- bed/unit import and ADT correction queue; the generic HL7 A01/A02/A03
  contract is implemented, while each partner's PID/PV1 profile still needs
  conformance sign-off;
- Bangladesh Core FHIR compatibility profile and conformance fixtures;
- mapping wizard with sample-message replay and acceptance report;
- backup/restore, downtime and security evidence export.

### Release B — metadata-only control plane

- tenant/site directory, operator authentication and strict platform roles;
- enrolment token and certificate rotation;
- non-PHI heartbeat, version, capacity, connector-state and incident telemetry;
- signed-release channel and update approval;
- hospital-approved, expiring support tunnel with full audit.

### Release C — vendor packs

- reusable, versioned mapping packs for actual HIS/LIS/monitor vendors;
- conformance test suites and sample-message fixtures supplied with permission;
- SMART App Launch/CDS Hooks only where the partner EHR supports them;
- FHIR Bulk Data export client for authorised retrospective validation.

### Release D — clinical evidence path

- local retrospective report;
- silent prospective observation and adjudication;
- security/regulatory/ethics decisions;
- locked model/version and rollback plan;
- only then, a separately authorised live decision-support release.

## Founder sales flow

1. Sell a fixed-scope readiness assessment, not “AI replaces the ICU.”
2. Inventory HIS/EHR, LIS, central monitors, interfaces, codes, units and
   responsible owners.
3. Demonstrate with synthetic data and agree one ICU plus one bounded source.
4. Quote connector/setup separately from recurring workflow/support.
5. Install the hospital data plane and commission without live alerts.
6. Leave the silent system running; review evidence remotely through approved
   non-PHI telemetry and scheduled governance meetings.
7. Convert to a workflow/research subscription if operational value is shown.
8. Treat clinical alerting as a later regulated/evidence milestone, not a
   promise attached to the first sale.

