# PredictRx Sentinel — investor memo

**Status:** pre-revenue research prototype; no clinical-use approval, hospital
customer, signed LOI or Bangladesh validation is claimed unless separately
documented.

## Thesis

ICU AI fails before inference when fragmented source data, uncertain mappings,
missing observations and unsafe workflows are hidden. PredictRx Sentinel starts
with a hospital-local workflow and data-quality command centre, then lets each
site earn the right to expose alerts through explicit evidence and governance
gates.

The wedge is not “replace the EHR” and it is not “sell an unvalidated sepsis
prediction.” It is a paid SafeLaunch engagement for one ICU:

1. map and validate source data;
2. provide digital flowsheet, handoff, feed-health and quality/research tools;
3. evaluate a frozen sepsis-risk model retrospectively and silently;
4. stop, redesign or advance only through recorded gates.

## Why now

- Bangladesh's ICU capacity is constrained and concentrated. DGHS's January
  2024 government-facility table lists 778 ICU beds in the facilities covered.
- Hospitals increasingly have digital fragments without an interoperable ICU
  operating layer.
- FHIR and HL7 permit a globally reusable canonical architecture, while local
  connectors and hospital-controlled deployment address sovereignty and
  connectivity constraints.
- Buyers need accountable workflow and evidence before they need another
  model-generated alert.

These observations support discovery; they do not prove demand. Interviews,
procurement evidence and a paid design partner are the next commercial gates.

## Product and technical moat

- source-to-canonical validation across FHIR, HL7, CSV, API and bedside relay;
- field-level provenance, quarantine, deterministic deduplication and replay;
- temporal feature parity and hash-verified frozen artifacts;
- calibrated output with Alert, Watch, Verify data and Abstain states;
- technical release gates that separate workflow value, silent research and
  clinical use;
- negative-experiment ledger and versioned evidence retrieval;
- hospital-local identifiable data plane; future founder fleet control plane
  receives only approved operational metadata by default.

The moat hypothesis is cumulative implementation evidence: reusable vendor
mapping packs, deployment playbooks, local validation protocols, workflow
trust and governed integration—not exclusive ownership of LightGBM.

## Buyer, offer and adoption path

**Initial customer:** private hospital or hospital group with an adult ICU, an
executive sponsor, ICU lead and IT owner.

**Offer ladder:**

1. paid readiness and source-inventory workshop;
2. fixed-scope 8–12 week SafeLaunch;
3. recurring workflow/research subscription and support;
4. only after separate evidence and approval, a prospective alert evaluation.

Clinical users never need a founder account. Hospital administrators manage
their users and roles. The founder manages releases, deployment health and
approved support access without default access to patient records.

## Commercial model — assumptions to test

These are scenario inputs, not quotations, bookings or forecasts.

- paid pilot: BDT 300k low, BDT 650k base, BDT 1.2m high-complexity;
- setup/integration, included or itemised: BDT 200k / 350k / 500k;
- recurring per site per month: BDT 75k / 150k / 250k;
- direct recurring delivery cost per month: BDT 45k / 60k / 100k;
- illustrative recurring gross margin: 40% / 60% / 60%.

The visual scenario model is available in the investor-readiness Canvas.

The first three deployments should optimize learning, not headline margin.
Track engineering hours, travel, hardware, interface fees, support load, sales
cycle and collections. A scalable motion exists only if reusable mappings and
remote operations reduce implementation cost without weakening governance.

## Milestones

### Gate 1 — problem proof

- 8–12 structured interviews and two hospital workshops;
- named buyer, budget owner, source owner and governance path;
- one written interest/LOI or paid-readiness decision;
- one clinical/informatics adviser and one contributing NRB/global reviewer.

### Gate 2 — design partner

- signed charter, data-use/security/ethics decisions and source inventory;
- partner mapping acceptance with synthetic/de-identified samples;
- installation, backup/restore and incident drills accepted.

### Gate 3 — local evidence

- retrospective report with uncertainty and prespecified subgroups;
- silent workflow and operational evidence if institutionally approved;
- measured implementation cost and renewal/stop decision;
- no outcome claim from retrospective or silent operation.

### Gate 4 — repeatability

- second site using reusable connector and onboarding assets;
- metadata-only fleet operations;
- independent security assessment and documented remediation;
- prospective clinical-evaluation/regulatory path agreed before any live alert.

## Capital use framework

No financing amount or valuation is assumed. For any proposed round, build a
milestone-based budget within these planning ranges:

- 30–40% product, interoperability and reliability;
- 20–25% clinical validation, biostatistics and human factors;
- 15–20% security, privacy, quality and regulatory work;
- 15–20% deployment, training and customer success;
- 5–10% legal, finance and operating reserve.

Tie release of spending to the gates above. Do not fund clinical-alert scaling
before local evidence and governance support it.

## Principal risks and kill criteria

- **No urgent buyer:** stop broad building if interviews do not identify a
  budgeted problem.
- **Data infeasibility:** redesign scope or stop if provenance, timestamps,
  identifiers or labels cannot support valid evaluation.
- **Low transferability:** remain workflow/research-only if local calibration
  or alert burden is unacceptable.
- **Integration services trap:** narrow supported systems if site-specific work
  cannot be reused.
- **Regulatory/safety uncertainty:** keep scores hidden until qualified review
  and institutional authorization exist.
- **Security or trust failure:** stop data movement on unresolved critical risk.

## Defensible investor ask today

Seek a design-partner introduction, clinical/informatics adviser, FHIR/HL7 and
security reviewers, and milestone financing—not a claim that the product is
ready for clinical-scale sales. Investment readiness improves when one buyer
pays for readiness, not when more speculative features are added.

