# Innovation: solving why sepsis ML still is not everywhere

The attraction for judges is not “another sepsis AUROC.” It is that **the
reasons hospitals still cannot adopt sepsis ML are solvable**, and PredictRx
is built as that solution layer. Two barriers dominate. This document states
each barrier, what the world already proved, what we reuse, and what we
invent.

---

## Barrier 1 — EHR / HIS lock-in

### What lock-in actually means

When a hospital runs one vendor’s clinical system, that vendor controls how
data leaves and how third-party AI is allowed in. In the US that vendor is
often **Epic** or **Oracle Health (Cerner)**. In Bangladesh and most LMICs it
is a patchwork of **local HIS + LIS + monitors**, often with weak or no FHIR
surface. TREWS implementers themselves wrote that scaling across dissimilar
EHRs remains hard and pointed to **HL7 / FHIR / SMART** as the way forward.

### Landscape (where what runs)

| Region | Dominant clinical systems (examples) | How AI usually enters today | PredictRx insertion mode |
|---|---|---|---|
| United States | Epic (~majority of large health systems), Oracle Health/Cerner, MEDITECH, athena | Built-in vendor model (e.g. Epic Sepsis Model) **or** third-party via **SMART on FHIR + CDS Hooks** listed in Epic Showroom / Connection Hub | **Mode U1–U2** below — we stay an independent company |
| UK / EU / high-income | Epic, Cerner, local EPR (e.g. SystmOne, Dedalus), national FHIR programmes | SMART/FHIR apps; on-prem inference for PHI | Same SMART/FHIR + hospital-local plane |
| Bangladesh public | OpenMRS+ (~100 public hospitals, mostly on-prem), OpenELIS, national FHIR/HIE work (SHR) | Module or interface engine; LAN-first | **Mode L2–L4** |
| Bangladesh private | Local HIS vendors (e.g. MySoft claiming 300+ hospitals with HL7/ASTM analyzer links; EMSL and others offering HL7/FHIR/DICOM) | Vendor interface if paid; else CSV / paper | **Mode L1–L5** |
| Other LMICs | Mixed OpenMRS/Bahmni, DHIS2 (reporting), proprietary HIS, paper wards | Same ladder | Same ladder |

Sources: Epic Showroom / SMART-on-FHIR + CDS Hooks practice; TREWS multi-EHR commentary; DGHS OpenMRS+ deployment notes; MySoft/EMSL public interoperability pages. Vendor names are market context, not partnerships claimed by PredictRx.

### Why we will NOT “just put the model inside Epic”

If the model becomes Epic’s built-in feature, **Epic owns distribution and
pricing**; PredictRx becomes a one-time license or disappears. Our business
answer:

1. **PredictRx remains the product.** The hospital (or health system) contracts
   with us for readiness, install, silent pilot, and governed alerting.
2. **Epic/Cerner are shells, not owners of our IP.** We plug in through open
   standards Epic already supports for *third-party* apps:
   - **SMART on FHIR** — launch our ICU board inside Hyperspace with OAuth
     patient/encounter context; we read Observations via the hospital’s FHIR
     server; scoring stays on **our** hospital-local (or hospital-approved)
     runtime.
   - **CDS Hooks** — event-driven card (e.g. patient-view) that can deep-link
     into our SMART app (Epic Launch Cards, 2024+) without giving Epic the
     model weights.
3. **Revenue stays with us:** Showroom listing is discovery; the paid work is
   our readiness + site ops + clinical module after gates — same commercial
   shape as today, just a new “U-series” connection tier.
4. **If a US site refuses SMART,** we still offer the **sidecar** (Mode U0):
   HL7/FHIR feed out of their interface engine into PredictRx on their VM —
   Duke Sepsis Watch style — again without handing the model to the EHR vendor.

### Invented product: the Connection Ladder (one story, many floors)

Every hospital climbs only as high as its systems allow. Lower floors always
work; higher floors are nicer UX, not a requirement to score.

| Tier | Name | When to use | How data enters PredictRx | Who we sell to |
|---|---|---|---|---|
| **L0** | Bedside chart | Paper / no interface | Nurse enters vitals/labs in `/chart` (offline queue) | Any ICU |
| **L1** | Controlled file drop | HIS can export CSV/Excel nightly or per shift | `POST /v1/integrations/csv/lab` or mapped native JSON batch | BD private HIS without APIs |
| **L2** | HL7 v2 messages | HIS/LIS/monitor speak ADT/ORU (common even when “no FHIR”) | `POST /v1/integrations/hl7v2/oru` (+ ADT); **edge MLLP relay** on LAN | BD MySoft-class analyzer HL7; US interface engines |
| **L3** | FHIR R4 | Modern HIS / national HIE / OpenMRS FHIR module | Bundle / NDJSON ingest | BD public FHIR path; US Epic FHIR |
| **L4** | Vendor Adapter Pack *(invented contract)* | HIS has proprietary REST/DB but no standard | Hospital IT or vendor implements our **minimal adapter** (below) that emits L1/L2/L3 | Local HIS shops (paid adapter SOW) |
| **L5** | Soft-landing sidecar | HIS will not change; clinicians need a second screen | PredictRx is the ICU intelligence UI; HIS stays billing/ADT source via L1–L3 | LMIC private hospitals |
| **U0** | Interface-engine pull | US Epic/Cerner site, Duke-style | Engine pushes HL7/FHIR to our on-prem API | US health systems |
| **U1** | SMART on FHIR app | Epic/Oracle wants in-chart launch | OAuth launch → FHIR read → our scorer | US/EU — **our** Showroom listing |
| **U2** | CDS Hooks + Launch Card | Want interrupt/card without leaving EHR | Hook → our service → card → opens U1 app | US — still **our** IP |

**Already shipped today:** L0–L3, edge MLLP, quarantine, mapping copilot,
conformance evidence. **Invented / specified now:** L4 Vendor Adapter Pack,
L5 Soft-landing positioning, U1/U2 business+architecture path (implementation
roadmap; not claimed as live Epic certification).

### Vendor Adapter Pack (L4) — how we get data when “they have no FHIR”

Many BD HIS vendors *do* have HL7 for analyzers (MySoft public claim: HL7/ASTM
to hundreds of analyzers) but expose weak third-party APIs. When standards are
missing we do **not** scrape the UI as primary design. We require one of:

1. **Outbound HL7 ORU/ADT** from their interface module (preferred; often
   already sold to labs).
2. **Scheduled secure CSV/JSON drop** to a hospital folder our agent watches
   (schema: `docs/adapters/vendor-adapter-contract.v1.json`).
3. **Read-only DB view** they create (MRN, encounter, code, value, unit,
   timestamp) — we never write their DB; hospital DBA owns the view.
4. **Last resort:** structured bedside chart (L0) for the ICU pilot ward only
   — still valid silent evidence, labelled as charting-sourced.

PredictRx never becomes a full HIS replacement. Soft-landing means: **scoring
+ TrustGate + alerts live in our app; registration/billing stay in theirs.**

### Layered data path (say this in the presentation)

```
Hospital sources          PredictRx edge                 PredictRx core
─────────────────         ──────────────                 ─────────────
Monitors / LIS  ──HL7──►  MLLP relay (LAN)  ──ORU──►┐
HIS ADT         ──HL7──►  or CSV/FHIR push           ├──► Validate/map/quarantine
OpenMRS/FHIR    ──R4──►                               ├──► Frozen Run 4 (local)
Paper ward      ──UI──►  /chart                        ├──► TrustGate
Epic/Cerner     ──SMART/CDS (U1/U2) or engine (U0)───►┘         │
                                                                 ▼
                                                    Silent pilot → 9 gates → alert
                                                    Fleet ← metadata heartbeat only
```

Exact commissioning steps: `docs/hospital-onboarding.md`. Judge live surfaces:
`/connection`, `/integration`, `/chart`, `/readiness`.

---

## Barrier 2 — Transfer: calibration & measurement habits

### Why another hospital’s AUROC may not transfer

1. **Case-mix / calibration.** Age, severity and base rates differ. Our own
   Dataset B (distinct public cohort) already shows calibration slope **0.80**
   — probabilities need local recalibration before thresholds mean the same
   thing.
2. **Measurement habits (care-process).** Ablations show much of Run 4’s
   signal is *how often clinicians measure*, not only physiology. A ward that
   charts BP every 4 h vs every 1 h changes feature distributions. This is
   disclosed in `docs/model-card.md`, not hidden.
3. **Code/unit drift.** Same analyte, different codes or units → garbage-in
   unless quarantined.

### Invented product: Transfer Shield

A named bundle of controls (mostly already in the product; named so judges
hear one innovation):

| Shield layer | What it does | Status |
|---|---|---|
| **S1 Freeze** | Model weights immutable; SHA-256 at start-up | Shipped |
| **S2 Quarantine** | Unknown codes/units/implausible values never enter scoring | Shipped |
| **S3 Freshness / Abstain** | Stale or missing required signals → Verify data / Abstain | Shipped |
| **S4 Silent local mirror** | Score for weeks without interrupting; compare to chart review | Shipped (`/pilot`) |
| **S5 Local calibration gate** | Before live: require site calibration report (slope/intercept or isotonic on silent labels); threshold simulation only — never silent re-fit of the forest | Protocol shipped in readiness/pilot; live alerting blocked until gates pass |
| **S6 Habit fingerprint** *(invented monitoring)* | During silent pilot, track per-unit median hours-between measurements for required vitals; flag >2× shift vs commissioning baseline as a readiness failure (“measurement habit drift”) before live | Specified on `/connection`; uses existing freshness signals; gate wording added to readiness narrative |
| **S7 Subgroup stop rule** | >10 pp sensitivity gap vs overall → keep pathway off until governance decides | Shipped (`docs/evidence/fairness-audit.md`) |
| **S8 Context policy** | Pregnancy, comfort care, etc. modulate alerts without editing probability | Shipped |

**We do not “fix transfer” by quietly retraining on hospital PHI in production.**
Any new model version is a new artefact with its own card. Transfer Shield makes
*mismatch visible and blocking*, which is the honest innovation relative to
shipping Epic-style scores everywhere with one global calibration.

### Presentation one-liner

> Sepsis ML is not missing from hospitals because the math is unsolved. It is
> missing because of EHR lock-in and unsafe transfer. PredictRx sells the
> unlock: a Connection Ladder from paper to SMART-on-FHIR without giving our
> model to the EHR vendor, and a Transfer Shield that refuses to alert until
> local calibration and measurement habits check out.

---

## Non-claims

- No live Epic Showroom listing or CDS Hooks production certification is
  claimed today — U1/U2 are the designed commercial path.
- No contract with MySoft, EMSL, Epic, or Oracle is claimed.
- Transfer Shield does not claim Bangladesh outcome validation.
