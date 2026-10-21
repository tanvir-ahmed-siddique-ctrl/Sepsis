# PredictRx Sentinel — SafeLaunch pilot proposal

## Proposal status

This document is a discussion draft for hospital discovery. It is not a clinical, regulatory, legal, security, or procurement approval.

PredictRx Sentinel is a **retrospective research prototype** and is **not approved for clinical use**. It has not been validated in Bangladesh, and no claim is made that it improves outcomes, prevents sepsis, reduces mortality, or saves cost. The frozen Run 4 model and its production thresholds remain unchanged during this pilot.

## Offer in one sentence

An 8–12 week, on-premises SafeLaunch pilot that gives an ICU a digital flowsheet, structured shift handoff, and quality/research dashboard while evaluating sepsis scoring silently, with no score or model-generated alert used for patient care.

## Why start with workflow

The near-term product wedge is the work hospitals can inspect without relying on model validity:

- one longitudinal view of ICU observations and data provenance;
- clearer shift handoff, ownership, and review status;
- feed-health, missingness, and mapping visibility;
- quality-review cohorts, audit export, and pilot metrics;
- a governed research environment for local retrospective and silent evaluation.

Sepsis scores run in the background only to measure local behavior. They do not diagnose, prescribe, prioritize care, contact patients, or trigger bedside action.

## Proposed customer and scope

**Initial buyer:** a private hospital or hospital group with an adult ICU, an executive sponsor, an ICU clinical lead, and an IT owner.

**Users during SafeLaunch:** designated ICU champions, quality/research staff, IT/integration staff, and approved evaluators. Bedside access to sepsis scores remains disabled.

**Illustrative pilot boundary:**

- one adult ICU and one source system or approved batch extract;
- retrospective validation followed, if approved, by silent prospective data collection;
- on-premises or hospital-controlled environment;
- no autonomous action, treatment advice, model retraining, or threshold change;
- no expansion to other units or conditions without a separate change decision.

## Deliverables

1. Signed pilot charter, data-use terms, scope, success criteria, and stop rules.
2. Data dictionary and source-to-canonical mapping with unit and range checks.
3. Security and architecture review pack, access matrix, retention plan, and incident contacts.
4. Configured digital flowsheet, handoff workflow, quality dashboard, and feed-health monitoring.
5. Frozen-artifact verification for Run 4; no model or threshold modification.
6. Retrospective local validation report covering prevalence, missingness, calibration, discrimination, alert burden simulation, and predefined subgroups where sample sizes permit.
7. If governance approves, a time-boxed silent run with bedside users blinded to model output.
8. Weekly status notes, issue/risk register, training materials, and final go/no-go report.
9. Data return or verified deletion at close, according to the approved agreement.

## SafeLaunch phases

| Phase | Typical timing | Exit condition |
|---|---:|---|
| Discover and govern | Weeks 1–2 | Named owners; approved scope; procurement, data-use, ethics, security, and legal paths identified |
| Map and validate data | Weeks 2–4 | Required fields mapped; units tested; provenance visible; unacceptable quality failures resolved or documented |
| Configure workflow | Weeks 3–5 | Flowsheet, handoff, roles, audit, backup, and quality dashboard accepted in a test environment |
| Retrospective evaluation | Weeks 4–7 | Locked analysis completed on local historical data without changing Run 4 |
| Silent operation | Weeks 6–10 | Governance approval obtained; scoring remains hidden from bedside care; operational metrics collected |
| Decision and closeout | Weeks 10–12 | Evidence reviewed; go, extend, redesign, or stop decision recorded; data closeout completed |

Timing depends on contracting, data access, mapping complexity, ethics review, and site availability. An 8-week pilot is feasible only when these prerequisites are ready; otherwise use the 12-week path or pause.

## Success metrics and pre-agreed targets

Targets must be set jointly before data are analyzed. Values below are **discovery starting points, not validated standards**.

### Workflow and operations

- at least 90% of expected observation messages received after agreed exclusions;
- at least 95% of accepted records retain source timestamp and provenance;
- median handoff completion time and missing-field rate measured against a pre-pilot baseline;
- at least 80% of designated pilot users complete training;
- no unresolved critical-severity security event;
- successful backup-and-restore test and auditable access review;
- weekly issue resolution within agreed severity-based service levels.

### Research evaluation

- prespecified cohort, label process, exclusions, missingness analysis, and subgroup plan completed;
- local calibration, discrimination, and simulated alert burden reported with uncertainty;
- at least 100 distinct encounters and 30 adjudicated outcomes as an operational starting point, subject to statistical review;
- no tuning of the frozen Run 4 model or its thresholds on pilot data;
- no outcome-improvement inference from retrospective or silent results.

### Commercial learning

- buyer, budget owner, procurement path, implementation burden, and willingness-to-pay documented;
- users identify a repeatable flowsheet, handoff, or quality-review problem worth continuing to solve;
- implementation effort and recurring support cost measured rather than assumed.

## Go/no-go decision

**Go to a larger workflow/research pilot** only if all mandatory governance gates pass, data quality is usable, the workflow is adopted, security risks are accepted by authorized owners, and the site sees value independent of model alerts.

**Continue silent research only** if workflow value exists but local model evidence, sample size, or regulatory position is insufficient.

**Redesign** if mapping, usability, or alert-burden simulation misses agreed targets but has a credible bounded remedy.

**Stop** if approval is absent, data rights are unclear, critical security issues remain, data quality makes evaluation invalid, staff burden is unacceptable, or anyone requests clinical reliance on an unapproved score.

Passing SafeLaunch does not itself authorize interruptive alerts. Any move toward clinical use requires a separate prospective protocol, institutional approval, clinical safety case, and regulatory/legal review.

## Responsibilities

**Hospital provides:** executive and clinical sponsors; authorized data access; source-system expertise; ethics and legal decisions; infrastructure or approved hosting; clinical adjudication; staff time; and final acceptance.

**PredictRx team provides:** field-deployment lead; implementation and training; mapping support; frozen-artifact verification; dashboards; analysis plan and report; issue management; and closeout support.

**Jointly owned:** scope control, risk register, success criteria, communication, incident response drills, and go/no-go decision.

## Commercial assumptions for discovery

These are hypotheses to test, not market facts or a quotation:

- one-site 8–12 week pilot: **BDT 300,000–1,200,000**, depending on integration, on-site effort, infrastructure, and evaluation scope;
- integration/setup component: **BDT 200,000–500,000**;
- post-pilot workflow/research subscription: **BDT 75,000–250,000 per hospital per month**;
- travel, hardware, third-party interfaces, taxes, security testing, and ethics/research costs priced separately where applicable.

Discovery should test a paid pilot, cost-covered pilot, and sponsor-subsidized pilot. No discount or free pilot should proceed without explicit learning goals, a named budget owner, and a closeout date.

## Procurement, security, data-use, and ethics checklist

Before any identifiable or linkable hospital data moves:

- [ ] legal entity, procurement method, budget owner, tax/VAT treatment, and signatories confirmed;
- [ ] intended use and prohibited uses written into the pilot charter;
- [ ] data controller/processor roles and permitted data fields documented;
- [ ] data-use agreement, confidentiality terms, retention, deletion, breach duties, and audit rights approved;
- [ ] ethics/IRB or institutional determination recorded, including consent or waiver basis where applicable;
- [ ] Bangladesh regulatory classification and any DGDA obligations reviewed by qualified local counsel/regulatory specialists; no definitive classification is asserted here;
- [ ] deployment boundary, network diagram, asset inventory, threat review, access roles, SSO/identity approach, encryption, key custody, logs, backups, recovery, patching, and vulnerability testing accepted;
- [ ] only minimum necessary data used; research exports pseudonymised; free text excluded where possible;
- [ ] model card, limitations, frozen hashes, label definition, and local validation protocol approved;
- [ ] incident, downtime, rollback, support, escalation, and data-closeout procedures rehearsed;
- [ ] public communications and use of hospital name/logo require written approval.

## Requested next step

A 60–90 minute discovery workshop with the hospital executive sponsor, ICU lead, quality/research lead, IT/integration lead, security/privacy representative, procurement, and legal/ethics representative. The output is a one-page problem statement, data feasibility decision, named owners, and a decision on whether to prepare a formal scoped quotation.
