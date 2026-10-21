# Product brief — PredictRx Sentinel

## Problem

Sepsis kills ~11 million people per year worldwide, with the highest burden in lower-middle-income countries. In ICUs, delayed recognition costs hours that matter for survival and organ preservation.

## Solution

A hospital ICU dashboard that continuously produces a calibrated
**PhysioNet Challenge-label early-warning score** from vitals, labs, and
past-only clinical trends. TrustGate checks freshness and perturbation
stability before any interruption; grouped TreeSHAP, a non-causal evidence
graph, and clinician review make the workflow inspectable. The score is not an
exact incident six-hour probability.

## Users

| Role | Need |
|---|---|
| ICU nurse / doctor | See who is deteriorating before labels catch up |
| ICU charge / coordinator | Unit-level urgency overview |
| Hospital quality / IT | Audit trail, model transparency, integration path |

## Hospital pilot cockpit (current release)

The product is now built to be run by a hospital, not only demonstrated:

| Module | What a site gets |
|---|---|
| Integration hub | FHIR R4, FHIR NDJSON and HL7 v2 ingestion through one validated pipeline; mapping registry; quarantine; feed health; retry spool; circuit breaker |
| Silent pilot | Real feeds scored while bedside staff are blinded; shadow alerts; outcome adjudication; clinician feedback; local metrics (detection, lead time, calibration, alert burden, subgroups, missingness); read-only threshold simulation; pseudonymised exports |
| Clinical workflow | Bed ownership and take-over, review SLA clock, printable shift handoff, observation provenance, missing-signal matrix, TrustGate-only attention banner |
| Evidence copilot | Cited Surviving Sepsis Campaign / Sepsis-3 passages beside model drivers; hospital-approved local protocols ranked first; treatment and dosing queries refused |
| Site operations | OIDC/SSO, scoped integration keys, secret rotation, single-writer lease with read-only fallback, Prometheus metrics, backup/restore, retention, audit-chain verification |

The immediate commercial wedge is the workflow layer, not a claim that the
sepsis model improves outcomes: bedside ICU/ward flowsheets, ADT, QR bed labels,
handoff, missing-data reporting, lab CSV and direct-monitor relay, plus NEWS2
for ward deterioration. Frozen Run 4 stays silent while the site builds local
evidence. See the [business and FDE pack](business/business-model.md).

Interruptive alerts stay off until every readiness gate passes: local
retrospective validation, pilot duration and volume, adjudicated outcomes,
sensitivity floor, alert-burden budget, healthy feeds, governance sign-off and
production security.

What it still does not do: diagnose, recommend treatment, act autonomously,
retrain or re-threshold the frozen model, or learn from site data
(no reinforcement learning, no federated learning in this release).

## Customer

Private hospitals, hospital groups, and NGO/public programmes operating ICUs. **Not** sold to patients.

## Positioning

Clinical **decision support** — never diagnosis, never prescription, never autonomous contact.

## Initial market

- CPU inference, offline-capable demo, modular API, future on-prem / private cloud
- A separately validated `vitals_only` fallback family is planned; it is not the current frozen model

## Value proposition

- Earlier warning before labelled onset (measured on held-out data)
- Explicit alert-burden measurement plus a data-quality/abstention gate;
  a TrustGate false-alert reduction benefit is not established
- Explainable factors + data-quality warnings
- Audit-ready workflow for mortality / quality review

## Pricing hypothesis (unvalidated)

- 8-week retrospective / silent pilot: free or cost-covered
- Integration: BDT 200k–500k
- Subscription: BDT 75k–250k / hospital / month (ICU size & integrations)
- Enterprise group: annual licence

## Expansion path

1. Adult ICU sepsis (V1)  
2. ED deterioration  
3. Ward deterioration  
4. AKI  
5. Readmission / complications  

Same observation platform → multiple risk models.
