# PredictRx: adoption business and operator control blueprint

Status: decision document and implementation ledger, 6 November 2026. Commercial numbers below are hypotheses, not sales, contracts or forecasts. No hospital deployment or clinical benefit has been established.

**Implemented locally:** the separate fleet console now persists typed agreement, subscription, invoice, contact, support and decommission-request records in SQLite; writes require the private console token and a reason, and each create/update is audited. Public fleet reads cannot access this ledger. Hospital clinical data and patient records remain outside it. The operator UI, accounting-provider integration, customer onboarding, entitlement enforcement, approval workflow and hospital-side decommission execution are still open work.

## Thesis and innovation

The model is an ingredient. The saleable product is a repeatable path from an unreliable hospital data environment to a governed, measured ICU workflow. The differentiation to prove is **the hospital onboarding system**: source fingerprint → mapping/quarantine → model abstention when inputs are unreliable → silent evaluation → staffed clinical review → monitored operation. This directly addresses why good retrospective models do not automatically become useful clinical systems. Independent validation of a widely deployed sepsis model found poor external performance and substantial alert burden, so model accuracy on its development dataset cannot be the commercial claim ([Wong et al.](https://jamanetwork.com/journals/jamainternalmedicine/fullarticle/2781307)).

The first buyer hypothesis is a digitally capable private or academic adult ICU in Dhaka or Chattogram, with a clinical owner, IT/interface owner, procurement sponsor and approval route. The daily users are nurses and physicians. The first sale is a **paid readiness assessment** with an explicit stop option. Do not promise a live alert licence at the start of a conversation.

## Offer and adoption ladder

1. **Readiness package:** fixed-scope source inventory, identity/timestamp contract, sample export, mapping and security assessment. Deliver a signed gap report with estimated integration effort and a go/no-go decision. Fee hypothesis: ৳3 lakh; test with buyers.
2. **Commissioning:** hospital-approved synthetic messages through one adapter and quarantine; ten representative examples per required field; correction/late-message and downtime drills. A site with paper observations may start with structured bedside entry. Commissioning proves plumbing, not model transfer.
3. **Silent evaluation:** institutional permission, local data profile, blinded scoring, prespecified analysis, clinician review, alert burden and subgroup report. Fee hypothesis: ৳5 lakh for six months, subject to study scope and approvals. The hospital can stop when data or performance is inadequate.
4. **Implementation:** unit workflows, users/SSO, training by shift, incident/restore exercises and readiness sign-off. Fee hypothesis: ৳6 lakh; quote connector work separately if scope exceeds the standard pack.
5. **Annual operation:** per-site licence for software, monitored feeds, audit, release management and an agreed support tier. Fee hypothesis: ৳12 lakh/year for one ICU. Additional units, adapters, 24/7 support and approved model maintenance are separate line items. Do not charge per alert or per patient.

These hypotheses come from the handoff brief and require buyer interviews and actual cost accounting. The contract should specify deliverables, acceptance criteria, support hours, data controller/processor responsibilities, downtime, liability/insurance, exit and verified deletion. A subscription expiry must trigger commercial follow-up and a continuity period; it must not silently disable bedside safety workflows.

## Economics and proof of demand

Track each lead from discovery → source assessment → budget owner → procurement → signed scope → paid pilot → approved deployment → renewal. Record an objection and next action for every lost lead. A positive clinician opinion is useful workflow feedback, not purchase intent. An LOI is not revenue. First-year contribution per site equals implementation fee + licence − direct integration cost − support/hosting cost; do not present ARR without signed recurring contracts. Price changes require a cost ledger: engineer days per adapter, hospital training hours, support incidents, on-site travel, monitoring, cloud/on-prem infrastructure and legal/compliance cost.

For a competition submission, the measurable business experiment is 8–12 buyer/clinical/IT interviews across at least two institutions; 1 completed source inventory; 1 priced scope reviewed by procurement; and 1 paid or cost-covered readiness assessment. Report actual counts and quotes only after they occur.

## The operator control plane to build

Keep clinical data in each hospital. Vendor records contain site ID, legal customer name, billing contact, contract dates, plan, entitlements, invoice/payment references, support owner, implementation stage, contact activities, signed release and patient-free health heartbeat. Every mutation needs an actor, time, reason and before/after audit record. The control plane has separate operator authentication and cannot issue hospital clinical roles.

The founder dashboard should show **actionable exceptions**: stale heartbeat, failing feed, broken audit chain, model hash mismatch, gate regression, renewal due, unpaid invoice, unresolved support ticket and contract nearing expiry. Heartbeats can identify technical risk; they cannot measure local sensitivity or calibration without adjudicated outcomes. Clinical performance summaries may leave a hospital only under an explicit agreement, aggregation rule and governance review. Default fleet telemetry remains patient-free.

Required business entities and controls:

- `customer`: legal name, jurisdiction, billing details, customer status; no patient fields.
- `site`: stable site ID, owner, environment, lifecycle, approved release and signing-key fingerprint.
- `agreement`: version, effective/expiry dates, scope, approvals, document reference and renewal notice period.
- `entitlement`: enabled units/connectors/support tier, activation and grace dates; changes versioned and audited.
- `invoice`: amount/currency, due/paid state, external accounting reference; never store card data.
- `contact_activity`: organization contact role, channel, date, summary, next action, owner; restrict access and retention.
- `support_case`: priority, site, technical symptom, owner, SLA and resolution; no chart text or patient identifiers.
- `decommission_request`: hospital authorization, export receipt, backup verification, revoked keys, retention hold and final evidence. Remote deletion must not execute solely from the vendor console. A hospital-side decommission tool verifies backup first.

Control actions are constrained: operator can pause **new deployments/updates** or support access, but cannot unilaterally activate clinical alerts, erase clinical data or silently turn off an operating ICU. Hospital clinical/governance sign-off remains required for live alerting. A break-glass support path, if ever built, needs explicit hospital authorization, narrow duration and complete audit.

## Impact and evidence plan

Report four separate layers: (1) connector reliability and data coverage; (2) model discrimination/calibration and alert burden in the local cohort; (3) workflow uptake and review time; (4) clinical outcomes in an appropriately designed study. Do not collapse these into a single “lives saved” number. Prespecify missingness, subgroup checks, incident thresholds and rollback before a silent pilot. Run structured training and usability sessions with nurses as well as physicians. WHO health-AI guidance emphasizes human oversight, transparency and accountability ([WHO](https://www.who.int/publications/i/item/9789240029200)).

## International and legal route

For each country, obtain qualified local advice on intended-use classification, research/ethics review, privacy/lawful basis, hosting/cross-border transfer, security, clinical responsibility, insurance, incident reporting, procurement and marketing claims. The hospital's consent/authority is not replaced by a vendor contract. Build one jurisdiction dossier before marketing there. FHIR support is an adapter capability, not a guarantee that a hospital can export usable data; Observation time, value, status and absent reason require local mapping and validation ([HL7 FHIR Observation](https://hl7.org/fhir/observation-definitions.html)).

## Roadmap and stop gatesshopb koroooo

- **0–12 months:** buyer discovery, source inventories, one costed assessment, one approved silent study if a hospital agrees. Stop clinical alert plans if no reliable source, owner, lawful route or useful local performance.
- **Years 2–3:** repeat one-ICU deployment in three independent sites; compare implementation days, adapter reuse, support cost, silent-study results and renewal. Stop expansion if integration remains bespoke or the alert burden is unsafe.
- **Years 4–5:** independent security/recovery evidence, support SLA, approved release process, country-specific regulatory decisions and documented outcome studies before benefit claims.
- **Years 6–10:** expand geography only where local support, evidence, lawful data handling and unit economics are repeatable. Do not count projected sites as customers.

The immediate engineering order is: separate authenticated vendor control plane with audited commercial ledger; invoice/entitlement lifecycle; support/contact workflow; site-side safe decommission request; then customer-tested operator UI. None of these records should be fabricated for judging.
