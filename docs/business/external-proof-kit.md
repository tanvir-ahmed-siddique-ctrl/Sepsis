# PredictRx Sentinel — external proof kit

This kit helps obtain real evidence without requesting patient records. Replace
bracketed fields. A draft, sent message or unsigned form is not an endorsement.

## Priority contact map

Start with warm introductions to:

1. ICU consultant/clinical lead;
2. hospital medical director or COO;
3. quality/research lead;
4. IT/HIS/integration owner;
5. information security/privacy owner;
6. procurement/finance owner;
7. clinical informatician or biostatistician;
8. NRB/global expert in interoperability, clinical safety or critical care.

## Hospital outreach

### Email

**Subject:** 45-minute ICU workflow and data-readiness discussion—no patient data

Dear [Name],

I am building PredictRx Sentinel, a hospital-local ICU workflow and
data-quality command centre. It connects fragmented observations, makes missing
or uncertain data visible, supports structured handoff and evaluates a frozen
sepsis-risk model silently. It is a research prototype, not approved for
clinical use, and we are not asking staff to act on a score.

Could we hold a 45-minute problem interview with an ICU and IT representative?
We need no patient records. We want to understand current handoff, data-quality,
integration and approval constraints. We will return a one-page findings
summary and will not use your hospital's name without written permission.

If there is a fit, the next step would be a separately scoped paid-readiness
workshop—not automatic access to data or a clinical deployment.

Regards,
[Founder name, role, phone, email]

### WhatsApp / LinkedIn

Hello [Name]—I am building PredictRx Sentinel, a hospital-local ICU
workflow/data-quality product. I am doing short problem interviews, not
requesting patient data or selling a clinical alert. Could you or the right ICU
/ IT person give 30–45 minutes to explain current handoff, source systems and
approval barriers? I can send a one-page brief first.

### Follow-up cadence

- Day 0: personalized message and one-page brief.
- Day 3: one short follow-up with two proposed times.
- Day 8: ask for referral to ICU/IT/quality owner.
- Day 15: close politely; do not repeatedly message.
- Within 24 hours of a meeting: send factual summary and corrections request.
- Within 7 days: ask for the exact next decision, owner and date.

## 45-minute problem interview

Do not demo for the first 25 minutes.

### Opening — 3 minutes

- confirm research/discovery purpose and note-taking consent;
- state that no patient data is requested;
- ask permission separately before naming or quoting the participant.

### Current workflow — 12 minutes

- Walk me through one ICU admission and one shift handoff.
- Where are observations, labs, medications and bed moves recorded?
- Which step creates the most delay, duplicate work or uncertainty?
- Tell me about the last time missing, late or mismatched data caused rework.
- What is used today, and why has the problem remained unsolved?

### Consequence and priority — 8 minutes

- Who feels this problem most? How often?
- What measurable operational consequence matters?
- Which current project would this compete with?
- What would make this not worth solving?

### Systems and feasibility — 10 minutes

- Which HIS/EHR/LIS/monitor vendors and versions are used?
- Are HL7 v2, FHIR, API, CSV or database extracts available?
- Who owns the patient, encounter, ward and bed identifiers?
- Where must data run and remain?
- Who approves security, ethics/research and data use?

### Buyer and next decision — 8 minutes

- Who can sponsor a one-ICU readiness engagement?
- Who owns budget and procurement?
- What evidence is required before payment?
- Would a paid readiness workshop be considered? Why or why not?
- What exact next meeting or artifact would move this forward?

### Close — 4 minutes

- read back the top three findings;
- ask what was misunderstood;
- request one referral;
- agree owner, action and date.

## 90-minute cross-functional workshop output

Invite executive sponsor, ICU, quality/research, IT/integration,
security/privacy and procurement/ethics representation.

Produce one signed or email-confirmed page containing:

- problem statement and current alternative;
- affected roles and operational baseline to measure;
- in-scope unit, systems and intended use;
- prohibited uses, including no bedside reliance;
- source feasibility and accountable source owners;
- approval/procurement path;
- success, stop and data-closeout criteria;
- next decision, owner and date.

## No-patient-data source inventory

Record only system metadata:

- hospital and unit name, with permission status;
- vendor/product/version and deployment owner;
- source type: EHR/HIS, LIS, monitor, ADT, pharmacy, manual;
- interface type and transport;
- message/resource/file names;
- available non-production schema or synthetic sample;
- identifier types and issuer namespaces;
- ward/bed master owner;
- timestamp format, timezone and clock source;
- units/codes/terminology and local dictionary owner;
- expected frequency, delay and downtime behavior;
- historical extract availability and retention;
- test environment, network and certificate requirements;
- support/vendor contact;
- required approvals and next technical action.

Do not copy real patient names, identifiers, dates, values, screenshots or free
text into discovery notes.

## Interview evidence record

- interview ID/date/mode:
- participant name/title/organization:
- permission to name: yes / no / pending
- permission to quote: yes / no / pending
- conflict or commercial relationship:
- problem in participant's words:
- recent concrete example:
- current workaround/product:
- frequency and measurable consequence:
- buyer/budget owner/procurement route:
- source systems and owners:
- objections and disconfirming evidence:
- requested product capability:
- willingness-to-pay signal: none / meeting / quote request / paid readiness
- next action, owner and date:
- founder interpretation—clearly separated from direct evidence:
- participant correction/confirmation date:

## Non-binding letter of intent

**Non-binding expression of interest**

Date: [date]

[Hospital legal name] is interested in evaluating whether PredictRx Sentinel
could support ICU workflow, data-quality and retrospective/silent research
objectives for [unit]. The parties intend to explore a scoped [paid readiness
workshop / SafeLaunch pilot] covering [scope].

Any project is conditional on mutually acceptable technical scope, pricing,
procurement, security, privacy, data-use, ethics/research, legal and clinical
safety approvals. This letter does not authorize patient-data access, clinical
use, model-generated alerts, public use of the hospital's name/logo, purchase
or exclusivity. Except for any separately signed confidentiality provision,
this letter is non-binding and either party may stop discussions.

Proposed next decision: [decision] by [date].

For hospital: [name, authorized title, signature/date]

For PredictRx: [name, title, signature/date]

Name/logo may be disclosed publicly: yes / no / separate written approval

## Paid-readiness discussion

Say:

> Before asking for clinical data or an implementation commitment, we offer a
> fixed-scope readiness engagement. It maps workflow, sources, governance and
> deployment constraints and ends with a go/redesign/stop recommendation. It
> does not enable bedside AI. Would your organization consider paying for that
> decision-quality work? Who approves the budget and what deliverable would
> justify it?

Then test:

- fee range and tax/procurement constraints;
- internal approval threshold;
- required vendor registration;
- payment milestone and acceptance owner;
- whether pilot cost can be budgeted this cycle;
- reasons for no—record them without negotiating against yourself.

## Clinical/informatics adviser review letter

I, [name, credentials, role/affiliation], reviewed [artifacts and version] on
[date] for [hours/method]. My contribution covered [clinical workflow /
clinical safety / informatics / biostatistics / human factors].

I reviewed the intended use, prohibited uses, key hazards, evidence limits and
proposed next validation step. My principal findings are:

1. [finding]
2. [finding]
3. [finding]

Required corrections or conditions: [items]

This review is / is not an endorsement. It is not regulatory approval,
institutional approval or proof of clinical benefit.

Conflicts/compensation: [details]

Permission to name reviewer and affiliation: yes / no / limited to [scope]

[signature/date/contact]

## NRB/global collaboration memo

**Collaborator:** [name, country, affiliation, expertise]

**Bounded contribution:** [for example, review FHIR mapping and provide a
written gap report; review the statistical analysis plan; conduct threat-model
workshop; compare one target country's procurement/regulatory path]

**Inputs and dates:** [artifacts, meetings, start/end]

**Deliverable:** [specific, reviewable output]

**Acceptance evidence:** [link/hash/date]

**IP/confidentiality/conflicts/compensation:** [terms]

**No implied claims:** participation is not clinical, institutional or
regulatory endorsement.

**Permission to name:** yes / no / exact permitted wording

[both parties sign/date]

## Evidence rules

- count an interview only when notes identify a participant, date, concrete
  example and next action;
- count an LOI only when an authorized external person signs it;
- count an adviser only when a defined review was delivered;
- count NRB collaboration only when an actual contribution is accepted;
- report “sent,” “meeting booked,” “under review” and “signed” as different
  states;
- preserve refusals and negative evidence;
- redact personal data in public Congress material;
- never backdate, pre-fill external findings or imply approval.

