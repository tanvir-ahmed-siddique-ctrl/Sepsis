# Hospital onboarding and data operations

This runbook turns PredictRx Sentinel from a Congress demo into a governed,
on-premise hospital pilot. It does **not** authorize clinical use. Frozen Run 4
remains retrospective and ICU-only; live alerts require the readiness gates,
local validation, hospital governance and applicable regulatory review.

## 1. Name accountable owners

Before receiving patient data, record:

- clinical owner (ICU/medicine), nursing workflow owner and patient-safety lead;
- hospital data controller/privacy officer and ethics/IRB contact;
- HIS/EHR, LIS, network/security and biomedical-engineering owners;
- PredictRx deployment owner, incident contact and downtime decision-maker;
- approved purpose, legal basis/consent position, retention period and users.

Use a data-processing agreement and data-flow diagram approved by the hospital.
Keep identifiers, logs and backups in the hospital-controlled environment.

## 2. Choose the smallest reliable source

| Need | Preferred source | Alternative | PredictRx entry point |
|---|---|---|---|
| Admission, transfer, discharge | EHR/HIS HL7 ADT or FHIR Encounter | Bedside ADT form | HL7 ADT endpoint / Care API / Chart page |
| Demographics and encounter ID | EHR/HIS | Approved registration export | FHIR, HL7 or native API |
| Laboratory results | LIS interface | Controlled CSV export | HL7 ORU, FHIR Observation, CSV lab upload |
| Vitals from central monitor | Existing interface engine | On-site edge MLLP relay | HL7 ORU via edge service |
| Paper-chart vitals | Structured bedside entry | None | Offline-capable Chart page |

Do not connect directly to a bedside device if the hospital already has a
validated central monitoring or interface-engine feed. The hospital remains
the source of truth.

## 3. Identity and encounter contract

Every message needs a stable hospital patient identifier (usually MRN), a visit
or encounter identifier, source timestamp and unit. Names are display-only and
must never be used for matching.

Before go-live, the hospital must document:

1. issuer/namespace for MRNs and encounter IDs;
2. how duplicate MRNs, merged records and corrected encounters are reported;
3. bed/unit master-list IDs and transfer timing;
4. timezone, daylight-saving policy and clock synchronization;
5. late/corrected/cancelled result handling;
6. who resolves identity or unit mismatches.

Unknown identities and ambiguous encounters are quarantined. Staff must fix the
source or mapping; PredictRx must not guess.

## 4. Mapping and validation

Create a signed source-to-target sheet for every field:

`source system → source code → display → target code → source unit → canonical unit → allowed range → example → approver`

- Prefer LOINC for laboratory tests and documented IEEE 11073 MDC mappings for
  monitor measurements.
- Confirm at least ten representative real examples for every required signal.
- Test decimals, negative values, inequality results, missing units, corrected
  results, delayed messages, duplicates and out-of-order timestamps.
- Unknown codes, unsupported units and impossible values remain in quarantine.
- Mapping changes are versioned, reviewed and re-tested; they are not model
  changes.

## 5. Network and credentials

- Run PostgreSQL, API, frontend and edge relay on the hospital LAN.
- Terminate TLS at the hospital reverse proxy; do not expose PostgreSQL.
- Prefer OIDC/SSO. Otherwise create named local users with 2FA and minimum unit
  scope. Shared ward accounts are prohibited.
- Give each interface a separate hashed integration key with only the required
  ingest scope and unit list. Rotate it after commissioning and on staff/vendor
  changes.
- Allow outbound internet only if explicitly required by hospital policy;
  scoring itself is offline.

## 6. Pilot sequence

1. **Synthetic commissioning:** verify routes, mappings, quarantine and restart.
2. **Retrospective local validation:** ingest an approved historical extract;
   evaluate missingness, discrimination, calibration and subgroup limitations.
3. **Silent pilot:** 28+ days; clinicians are blinded; reconcile census,
   timestamps, outcomes, downtime and feed alarms.
4. **Governance review:** clinical, ethics/privacy, IT/security and executive
   owners review every readiness gate and incident.
5. **Live-disabled or live:** only the hospital can authorize progression.
   Failure of any gate keeps the system non-interruptive.

## 7. Daily operations

- Integration Hub: feed silence, lag, quarantine, duplicates and retry spool.
- Bedside chart: due observations, offline queue and 8-hour completeness.
- Ward board: complete NEWS2 inputs and overdue observations.
- Pilot page: adjudication, shadow-alert burden and readiness evidence.
- Operations: database/lease health, audit-chain verification, backup success,
  storage capacity and restore drills.

When a feed fails, use the hospital downtime process. Offline chart entries
must be reconciled after recovery; never silently create missing values.

## 8. User and data lifecycle

- Admins create, edit, disable, reset or remove login profiles. Role/unit
  changes revoke existing sessions. The final active administrator is
  protected. Removing a profile deletes credentials but retains the stable
  user ID in immutable audit history.
- Discharge closes an encounter; late observations are quarantined.
- Retention jobs cover operational prediction/connector data. Identifiable
  clinical-source records and backups require the hospital's approved retention
  and deletion schedule.
- A patient correction/deletion request must be handled jointly with the source
  EHR, audit/legal requirements and backup policy. Never delete only the
  dashboard copy while leaving an undocumented source mismatch.

## 9. Acceptance evidence

The site deployment record should contain:

- approved owners, purpose, data agreement and network diagram;
- unit/bed and identity contract;
- signed mapping sheet and test-message results;
- security/config check, dependency inventory and penetration-test disposition;
- backup plus restore evidence and downtime drill;
- local retrospective report and silent-pilot report;
- readiness-gate export, governance decision and current model hash;
- training attendance, incident process and rollback owner.

See [operations](operations.md), [integration](integration.md), the
[FDE deployment playbook](business/fde-deployment-playbook.md) and the in-app
**Site setup** page.
