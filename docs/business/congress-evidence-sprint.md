# PredictRx Sentinel — Congress evidence sprint

Congress points that depend on real demand, collaboration or local evidence
cannot be created by adding code. This sprint collects credible evidence
without requesting patient records or claiming clinical use.

## Target by 20 December 2026

Minimum credible target:

- 8–12 documented discovery interviews across ICU clinicians, nursing/quality,
  hospital IT/biomedical engineering and hospital leadership;
- at least two cross-functional hospital discovery meetings;
- one written expression of interest for a paid readiness assessment or one
  documented reason hospitals will not buy the current offer;
- one named Bangladesh clinical/health-informatics adviser with a defined
  review role and permission to be named;
- one named NRB/global technical, clinical or interoperability collaborator
  with a concrete contribution and permission to be named;
- one source-system inventory completed without patient data;
- one timed three-minute pitch tested with five independent reviewers.

These are targets, not current achievements. Do not place them in a pitch as
facts until evidence is stored and permission is recorded.

## No-patient-data discovery

A first meeting does not require HL7 messages, FHIR access or patient data.
Ask for:

1. number and type of ICU beds;
2. whether vitals are paper, monitor-only, central-monitor, HIS or EHR based;
3. names and versions of HIS/EHR, LIS, central monitor and interface engine;
4. whether any system already exports HL7, FHIR, CSV or scheduled reports;
5. who owns ICU workflow, biomedical equipment, IT security, privacy/ethics,
   procurement and budget;
6. current handoff, missing-data, audit and quality-review workflow;
7. observed problems and workarounds, without asking for patient identifiers;
8. what a one-ICU readiness assessment would need to deliver to be paid;
9. procurement threshold, timeline and acceptable deployment location;
10. what would make the hospital stop or reject the project.

Record the role, date, consent to retain notes, exact problem statements,
current alternative, urgency, decision process and permission to quote.

## Source-system inventory

Collect configuration facts, not records:

| Area | Inventory fields |
|---|---|
| HIS/EHR | vendor, product/version, deployment owner, API/interface modules, FHIR/HL7 support, sandbox availability |
| LIS | vendor, result export formats, codes, units, correction process, interface owner |
| Monitoring | bedside and central-station vendor/model, gateway/interface licence, export protocol, network owner |
| Identity | MRN namespace, encounter/visit ID, merge/correction process, ward/bed master owner |
| Infrastructure | on-prem/private-cloud preference, OS/virtualisation, reverse proxy/TLS, backup, monitoring, downtime process |
| Governance | data controller, clinical owner, ethics/legal route, retention and support-access policy |

Never ask a contact to email an identifiable spreadsheet or screenshots of
patient charts for convenience.

## Evidence register

For every statement planned for the pitch, mark one category:

- **Observed:** code/test output, signed interview note, written partner
  statement or measured result.
- **Assumed:** buyer, price, deployment duration, willingness to pay or impact
  metric still being tested.
- **Planned:** roadmap capability not yet implemented.
- **Prohibited:** clinical effectiveness, Bangladesh validity, approval,
  endorsement or customer relationship without evidence.

The register should include:

`claim → category → evidence location → evidence owner → permission to disclose → expiry/review date`

## Expression-of-interest scope

An ethical, useful expression of interest can state that the hospital is
interested in evaluating:

- workflow/source readiness;
- one bounded ICU data source;
- hospital-local deployment;
- synthetic commissioning;
- flowsheet, integration-health, audit or research workflow;
- silent model evaluation only if later approved.

It must not state that the hospital endorses the model, authorises clinical
alerts, guarantees procurement or confirms effectiveness unless that is
separately true and approved.

## NRB/global collaboration

Recruit for a defined contribution, not logo collection. Suitable bounded
roles include:

- FHIR/HL7 architecture review;
- clinical-safety or human-factors review;
- biostatistical validation-protocol review;
- security/threat-model review;
- international-market or health-system comparison;
- one recorded pitch critique.

Store the collaborator's name, affiliation, contribution, date, conflicts and
written permission before mentioning the relationship publicly.

## Schedule

### 20–31 October

- freeze the single positioning statement and three-minute pitch;
- build a list of 25 relevant hospital, university, health-informatics and NRB
  contacts;
- complete the first five discovery interviews;
- record objections and change the offer, not the evidence boundary.

### 1–15 November

- complete at least three additional interviews;
- hold two cross-functional discovery meetings;
- complete one no-patient-data source inventory;
- propose a fixed-scope paid readiness assessment;
- recruit defined clinical and NRB/global reviewers.

### 16–30 November

- if a partner exists, run synthetic commissioning and mapping workshop;
- otherwise run independent workflow/usability reviews using synthetic data;
- obtain a written expression of interest or document the commercial no-go
  evidence and resulting redesign.

### 1–15 December

- freeze code, model hash, claims and evidence register;
- record the offline demo and complete five timed pitch reviews;
- prepare judge objection cards and one-page commercial offer.

### 16–25 December

- fix only critical defects;
- rehearse failure recovery and offline operation;
- verify every named relationship, metric and claim;
- run the final Congress preflight and preserve its output.

## Congress proof pack

Carry offline:

- one-page product and commercial offer;
- current model/readiness passport;
- frozen model hash and test/preflight output;
- architecture/data-flow diagram;
- interview evidence summary with identities removed where required;
- any disclosable expression of interest;
- security, ethical-AI and claims-boundary summary;
- three-minute demo recording and screenshots;
- source-system inventory template and paid-readiness proposal.

