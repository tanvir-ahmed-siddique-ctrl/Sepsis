# PredictRx Sentinel — FDE deployment playbook

## Purpose and non-negotiable boundary

This playbook guides a forward-deployed engineering (FDE) team through an 8–12 week hospital SafeLaunch.

PredictRx Sentinel is a **retrospective research prototype**, not approved for clinical use and not validated in Bangladesh. The frozen Run 4 model and thresholds do not change. Sepsis scoring remains silent and unavailable for bedside decision-making. The engagement must not claim improved outcomes, prevented sepsis, reduced mortality, cost savings, or clinical effectiveness.

The product delivered now is an ICU digital flowsheet, structured handoff, and quality/research dashboard. Model evaluation is a governed research workstream inside that workflow deployment.

## Operating principles

1. **Workflow before prediction.** A site must receive measurable value from documentation, handoff, provenance, and quality review without relying on a score.
2. **One accountable owner per decision.** The FDE resolves ambiguity in the field but does not substitute for hospital clinical, ethics, security, or legal authority.
3. **Configuration before customization.** Record every site-specific request; avoid forks unless the need repeats and has a product owner.
4. **Evidence before escalation.** Keep scores silent until a separate future protocol and all institutional and legal requirements are satisfied.
5. **Minimum necessary data.** Avoid free text and direct identifiers unless explicitly necessary and approved.
6. **Reproducibility.** Record versions, frozen hashes, mappings, cohort definitions, exclusions, and report-generation steps.
7. **Stop safely.** A clean rollback and data-closeout path exists before ingestion begins.

## Preconditions

Do not start data ingestion until:

- an executive sponsor, ICU clinical lead, IT owner, security/privacy owner, and project manager are named;
- intended use, prohibited use, unit boundary, timeline, and stop rules are signed;
- procurement and contracting path is known;
- data-use and ethics/institutional determinations are documented;
- Bangladesh regulatory and DGDA questions have been sent for qualified local legal/regulatory review; this playbook does not determine classification;
- the hospital accepts that Run 4 is frozen and that the score cannot be used for care;
- deployment architecture, identity, encryption, backup, retention, deletion, and incident responsibilities are accepted;
- source-system access and a test dataset are available.

## Week-by-week execution

### Week 0 — qualify and mobilize

**Goals:** confirm fit before consuming clinical or engineering time.

- interview sponsor, ICU, quality, IT, security/privacy, procurement, and ethics/legal;
- document the current flowsheet, handoff, review process, and failure points;
- identify source systems, interface methods, data owners, and infrastructure constraints;
- agree discovery targets, exclusions, meeting cadence, escalation route, and change control;
- issue a red/amber/green readiness memo.

**Exit:** signed charter or no-go. No patient data.

### Week 1 — govern and baseline

- complete procurement, security, data-use, and ethics trackers;
- define roles, access matrix, minimum dataset, retention, deletion, and support hours;
- baseline current handoff completion, missing fields, review turnaround, and staff burden;
- freeze the local evaluation protocol before outcome analysis;
- inventory the exact Run 4 artifact and verify recorded hashes.

**Exit:** governance owner accepts the data path; baseline and analysis plan are versioned.

### Week 2 — map data

- map identifiers, encounters, timestamps, vitals, labs, units, code systems, and provenance;
- profile completeness, duplicates, delay, implausible values, and unit conflicts;
- build a mapping decision log with clinical sign-off;
- use synthetic or de-identified test records first;
- define quarantine behavior and reconciliation ownership.

**Exit:** mapping coverage is reported; unsafe ambiguity is resolved or blocks the field.

### Week 3 — deploy the test environment

- install inside the approved network boundary;
- configure secrets, least-privilege roles, SSO/OIDC where available, TLS termination, monitoring, and log access;
- verify non-demo mode, one active writer, health checks, backup, restore, audit-chain verification, and rollback;
- run a security tabletop for credential compromise, feed outage, and suspected data exposure.

**Exit:** security/IT sign the environment checklist; restore and rollback evidence exists.

### Week 4 — configure workflow

- configure the digital flowsheet, source provenance, handoff ownership, review status, missing-signal views, and quality dashboard;
- test representative shift scenarios with clinicians using non-production data;
- resolve critical usability and accessibility problems;
- prepare role-specific quick guides and support channels.

**Exit:** clinical lead accepts workflow for limited pilot use; scores remain hidden.

### Week 5 — dry run and training

- execute end-to-end test records from source through dashboard and approved export;
- validate timestamps, unit conversion, quarantine, duplicate handling, downtime, and reconciliation;
- train champions, quality reviewers, and support staff;
- rehearse incident response and system-unavailable workflow;
- confirm that no score or model alert is exposed to bedside users.

**Exit:** signed dry-run report; no open critical defects.

### Week 6 — retrospective evaluation

- run the prespecified cohort against the unchanged Run 4 artifact;
- measure prevalence, missingness, discrimination, calibration, simulated alert burden, and subgroup results with uncertainty;
- document label quality and adjudication limits;
- prohibit threshold tuning, retraining, or post-hoc subgroup claims;
- review results first with the statistician and clinical governance group.

**Exit:** reproducible local report. Results may support more research; they do not establish clinical benefit.

### Week 7 — limited workflow launch

- activate the flowsheet, handoff, and quality workflow for designated users;
- begin daily adoption, data quality, feed health, and support review;
- keep all model outputs in the approved silent evaluator view only;
- record workarounds and classify each as training, configuration, defect, or product request.

**Exit:** stable operation for five working days or rollback.

### Week 8 — stabilize and review

- compare workflow metrics with baseline;
- sample audit logs and role access;
- run a second restore or failover exercise if Week 3 evidence was incomplete;
- assess support load, mapping maintenance, user burden, and recurring cost;
- hold an interim go/extend/redesign/stop review.

**Exit:** sponsor decides whether to close at eight weeks or continue to Weeks 9–12.

### Weeks 9–10 — silent observation, if approved

- continue silent score collection and outcome adjudication;
- monitor source lag, missingness, score distribution, calibration drift proxies, and simulated alert burden;
- collect structured user feedback on flowsheet, handoff, and quality tasks—not on score-guided care;
- do not alter Run 4 or enable interruptive alerts.

**Exit:** minimum agreed duration/volume reached or limitations documented.

### Week 11 — decision package

- assemble workflow, operational, security, research, economics, and user findings;
- quantify implementation hours, support hours, infrastructure, and unresolved dependencies;
- clearly separate observed results from assumptions;
- draft one of four recommendations: go to larger workflow/research pilot, continue silent research, redesign, or stop.

**Exit:** cross-functional review completed and dissent recorded.

### Week 12 — handover and closeout

- obtain the executive/governance decision;
- hand over runbooks, ownership, open risks, training record, and support terms;
- export, return, retain, or delete data exactly as contracted and verify completion;
- revoke temporary access and rotate temporary credentials;
- hold a blameless retrospective and product-learning review.

**Exit:** signed closeout and data disposition record.

## Stakeholders

- **Executive sponsor:** owns institutional priority, funding, and final decision.
- **ICU clinical lead:** owns workflow safety, clinical interpretation boundaries, and clinician availability.
- **Nursing/shift champion:** validates flowsheet and handoff usability.
- **Quality/research lead:** owns cohort review, adjudication operations, and quality measures.
- **Biostatistician/epidemiologist:** owns prespecified analysis and uncertainty.
- **IT/integration lead:** owns source access, mappings, network, and operational interfaces.
- **Security/privacy officer:** owns security and privacy acceptance.
- **Ethics/IRB or institutional review body:** determines research/quality-review oversight.
- **Legal/regulatory counsel:** reviews contracts, data obligations, and Bangladesh/DGDA implications.
- **Procurement/finance:** owns vendor onboarding, commercial process, tax, and payment.
- **FDE lead:** accountable for delivery coordination, configuration, evidence pack, and issue closure.
- **Product/engineering:** owns product defects, release decisions, and support beyond field configuration.

## RACI

R = responsible, A = accountable, C = consulted, I = informed.

| Work/decision | Exec sponsor | ICU lead | Quality/research | IT | Security/privacy | Ethics/legal | FDE lead | Product/engineering |
|---|---|---|---|---|---|---|---|---|
| Charter, scope, funding | A | C | C | C | C | C | R | I |
| Intended-use boundary | I | A | R | I | C | C | C | I |
| Data-use and ethics approval | I | C | R | C | C | A | C | I |
| Bangladesh regulatory/DGDA review | I | C | C | I | C | A/R | I | I |
| Source mapping | I | C | C | A/R | I | I | R | C |
| Infrastructure deployment | I | I | I | A/R | C | I | R | C |
| Security acceptance | I | I | I | R | A | C | R | C |
| Workflow acceptance | I | A | C | C | I | I | R | C |
| Frozen-artifact verification | I | C | C | I | I | I | R | A |
| Statistical analysis | I | C | A/R | I | I | C | R | I |
| Incident response | I | C | I | R | A | C | R | C |
| Go/extend/redesign/stop | A | R | C | C | C | C | C | I |
| Data closeout | I | C | R | R | A | C | R | I |

The named person and delegated authority for every A/R cell must be recorded in the charter. One individual may hold several roles at a small site, but accountability cannot be left blank.

## Daily and weekly operating cadence

**Daily during mapping and launch:** 15-minute FDE/IT checkpoint; review feed failures, quarantines, critical defects, and access incidents.

**Twice weekly:** clinician champion workflow session; observe tasks and record burden without soliciting clinical reliance on scores.

**Weekly steering review:** scope, milestones, metrics, risks, decisions, spend, and upcoming approvals. Send a one-page status note with red/amber/green items and named owners.

**Decision log:** record date, decision, alternatives, evidence, approver, and reversal condition.

## Metrics and go/no-go rubric

Targets are agreed before launch. Suggested starting points are not validated standards:

| Domain | Example measure | Go signal | Stop/redesign signal |
|---|---|---|---|
| Governance | Required approvals | All recorded | Missing/ambiguous authority |
| Security | Critical findings/incidents | None unresolved | Unaccepted critical risk or reportable breach |
| Data | Expected messages and provenance | ≥90% expected; ≥95% provenance after agreed exclusions | Systematic missingness/unit ambiguity invalidates use |
| Reliability | Availability and restore | Agreed availability; restore demonstrated | Unsafe silent loss or no recoverable backup |
| Workflow | Training and repeated use | ≥80% designated users trained; sustained weekly use | Material burden or workflow rejection |
| Handoff | Completeness/time | Improvement against prespecified local baseline | No improvement or increased safety burden |
| Research | Cohort and adjudication | Prespecified report completed; sample supports interpretation | Invalid labels, leakage, or underpowered claims |
| Commercial | Buyer/problem/effort | Named budget owner; repeatable problem; support cost understood | No owner, no budget path, or services burden dominates |

Local model metrics are reported, not converted into bedside authorization. Existing operational defaults such as 100 encounters, 30 adjudications, sensitivity floor 0.5, and at most 2 simulated alerts per 100 patient-hours are committee starting points only—not validated clinical thresholds.

## Stop-work triggers

Pause ingestion or access immediately for:

- suspected unauthorized access, data disclosure, or audit-chain failure;
- uncertain patient-data authority or expired approval;
- score exposure to unapproved users or use in clinical decisions;
- material mapping/unit error that could corrupt records;
- request to retrain, re-threshold, or modify frozen Run 4 outside an approved separate research protocol;
- uncontrolled export, unapproved scope expansion, or inability to honor deletion;
- infrastructure state that risks silent data loss.

The FDE lead records the event; the hospital’s authorized owner decides restart after evidence of containment and remediation.

## Field change control

Classify every request:

1. **Configuration:** reversible site setting within approved intended use.
2. **Mapping:** source normalization with clinical/IT sign-off.
3. **Defect:** expected behavior is broken; product/engineering owns remediation.
4. **Product request:** reusable capability requiring roadmap decision.
5. **Clinical/model change:** out of pilot scope; requires separate protocol and governance.

No field engineer changes model files, thresholds, labels, or clinical logic to close a deployment ticket.

## Security, procurement, data-use, and ethics evidence pack

- [ ] vendor registration, purchase order/SOW, payment milestones, support and exit terms;
- [ ] architecture/data-flow diagram and inventory of systems, ports, subprocessors, and data locations;
- [ ] least-privilege access matrix, identity lifecycle, secrets/key custody, encryption, logs, patching, vulnerability review;
- [ ] backup/restore, downtime, disaster recovery, incident notification, and contact tree;
- [ ] DUA/DPA or equivalent, purpose limitation, minimization, retention, deletion, export, audit, and breach terms;
- [ ] ethics/IRB/institutional determination and approved protocol or quality-improvement basis;
- [ ] legal/regulatory review, including any DGDA position, documented as professional advice rather than inferred by the team;
- [ ] model/data cards, frozen artifact hashes, limitations, label definition, analysis plan, subgroup safeguards;
- [ ] training roster, dry-run evidence, decision log, issue/risk register, final report, and data disposition certificate.

## Why reinforcement learning is not used

Reinforcement learning (RL) would require a defensible reward tied to actions and outcomes, reliable causal attribution, safe exploration, and controls against learning hospital practice patterns or harmful shortcuts. This pilot has retrospective and silent observational data, no permission for automated action, and no evidence that an optimized policy would improve outcomes. Feedback such as acknowledgement or dismissal is also not a clinical reward. Therefore RL would add safety, causal, governance, and validation risk without a justified deployment benefit.

## Why federated learning waits

Federated learning is not a substitute for local validation or aligned governance. Consider it only after **at least three sites** have:

- comparable intended use, cohort and outcome definitions;
- aligned variable semantics, units, timing, missingness handling, and quality controls;
- sufficient local sample size and stable pipelines;
- compatible consent/data-use, ethics, security, and cross-site governance;
- an agreed evaluation protocol and a held-out assessment strategy;
- resources for secure aggregation, version control, rollback, poisoning/leakage analysis, and site-drift monitoring.

Before those conditions, federation can average incompatible processes and hide site-specific failure. With one or two sites, keep data local, validate separately, and learn which semantics must be aligned.

## Handover standard

The engagement is complete only when the hospital has named operational owners, usable runbooks, verified access removal, a tested recovery path, a limitations-aware evaluation report, an explicit go/no-go decision, and documented data disposition.
