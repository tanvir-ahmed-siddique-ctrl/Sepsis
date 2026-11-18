# Real-world action plan (founder / external stakeholders)

This document lists work that **cannot be completed inside the repository alone**. Software in this tree may be implemented, tested, and runtime-verified locally; the items below require people, institutions, or approvals outside the development environment.

Do **not** treat anything here as done because code exists. Do **not** claim hospital validation, regulatory approval, outcome improvement, or production clinical readiness until the corresponding row is actually completed with evidence.

---

## How to use this list

| Column | Meaning |
|---|---|
| Needed because | Why the product cannot honestly claim readiness without it |
| Who | People or organizations that must act |
| Prerequisites | What must exist before that action starts |
| When | Earliest sensible time relative to product milestones |

---

## 0. Founder commercial decisions (software is configurable; policy is not)

Resolve items in `docs/business/founder-decision-register.md` before treating them as approved company policy: hardware stock vs OEM, leasing, managed-IT inclusions, complimentary training scope, seminar funding, master-agreement shape, and any cross-site research ambitions. Unvalidated BDT pricing hypotheses must not appear on the public site (`docs/business/pricing-assumptions.md`).

Calendar provider credentials are required before consultation booking can show live availability; until then preferred windows stay pending confirmation in the Vendor Control Plane.

## 1. Hospital partnership and site selection

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Written partnership / MoU with at least one ICU-capable hospital | Local deployment, data access, and clinical feedback require institutional consent | Founder + hospital leadership (medical director, CIO/IT, legal) | Pitch materials, honest scope (decision support, not autonomous treatment), security overview | Before any live HIS connection or pilot protocol |
| Named ICU clinical champion (consultant) | Workflow fit, alert thresholds, and feedback quality need a clinician owner | ICU consultant + nursing lead | Partnership MoU | Immediately after site selection |
| Named hospital IT / EHR owner | Connector deployment, network rules, identity provider, and change windows | Hospital IT + vendor deployment engineer | Site assessment maturity ≥ M2 | Before technical commissioning on hospital network |

---

## 2. Permissions, ethics, and data access

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Written permission to receive/process hospital clinical data (or to run in-hospital only with no export) | Legal basis for processing; repository must not invent consent | Hospital legal / DPO + founder counsel | Data-flow diagram, DPIA draft in `docs/` | Before any non-synthetic data leaves hospital control—or before on-prem install if counsel requires it |
| Ethics / IRB / institutional review (if required for pilot measurement) | Prospective evaluation and outcome claims need ethics pathway where applicable | Hospital ethics board + clinical PI | Protocol outline, risk/benefit, consent model | Before prospective pilot data collection for publication or regulatory use |
| De-identification / data-minimization rules approved by hospital | Prevents accidental PHI in vendor systems, tickets, or telemetry | Hospital IT + security + vendor security/compliance role | Telemetry allowlist already in product | Before enabling any outbound metadata |

---

## 3. Clinical validation and evidence

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Retrospective validation on hospital’s own historical data (or locked retrospective extract under agreement) | PhysioNet / synthetic evaluation ≠ local performance | Clinical PI + data manager + vendor ML under hospital rules | Data access agreement; frozen model SHA recorded | After data access; before live interruptive alerting |
| Prospective silent / shadow-mode pilot with alert-burden metrics | Judges and hospitals need operational evidence, not only AUROC | ICU team + nursing + vendor pilot lead | Soft-landing / silent mode configured; feedback inbox used | After retrospective check and staff training |
| Independent clinical review of false-positive / false-negative cases | Safety case and TrustGate thresholds need clinical judgment | ICU consultants | Case review worksheet; provenance UI available | During shadow pilot |
| Outcome measurement plan (LOS, sepsis bundle timing, alert response time)—measured, not claimed early | Commercial and competition “impact” scores require measured baselines | Hospital QI + clinical champion | Baseline KPI sheet (`docs/evidence/impact-kpi-baseline.md`) | Define before pilot; report only after measurement period |

---

## 4. Regulatory, legal, and compliance

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Qualified legal review of contracts, BAAs/DPAs, and marketing claims | Draft contract text in-product is not legal advice | External counsel (BD and any export market) | Commercial templates marked draft | Before first paid contract or public compliance claim |
| Regulatory pathway advice (e.g. DGDA / SaMD classification where applicable) | Software as clinical decision support may be regulated | Regulatory consultant + founder | Intended use statement; risk classification draft | Before commercial clinical claims or paid clinical pilots that require it |
| Security questionnaire / pen-test for hospital onboarding | Hospitals will not accept “we have auth” alone | Vendor security + independent tester | Hardened deployment guide; audit logs | Before production cutover |
| Insurance / liability allocation (malpractice vs product) | Clinical alerts create liability questions | Counsel + hospital risk | Intended use: clinician-in-the-loop | Before go-live |

---

## 5. Infrastructure and on-site deployment

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Hospital-approved hardware (or VM) for local clinical plane | Product is designed for hospital-local inference and data plane | Hospital IT + procurement + vendor deployment | Site assessment, bed/unit counts, licence bed-band | After contract / licence |
| Network isolation rules, DNS, TLS certificates | Offline-capable clinical use needs local name/TLS | Hospital network team | Architecture diagram | During installation window |
| HIS / LIS / monitor interface credentials and sample messages | Integration Hub cannot map what it cannot see | Hospital IT + interface engine vendor | Connector scopes; test patients | Commissioning phase |
| Backup, restore drill, and key custody on hospital-controlled storage | Disaster recovery is a hospital responsibility | Hospital IT + vendor runbook support | Backup docs in `docs/operations/` | Before clinical go-live |
| ClamAV / malware scanning host policy for document centre | Document uploads need runtime scanner in production | Vendor ops or hospital shared service | `ACCOUNT_DOCUMENT_KEY`, scanner endpoint | Before customer-visible document exchange |

---

## 6. Identity and workforce

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Hospital IdP / local account provisioning policy | Cloud vendor login must not be required for ICU care | Hospital IAM + HospitalAdmin | Local auth docs; role matrix | During installation |
| Shift roster ownership (who updates CSV / assignments) | On-shift strip is useless without operational ownership | Nursing admin / ward clerk | `/staff` workflow training | Before alert escalation by shift |
| Staff training sessions (doctor, nurse, IT) | Alert fatigue and misuse dominate sepsis CDS failures | Vendor training records + hospital educators | Training packs; feedback forms | Before interruptive mode |
| Break-glass / emergency access policy | ICU emergencies need audited exception paths | Hospital CISO + clinical lead | Approval workflow in vendor/hospital policy | Before go-live |

---

## 7. Commercial and customer operations

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Real quotations, contracts, and payment verification process | Portal records are operational metadata, not a payment gateway | Finance/legal + customer procurement | Issued quotes/contracts; bank/receipt process | First paying customer |
| SLA and support hours committed in writing | Ticket severity without SLA is incomplete commercially | Vendor support lead + customer technical contact | Support plan record | At contract signature |
| Licence bed-band agreement matching purchased units | Entitlements must match physical ICU capacity | Sales + HospitalAdmin | Site bed inventory | Before entitlement issue |
| Offboarding / data return procedure executed once | Must be practiced, not only coded | Both parties’ IT + legal | Dual-approval offboarding flow | At contract end or drill annually |

---

## 8. Competition / presentation (Congress and similar)

| Item | Needed because | Who | Prerequisites | When |
|---|---|---|---|---|
| Honest 180-second video with labelled synthetic / de-identified replay | Preliminary submission artifact | Founder | Stable demo URL; no false “live hospital” claims | Before video deadline |
| Public demo kept labelled as evaluation / replay | Judges probe provenance | Founder + whoever operates Render/Docker | `PUBLIC_SIMULATION` / PhysioNet labelling | Continuously |
| No claims of BD ICU outcome improvement without measured pilot | Scoring honesty and long-term credibility | Founder | This action plan | Always |

---

## What the software team can finish without the above

- Role–permission matrix, API enforcement, invitations, approvals, audit chains (vendor/customer).
- Commercial CRM → quote → contract → licence → invoice → payment **record** workflows (no bank integration).
- Hospital-local clinical UI, TrustGate, connectors against synthetic / PhysioNet replay.
- Docker compose evaluation isolation, local backup scripts, documentation, and automated tests.
- Draft regulatory/security documents clearly marked as **not approved**.

## What must never be claimed from repo work alone

- “Deployed in N hospitals” / “reduced mortality” / “DGDA approved” / “HIPAA compliant” / “validated on our hospital’s patients” without the corresponding external evidence rows above.
