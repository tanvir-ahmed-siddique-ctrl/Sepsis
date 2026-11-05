# Deployment innovation plan — 5 November 2026

## Decision

PredictRx's defendable opportunity is a **hospital-specific path from unreliable source data to governed silent evaluation**, with useful ICU charting, handoff and data-quality work before any clinical AI claim. A model score alone is not the invention. The model is frozen; the deployment system needs to show when *not* to score, when a source is late, what data was used, and who is accountable for review. These are design hypotheses, not proven clinical benefits or a claim of novelty over every competitor.

The research reports supplied by the founder are planning inputs. This plan checked the high-impact external claims against primary sources. The public demo uses generated/replayed data; no hospital integration, prospective Bangladesh validation, paying customer, regulatory clearance or outcome improvement is established.

The supplied competition PDF text describes a five-part 20-point final rubric, while an earlier portal snapshot listed six weighted criteria. Verify the current official portal before assigning score targets; this plan addresses the shared themes rather than treating either snapshot as a guaranteed scoring rule.

## Why adoption is hard, and the product answer

| Barrier | Product answer | Evidence needed at a site |
|---|---|---|
| Too many false alerts | Keep scores silent during commissioning; count simulated alerts per 100 patient-hours, repeated alerts per encounter, positive predictive value with uncertainty and missed cases; set an alert budget with the clinical team. Deduplicate and route to the designated on-shift owner. Do not quietly suppress a score without a reason and deadline. | Local adjudicated outcomes, present workflow baseline and alert-review time. |
| Clinician distrust | Show source, observed time, missing signals, model version, explanation and an abstain/verify-data path. Review false positives and misses with nurses and physicians; record dissent and changes. | Task observation, training completion, feedback and signed clinical governance decision. |
| Fragmented HIS/LIS/monitors | Use the existing Connection Ladder: manual/CSV/HL7/FHIR/vendor adapter as the source permits. Map all routes into one observation contract, quarantine unknown codes/units, and prove a sample message through to chart and audit. | Named source owner, test interface, field-level mapping, timestamp and correction/merge tests. |
| Intermittent vitals and labs | Treat labs as event-driven, not hourly. Preserve observation time and receipt time, carry prior values only within documented feature limits, show freshness, and abstain when required vitals are absent. Never invent a CBC/lactate value or claim continuous monitoring when readings are manual. | Per-variable coverage and lag by shift, source and patient-hour; comparison with model training distribution. |
| Local performance can change | Measure local discrimination, calibration, prevalence, burden and subgroup uncertainty before clinical use. Keep model artifact and thresholds frozen for the current protocol. A change is a separately versioned study and release. | Prespecified cohort/labels, sufficient adjudication, held-out evaluation and approval. |
| Sites lack IT capacity | Sell a bounded installation and support service: source inventory, mapping, local deployment, backup/restore, training and monthly feed review. A small site may need offline charting first. | Measured engineering days, training uptake, restore result and named hospital owner. |

The [external validation of a widely deployed sepsis model](https://pubmed.ncbi.nlm.nih.gov/34152373/) reported AUROC 0.63 and substantial missed cases and alert burden at one health system. That demonstrates why transfer and workload must be tested; it does **not** prove this product is superior. [ONC SAFER guidance](https://healthit.gov/clinical-quality-and-safety/safer-guides/) likewise treats patient identification, CDS monitoring and clinician communication as safety work, not just interface features.

### Founder a–h delivery ledger

| Request | Working product now | Proof still required |
|---|---|---|
| a. False alarms and fatigue | Threshold-crossing alert creation, active-alert deduplication, TrustGate, silent burden metrics, local monitoring action queue. | Site-specific adjudication and measured staff burden; no claim of fewer false alarms yet. |
| b. Doctor/nurse trust | Explanation, freshness, provenance, bedside feedback and audited ownership. | Observed usability sessions, training completion and independent clinical review. |
| c. Sparse data and readiness | Required-vital freshness and abstention, measurement-habit check, new hospital source inventory with hourly cadence gaps. Labs remain event-driven. | Actual site source inventory, approved data profile and local missingness analysis. |
| d. Integration support, training and drift | Connector health, mapping registry, audit, local pilot metrics/action queue and patient-free fleet operational findings. | A staffed support process, hospital training record, outcome labels and prespecified drift/recalibration protocol. Fleet cannot infer clinical performance. |
| e. SWOT, demographics, revenue, roadmap | This plan and the business model define hypotheses and stop gates. | Buyer interviews, paid procurement evidence and real unit costs. |
| f. Easier integration | One canonical observation contract, Connection Ladder and source-inventory next actions. | Timed deployment at independent hospitals; vendor-tested mappings. |
| g. Legal path | Intended-use boundary, access/audit/retention controls and jurisdictional checklist in the runbooks. | Qualified counsel, institutional approvals, executed agreements and any required regulator decision. |
| h. Different or legacy HIS | FHIR, HL7, CSV, native JSON, vendor adapter and manual chart paths; unrecognized data quarantines. | Conformance tests against each actual vendor/interface and identity correction workflow. |

## The integration offer, end to end

1. **No-patient-data readiness check:** identify ICU clinical owner, IT/source owner, LIS, HIS, monitor gateway, export rights, recording cadence, IDs, timestamps, staff escalation, network/hosting and governance route. Produce a red/amber/green source inventory and a fixed-scope quote.
2. **Synthetic commissioning:** run sample messages through one chosen adapter, mapping registry, validation, quarantine, chart, audit and restore test. Confirm unit conversion and late/corrected result behavior with the site. “FHIR compatible” alone is not a connection; [FHIR Observation](https://hl7.org/fhir/R4/observation-definitions.html) carries clinically relevant time and explicit absence reason.
3. **Bounded retrospective study:** after authorization, use local records to test missingness, label quality, discrimination, calibration, simulated burden and subgroups under a written analysis plan. A poor result leads to hold/redesign, not an automatic threshold change.
4. **Silent pilot:** score without interruptive bedside alerts; review operational metrics daily and adjudication weekly. Clinical work uses the flowsheet/handoff while the AI remains a study output.
5. **Live alert consideration:** only after adequate local evidence, regulatory/institutional decisions, clinical ownership, tested delivery/escalation and the product's readiness gates. This is a future decision, not a deployment promise.

The minimum adapter handoff is source identifier, encounter mapping, observation code, unit, value, effective time, receipt time, status/correction and provenance. For a legacy system, prefer a hospital-controlled outbound export or sidecar; direct database access is a last-resort, read-only, contracted exception. If there is no digital feed, offline bedside charting can be useful, but it does not magically create model-ready hourly data.

## Operational monitoring, and what fleet cannot know

Hospital-local monitoring should track feed lag, mapping failures, duplicates, missing required vitals, score/abstain mix, review time, simulated alert burden, adjudicated sensitivity and calibration when labels exist. Use weekly trend review and predefined stop limits, with the clinical lead owning clinical interpretation. A statistically meaningful drift or calibration claim requires a baseline, enough observations and outcomes. A change in mean score alone is only a *signal to investigate*.

The vendor fleet receives signed, allowlisted site metadata only: heartbeat age, database/writer/audit condition, release/model hash, readiness count and connector circuits. It can raise **operational** attention items. It cannot calculate hospital-level sensitivity or inspect patient records from the fleet. Any shared performance report requires a separate hospital-approved, aggregate reporting design and disclosure review. This protects the on-premises data boundary.

## Customers, users and commercial hypothesis

**First buyer to test:** a private adult-ICU hospital/group with an executive budget owner, ICU clinical lead, nursing lead and IT owner. **Daily users:** shift nurses, duty doctors, ICU leads and quality/research reviewers. **Technical users:** HIS/LIS/interface and security staff. A public/district site may need a donor or procurement path and a lighter workflow-only phase. These are candidate segments, not measured demand.

Keep three separate prices in every quote: fixed readiness assessment, bounded one-ICU integration/pilot, and recurring workflow/data-quality/support subscription. The [business model](./business-model.md) has discovery ranges; these are unvalidated. Include training and initial mapping in the pilot scope, but price extra interfaces, on-site support, repeated recalibration studies and SLA tiers explicitly. Do not offer indefinite free retraining; each model change incurs evaluation, governance and support cost. Track total customer cost and deployment days, not just subscription margin. Consider a paid assessment credited against the pilot if the buyer asks for lower initial risk; measure whether it improves conversion.

**Sales proof required:** interview notes with consent, one no-patient-data source inventory, a buyer/budget/procurement map, a written scope/quote and, ideally, a paid assessment or written interest. A clinician conversation is workflow discovery, not clinical validation or an endorsement. Training should be evidence-based and available to all relevant staff, with transparent conflict-of-interest handling; adoption cannot depend on personal inducements.

## SWOT for the current stage

| Strength | Weakness | Opportunity | Threat |
|---|---|---|---|
| Frozen, benchmarked model; source mapping, provenance, audit, readiness and silent-pilot workflow already in code. | No Bangladesh validation or outcome proof; no live site; single active writer; untested vendor interfaces; commercial assumptions. | Hospitals may buy traceable charting, data quality and research operations before considering alerts; reusable adapters across sites. | Existing HIS/CDS vendors, long procurement, weak source data, alert fatigue, regulatory obligations, security incidents and model transfer failure. |

Do not claim a moat from the model alone. Potential defensibility is repeatable field mapping, source-quality evidence, governance workflow, implementation efficiency and trust earned through measured use. Each must be shown at more than one site.

## Five-to-ten-year direction with stop gates

| Period | Measurable target to test | Stop or change course if |
|---|---|---|
| 0–12 months | 8–12 documented discovery interviews; 2 cross-functional site workshops; 1 source inventory; 1 paid/cost-covered readiness assessment; 1 approved silent study if a hospital agrees. | No buyer owns the problem, no source can support a useful workflow, or approvals are unavailable. |
| Years 2–3 | Repeat one-ICU setup at 3 independent sites; record deployment days, mapping reuse, support cost, renewals and local validation results. | Integrations remain bespoke and uneconomic, or the model fails local safety/utility gates. Keep the workflow/data product if it has measured value. |
| Years 4–5 | Multi-site product with documented security/recovery tests, support SLAs, interoperable adapter packs and country-specific regulatory decisions before clinical claims. | No repeatable retention, unsafe alert burden, or insufficient local clinical evidence. |
| Years 6–10 | Expand only where a country/site can supply governance, service capacity and data; compare outcomes in properly designed studies before marketing patient benefit. | Expansion cannot preserve local performance, privacy, support quality or economics. |

All counts above are **planning milestones**, not forecasts or achievements. The company should report monthly pipeline conversion, deployment days, mapping reuse, recurring gross margin after support, trained active users per shift, data-quality trends, safety events and renewal intent. Clinical metrics remain local and separate from commercial KPI pressure.

## Legal and safety workstream

For each country, obtain qualified advice on product classification, intended use, research/ethics review, data protection, hosting, cross-border transfer, procurement, liability/insurance, incident duties and marketing claims. Contract for roles, source access, data ownership, retention, audit, support, downtime, change control and exit/backup. A contract cannot erase responsibility for an unsafe product; the practical protection is a clear scope plus evidence, testing and incident response. The [WHO AI health guidance](https://www.who.int/publications/i/item/9789240029200) centers human oversight, transparency and accountability. The [US FDA's 2026 CDS guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software) is relevant only to a US pathway and does not determine Bangladesh classification.

## Immediate engineering sequence

1. Harden fleet metadata validation and show actionable operational failures (this change set).
2. Add a hospital-local, versioned source-inventory record and mapping sign-off tied to a named site owner; test against an actual consenting vendor sample.
3. Add a repeatable commissioning report that measures data coverage/freshness and a no-score case without touching the frozen model.
4. Run restore, load/soak, access and incident exercises; fix the single-writer operational limits before calling the stack highly available.
5. Obtain external workflow, regulatory and clinical evidence before expanding claims or alert exposure.
