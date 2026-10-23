# PredictRx Sentinel — business model

## Status and evidence boundary

This is a set of commercial hypotheses to test, not a forecast or statement of market fact.

PredictRx Sentinel is a **retrospective research prototype**, is **not approved for clinical use**, and has **no Bangladesh validation**. The frozen Run 4 model and thresholds remain unchanged. No clinical outcome improvement, mortality reduction, prevented sepsis, operational savings, or return on investment is claimed.

Bangladesh is the target learning market. Product classification, registration, licensing, data, research, and other DGDA or local regulatory obligations require advice from qualified Bangladesh legal/regulatory professionals and, where appropriate, relevant authorities. This document does not make a definitive regulatory determination.

## EHR / HIS commercial & legal path

How we sit beside Epic/Cerner/OpenMRS/local HIS without giving away IP —
Connection Ladder L0–U2, Vendor Adapter fees, SMART/CDS Hooks as standards
(not claimed partnerships), soft-landing sidecar language — is documented in
[`ehr-partnership-and-commercial-strategy.md`](./ehr-partnership-and-commercial-strategy.md).
That playbook is part of the business system of record, not a side note.

## Product wedge

The initial product is not “AI that treats sepsis.” It is an ICU workflow and research operations layer:

1. digital longitudinal flowsheet with source provenance;
2. structured shift handoff, ownership, and review status;
3. feed health, missingness, mapping, and quarantine visibility;
4. quality/research dashboard, cohort review, audit, and pseudonymised export;
5. frozen sepsis scoring in silent mode for locally governed evaluation.

This wedge can be bought and assessed on workflow, data quality, governance, and research utility while clinical model value remains unproven.

## Customer segments

### Beachhead: Bangladesh private hospitals

**Hypothesis:** private hospitals and groups with adult ICUs, digital source data, an executive sponsor, and quality or research priorities can fund 8–12 week pilots and make faster procurement decisions.

**Likely buyer roles to test:** hospital CEO/COO, medical director, ICU director, chief nursing officer, quality head, CIO/IT director, or innovation lead.

**Users:** ICU and nursing champions, shift coordinators, quality/research staff, and IT/integration teams.

### Public, NGO, and academic path

Potential models:

- public procurement for workflow/data-quality infrastructure;
- donor or NGO-funded implementation research;
- university/hospital research collaboration;
- shared services across a health network;
- open-core software with paid deployment, security, integration, validation, training, and support.

These routes may improve access but often require longer approvals, grant alignment, and strict sustainability planning. Grant support should not disguise an offering that a site cannot operate after the award.

## Jobs to be done

Customer discovery should test whether hospitals will pay to:

- reduce manual effort finding a coherent ICU timeline;
- improve completeness and accountability of shift handoff;
- see delayed, missing, conflicting, or quarantined observations;
- create auditable quality-review cohorts and exports;
- run a governed local evaluation of a frozen model;
- satisfy internal evidence, security, and oversight expectations before considering clinical AI.

Do not assume these jobs are priorities; rank them through observation, interviews, and paid-pilot behavior.

## Value propositions to test

### Clinical operations

“Give designated ICU staff one traceable flowsheet and handoff workspace.”

Measure: task completion, completeness, time, adoption, workarounds, and user burden. Do not infer patient benefit.

### Quality and research

“Make local data quality, cohort review, adjudication, and audit easier to govern.”

Measure: cohort preparation time, provenance coverage, adjudication throughput, export reproducibility, and review satisfaction.

### IT and governance

“Provide an on-premises, role-scoped, auditable path to evaluate before exposing a model.”

Measure: deployment effort, mapping maintenance, incidents, restore success, access review, and approval completion.

## Offer ladder

### 1. Discovery and readiness assessment

- 1–2 weeks;
- workflow observation, source inventory, governance gap assessment, data feasibility, and scoped proposal;
- fixed-fee or credited toward a pilot.

### 2. SafeLaunch workflow/research pilot

- 8–12 weeks, one adult ICU;
- mapping, deployment, workflow configuration, retrospective evaluation, optional approved silent operation, training, and closeout;
- unchanged Run 4; no live model alerts.

### 3. Workflow/research operations subscription

- flowsheet, handoff, quality dashboard, monitoring, support, audit export, upgrades, and periodic data-quality review;
- model scoring remains within the approved silent/research boundary unless a separate future authorization exists.

### 4. Hospital group deployment

- standardized mappings and governance with site-specific validation;
- central portfolio view without erasing local ownership or local failure analysis.

### 5. Open-core / public-interest deployment

- a defined core may be openly available in the future;
- revenue from implementation, supported releases, enterprise identity/security, connectors, validation operations, training, and service levels;
- license, governance, maintenance capacity, and sustainability require a separate decision.

## Pricing hypotheses

All amounts below are **discovery ranges**, not quotes, validated willingness-to-pay, or market facts. Test total cost, payment milestones, taxes, procurement friction, and alternatives with buyers.

| Offer | Discovery range | Primary pricing variable |
|---|---:|---|
| Readiness assessment | BDT 75,000–250,000 | stakeholder count, source complexity, on-site work |
| 8–12 week one-ICU SafeLaunch | BDT 300,000–1,200,000 | integrations, data cleanup, security, adjudication, travel |
| Integration/setup component | BDT 200,000–500,000 | source systems and connector work |
| Workflow/research subscription | BDT 75,000–250,000 per hospital/month | ICU size, support level, connectors, hosting responsibilities |
| Hospital group | custom annual assumption | site count, shared services, SLA, integration reuse |

Separate or pass-through costs may include hardware, cloud/private hosting, interface vendor fees, penetration testing, travel, tax/VAT, translation, ethics administration, clinical adjudication, and third-party support.

### Pricing discovery questions

- Which budget owns flowsheet, handoff, quality, research, or integration work?
- What approval thresholds change the procurement route?
- Is a paid pilot possible, and what deliverables release payment?
- Which current staff/vendor costs are observable without claiming savings?
- What implementation work is one-time versus recurring?
- What support hours and response commitments are required?
- Would a hospital prefer capital, annual licence, monthly service, or grant-supported procurement?
- What data, publication, branding, or exclusivity terms would be unacceptable?

## Unit economics to learn

Track per site:

- sales and procurement cycle;
- FDE, clinical, statistician, security, training, and support hours;
- integration reuse versus site-specific work;
- infrastructure and third-party costs;
- gross contribution before shared R&D;
- incident and maintenance burden;
- renewal, expansion, and reference willingness.

No scalable business claim is warranted until multiple paid sites show repeatable mappings, bounded deployment effort, sustained workflow use, and renewal intent.

## Channels and sales motion

1. clinician, quality, or IT champion identifies a workflow problem;
2. cross-functional discovery includes buyer, user, data owner, security, procurement, and governance;
3. paid readiness assessment where feasible;
4. fixed-scope SafeLaunch with explicit stop rules;
5. evidence review and subscription/group proposal;
6. expansion only after repeat use and site-specific approval.

Potential channels to test include hospital groups, ICU/quality professional networks, EHR/interface partners, universities, implementation-research consortia, NGOs, and public digital-health programmes. No partnership should be represented without written agreement.

## Grant and sponsorship strategy

### Appropriate categories

- implementation research and health systems strengthening;
- ICU quality, patient safety, and sepsis research;
- responsible AI, local validation, and algorithmic accountability;
- clinical informatics and LMIC research capacity;
- digital public goods/open-source sustainability;
- catalytic innovation pilots;
- in-kind infrastructure, cybersecurity, or connectivity support.

### Named leads to verify

These are unverified prospecting leads only. Verify current calls, eligibility, deadlines, geography, terms, and conflicts directly. Inclusion implies neither funding nor endorsement:

- Bangladesh Medical Research Council;
- DGHS / Ministry of Health and Family Welfare programmes;
- ICT Division / Aspire to Innovate;
- icddr,b;
- BRAC and BRAC University;
- Wellcome;
- Gates Foundation / Grand Challenges opportunities;
- Grand Challenges Canada;
- Global Innovation Fund;
- USAID Development Innovation Ventures;
- NIHR global health research opportunities;
- UNICEF innovation programmes;
- WHO calls;
- Asian Development Bank and World Bank health-system programmes;
- Bangladesh hospital groups and corporate CSR programmes.

Funding agreements must preserve research independence, hospital data control, publication integrity, conflict disclosure, and the right to report negative results.

## Go/no-go scorecard

Agree thresholds before each engagement. Proceed only when all mandatory gates pass.

### Pilot go

- named executive, clinical, IT, security/privacy, quality/research, and governance owners;
- approved procurement, data-use, ethics/institutional, security, and legal/regulatory paths;
- usable source data and a bounded mapping plan;
- willingness to keep scores silent and Run 4 unchanged;
- measurable workflow problem and designated users;
- budget or verified funding path.

### Subscription go

- sustained workflow use and acceptable burden;
- reliable data pipeline, provenance, backup/restore, and access control;
- implementation and support cost fits the tested price;
- named operational owner and renewal budget;
- no unresolved critical security or governance issue;
- value demonstrated independently of clinical model claims.

### No-go or redesign

- request for clinical use of the unapproved score;
- no authority to use data or no ethics/institutional determination;
- data quality invalidates the intended workflow or evaluation;
- buyer and user problems do not align;
- customization or support overwhelms recurring value;
- sponsor requires data access, favorable findings, or unsupported claims;
- regulatory/legal uncertainty cannot be responsibly bounded.

## Model roadmap and restraint

### Frozen Run 4

Run 4 remains unchanged during SafeLaunch so evaluation is interpretable and post-hoc tuning does not manufacture apparent local fit. Threshold simulation may inform research reporting but does not change production behavior.

### No reinforcement learning now

Reinforcement learning requires a defensible reward, safe exploration, causal interpretation of actions and outcomes, and permission for a policy to affect care. Current data are retrospective or silent; acknowledgements and clicks are not clinical rewards. RL would risk optimizing documentation patterns, treatment-selection bias, or proxies rather than patient benefit. It is therefore outside the current product and evidence strategy.

### Federated learning only after three aligned sites

Do not begin federated learning until **at least three sites** align:

- intended use, cohorts, outcomes, and label timing;
- variable definitions, units, timestamps, and missingness handling;
- data quality and local sample sufficiency;
- ethics, consent/data-use, security, and cross-site governance;
- evaluation, versioning, rollback, and held-out testing.

Federation does not fix incompatible data. Before three aligned sites, validate each site independently and invest in common semantics and governance.

## Defensibility

Potential defensibility must be earned through:

- repeatable deployment and mapping playbooks;
- trusted hospital relationships and locally governed evidence;
- workflow fit and auditable operations;
- reusable, versioned data semantics;
- honest negative-result handling and safety discipline;
- lower implementation and support effort across sites.

Model complexity alone is not a moat, and hospital data must not be treated as a proprietary asset unless rights explicitly allow the stated use.

## Twelve-month learning agenda

This is sequencing, not a revenue forecast:

1. complete buyer/user interviews across private, public, NGO, and academic segments;
2. secure one paid or cost-covered readiness assessment;
3. run one SafeLaunch with explicit workflow and economics measures;
4. refine standard mappings, security pack, contracting templates, and training;
5. seek a second and third site only if the first shows repeatable non-model value;
6. compare site semantics and governance before considering any federated research;
7. publish limitations and negative findings where agreements permit;
8. decide whether the viable core is workflow SaaS/support, research infrastructure, services, open-core, or a combination.

## Claims discipline

Every proposal and sales artifact should distinguish:

- **observed:** repository evidence or measured pilot result;
- **assumed:** pricing, buyer, workflow value, or delivery estimate to test;
- **planned:** capability or study not yet completed;
- **prohibited claim:** clinical effectiveness, Bangladesh validity, approval, or endorsement without evidence.

Commercial urgency never overrides the research-only boundary.
