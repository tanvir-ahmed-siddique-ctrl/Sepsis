# Auralis — system layers (visual)

> Research prototype · synthetic / PhysioNet replay on the public demo · **not approved for clinical use**.  
> Patient data stays inside the hospital boundary. Vendor sees **metadata only**.

GitHub renders these diagrams on this page. Start here if a judge asks “show me the layers.”

---

## L0 — One picture: hospital-local product

```mermaid
flowchart TB
  subgraph HOSP["HOSPITAL BOUNDARY — on-prem / LAN"]
    SRC["Monitors · LIS · HIS · Bedside chart"]
    CONN["L1 Connectors<br/>FHIR R4 · HL7 v2 · CSV · Vendor adapter"]
    MAP["L2 Mapping + Quarantine<br/>units · LOINC · Bangla terms"]
    FEAT["L3 Features<br/>past-only · 24h window · 673 inputs"]
    ML["L4 Frozen LightGBM Run 4<br/>TreeSHAP drivers"]
    TG["L5 TrustGate<br/>Alert · Watch · Verify · Abstain"]
    MODE["L6 Site mode<br/>demo · silent · live-disabled · live"]
    UI["L7 Clinical workspaces<br/>ICU · Patient · Alerts · Handoff · Ward · Chart"]
    DB[("Local DB + hash-chained audit")]

    SRC --> CONN --> MAP --> FEAT --> ML --> TG --> MODE --> UI
    FEAT --> DB
    ML --> DB
    TG --> DB
    UI --> DB
  end

  subgraph SIDE["Side branch — never edits the risk score"]
    BN["Bangla / local lab names"]
    LLM["Local mapping LLM + RAG retrieval"]
    LOINC["LOINC / standard tags · human sign-off"]
    BN --> LLM --> LOINC
    LOINC -.-> MAP
  end

  subgraph VENDOR["Vendor plane — outside patient data"]
    FLEET["Fleet / CRM / FDE projects<br/>metadata · licences · readiness only"]
  end

  UI -.->|no patient payload| FLEET
```

---

## L1 — Input → AI → Output (Congress mandatory flow)

```mermaid
flowchart LR
  I["INPUT<br/>vitals · labs · demographics<br/>freshness · missingness"]
  AI["AI CORE<br/>frozen LightGBM<br/>+ isotonic calibration<br/>+ TreeSHAP"]
  G["GUARD<br/>TrustGate"]
  O["OUTPUT<br/>probability · band · drivers<br/>owner · SLA · handoff"]

  I --> AI --> G --> O
```

| Step | What happens | Where in repo |
|------|----------------|---------------|
| Input | Hourly observations, provenance, units | `backend/app/integrations/`, charting |
| Features | Past-only windows; no future leak | `ml/`, `backend/app/services/engine.py` |
| Model | Frozen Run 4 LightGBM | `ml/artifacts/`, model card |
| Guard | Stale / mismatch / gaps → Verify or Abstain | `backend/app/trustgate.py` |
| Output | Score, drivers, alert ownership, audit | ICU board, patient, alerts |

---

## L2 — Safety stack (Responsible AI)

```mermaid
flowchart TB
  A["Frozen model SHA — no silent retrain"] --> B["Past-only features"]
  B --> C["TrustGate data-quality gate"]
  C --> D["Silent evaluation before live alerts"]
  D --> E["Readiness gates + site mode"]
  E --> F["Clinician acknowledgement required"]
  F --> G["Hash-chained audit · DPIA · model card"]
```

**We do not claim:** saves lives · approved · live hospital connection · auto-retrains · false-alarm % reduction as proven.

---

## L3 — Role-separated planes

```mermaid
flowchart TB
  SIGNIN["One sign-in → role workspace"]
  SIGNIN --> DOC["Doctor / ICU board"]
  SIGNIN --> NURSE["Nurse / chart · NEWS2"]
  SIGNIN --> ADM["Hospital admin / staff · pilot · readiness"]
  SIGNIN --> IT["Clinical IT / deploy · mapping · quarantine"]
  SIGNIN --> VEN["Vendor / fleet — metadata only"]
```

Roles never share the same clinical screens. Crossing into another plane requires that identity.

---

## L4 — Integration path (worldwide, site by site)

```mermaid
flowchart LR
  D["Discover"] --> BS["Bridge Start"]
  BS --> BC["Bridge Connect"]
  BC --> VE["Validated Evaluation"]
  VE --> CL["Clinical Licence"]
  CL --> ME["Managed Edge optional"]
```

```mermaid
flowchart LR
  A["Assess"] --> E["Equipment"]
  E --> I["Integrate"]
  I --> Dep["Deploy"]
  Dep --> S["Silent eval"]
  S --> T["Train"]
  T --> Sup["Support"]
  Sup --> P["Partner"]
```

| Track | What we do |
|-------|------------|
| Small / mid hospitals | Enable infrastructure + coordinate missing devices |
| Large / mature hospitals | Integrate existing EHR / HIS feeds |

---

## L5 — Evidence layers (honest numbers)

```mermaid
flowchart TB
  DATA["PhysioNet 2019<br/>~40k ICU stays · ~1.55M hourly rows"]
  A["Dataset A — train / select"]
  B["Dataset B — scored once"]
  WIN["LightGBM Run 4 · AUROC ~0.81"]
  REJ["Rejected: CatBoost search · GRU-D · TCN · Graph-Hazard · blends"]

  DATA --> A --> WIN
  DATA --> B --> WIN
  A --> REJ
```

Details: [model card](model-card.md) · [data card](data-card.md) · [experiment ledger](experiment-ledger.md)

---

## L6 — Product surface (demo paths)

| Layer | Route / surface | Users |
|-------|-----------------|-------|
| Public site | `/` splash · hero · connect story | Everyone |
| Sign-in | `/signin` quick roles | Demo / staff |
| ICU | `/app/icu` | Clinicians |
| Patient | `/patient/BED-*` | Clinicians |
| Alerts / handoff | `/app/alerts` · `/app/handoff` | Care team |
| Ward / chart | `/app/ward` · `/app/chart` | Nurses |
| Deploy | `/deploy` | Clinical IT |
| Admin | admin / pilot / staff | Hospital admin |
| Vendor | `/platform` · control-plane | Auralis ops |
| Book | `/contact` | Hospitals |

Live demo (synthetic): https://predictrx-sentinel-demo.onrender.com

---

## L7 — Congress submission map

```mermaid
flowchart LR
  P["Problem 0:00–0:30"] --> S["Solution 0:30–1:00"]
  S --> D["Demo 1:00–2:00"]
  D --> AI["AI 2:00–2:20"]
  AI --> B["Business 2:20–3:00"]
```

| Package piece | Where |
|---------------|--------|
| Problem / users | Pitch VO + product brief |
| AI architecture | **This page** + [architecture](architecture.md) |
| Data & sovereignty | [data card](data-card.md) · [DPIA](data-protection-impact-assessment.md) · on-prem boundary |
| Demo | Live Render site (pitch video local only — not in Git) |
| Scalability | [scalability](scalability.md) · FDE packages · worldwide site-by-site |
| Ethical safeguards | [safety-ethics](safety-ethics.md) · TrustGate · frozen model |

Checklist: [submission wrap-up](submission/WRAP_UP_CHECKLIST.md)
