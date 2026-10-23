# International deployment validation — timeline & pathway map

ML sepsis systems **have already been put into real hospitals**. This document
does not claim PredictRx is one of those deployments. It shows that the
pathway we built (standards connectors → mapping/quarantine → silent
evaluation → human-gated alerts → hospital-local data) is the same pattern
successful (and cautionary) international deployments published — so a judge
can treat our architecture as **pathway-validated**, not invented in a vacuum.

PredictRx itself remains a research prototype: no Bangladesh hospital install
and no clinical-use approval are claimed.

## Timeline (published go-lives and studies)

| When | What happened | Where | How data entered the model | What happened before live alerts |
|---|---|---|---|---|
| 2018 (ongoing build) | TREWS developed; early hospital use begins | Johns Hopkins–affiliated hospitals | Continuous EHR stream: vitals, labs, medications, clinical documentation | Configured as **non-interruptive** EHR alerts; clinician must confirm or dismiss |
| **5 Nov 2018** | **Sepsis Watch go-live** after silent period | Duke University Hospital ED (~1,000-bed flagship) | **Epic web services** (off-the-shelf + custom): pull nurse-verified EHR data every **5 minutes** into an external DB; model updates hourly; on-premise infra | **3-month silent period** on live data: remapping, end-to-end test, threshold tuning, clinical leaders reviewing cases with delay |
| 2018–2019 | Sepsis Watch pilot → expanded | All three Duke Health EDs (after pilot Nov 2018–Jun 2019) | Same Epic pull pattern; RRT nurse tablet + web app workflow | Silent period already completed at flagship before scale-out |
| 2018–2020 study window | TREWS prospective multi-site evaluation | **Five** hospitals (2 academic + 3 community), shared EHR | EHR-embedded analytics + alert → dashboard → low-friction orders | Engagement measured: ~**89%** of alerts evaluated; confirm ≤3 h associated with faster antibiotics and lower adjusted mortality (*Nat Med* 2022) |
| ~2015–present | Epic Sepsis Model shipped inside Epic EHR | Epic reported ~**170 customers / hundreds of US hospitals** | **Native EHR embed** — no separate “connector product”; scores computed inside the chart | Often **insufficient independent local validation** before wide use → external validation AUROC **0.63**, alerts on 18% of hospitalizations, 67% of sepsis missed (Wong, *JAMA Intern Med* 2021) |
| 2022 commentary | Multi-EHR scale called out as hard | — | Authors note HL7 / **FHIR** / SMART as the portable future when hospitals do not share one EHR | Validates why PredictRx ships FHIR + HL7 rather than locking to one vendor |
| 2025 | Bayesian Health (TREWS lineage) system-wide sepsis tool | Cleveland Clinic (public go-live announcement) | Commercial EHR-integrated deployment at health-system scale | Shows the product category continues to expand in high-income systems |

Sources: Sendak et al., *JMIR Medical Informatics* 2020 (PMC7391165); Duke Health referring-physician article on Sepsis Watch; Adams/Henry et al., *Nature Medicine* 2022; Wong et al., *JAMA Internal Medicine* 2021; Cell Reports Medicine / *Med* viewpoints on TREWS deployment lessons; Epic customer-count reporting via contemporary press covering Wong.

## How they connected — three patterns

```
Pattern A — EHR web-service pull (Duke Sepsis Watch)
  Epic EHR ──(web services every 5 min)──► hospital DB ──► model ──► separate web app / RRT workflow

Pattern B — EHR-native alert (TREWS / Epic ESM)
  EHR data plane ──► model inside or beside EHR ──► in-chart alert / dashboard / orders

Pattern C — Standards / multi-vendor (what LMIC + multi-HIS need)
  HIS / LIS / monitors ──(FHIR / HL7 v2 / CSV / MLLP)──► mapping + quarantine ──► model ──► clinical UI
```

Duke and TREWS mostly lived in **Pattern A/B** because US academic centres share
Epic (or one EHR). Cell Reports Medicine commentary on TREWS explicitly says
scaling across **dissimilar** EHRs is still hard, and points to **HL7 and FHIR**
as the path forward. That is Pattern C — and that is what PredictRx implements
with measured connector conformance.

## Map: international lesson → PredictRx control

| Published lesson | Evidence it is real | PredictRx equivalent (verify) |
|---|---|---|
| Pull or stream clinical data continuously, not once | Duke: 5-minute Epic web services; TREWS: continuous EHR monitoring | FHIR Bundle/NDJSON, HL7 ORU, CSV, native JSON, edge MLLP — `docs/evidence/connector-conformance.md` |
| Remap and validate codes before trusting scores | Duke silent period: final data mapping + clinical validation | Mapping registry + human sign-off + quarantine for unknown units/codes |
| Run silently on live data before interrupting clinicians | Duke: **3-month silent period**; Tonekaboni silent-trial protocol (ICU) | Site `silent` mode + nine readiness gates — `/readiness`, `/pilot` |
| Human must engage the alert | TREWS: ~89% evaluated; confirm ≤3 h associated with benefit | Acknowledge / dismiss-with-reason / escalate — `/alerts` |
| On-premise or hospital-controlled compute for PHI | Duke: on-premise, fault-tolerant infra | Hospital-local data plane; vendor sees HMAC metadata only — `/fleet` |
| Wide deploy without local proof can harm | Epic ESM: hundreds of hospitals, external AUROC 0.63, alert fatigue | Frozen hash-verified model; no live alerts until local gates; failures disclosed in model card |
| Portable multi-HIS needs open standards | TREWS commentary: FHIR/HL7/SMART for dissimilar EHRs | Standards-first connectors + conformance run; not Epic-locked |

## What a judge should conclude

1. **Feasibility:** Putting ML sepsis into hospital workflow is not theoretical —
   Duke (2018), TREWS multi-site (evaluated through 2020), Epic-embedded tools
   (hundreds of hospitals), and later commercial expansions prove the category.
2. **Method:** Successful careful deployments used continuous feeds, mapping,
   silent evaluation, and human confirmation — the same sequence PredictRx
   software-enforces.
3. **Differentiation:** PredictRx is not “first sepsis ML.” It is the
   **standards-based, hospital-local, evidence-gated** packaging of that proven
   pathway for sites that do not live inside one US EHR vendor — including
   Bangladesh ICUs.

## Explicit non-claims

- PredictRx has **not** been installed in Duke, Johns Hopkins, Cleveland Clinic,
  or any Bangladesh hospital.
- Citation of these systems is **pathway corroboration**, not endorsement of
  PredictRx by those institutions.
- No mortality or outcome claim for PredictRx is made from TREWS/Duke results.
