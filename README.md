# Auralis

<p align="center">
  <strong>Hospital-local ICU early-warning intelligence</strong><br/>
  Public brand <b>Auralis</b> · Research track <b>PredictRx Sentinel</b> · FDE-led hospital enablement
</p>

<p align="center">
  <a href="https://predictrx-sentinel-demo.onrender.com"><img alt="Live demo" src="https://img.shields.io/badge/Live_demo-Render-2A9D8F?style=for-the-badge&labelColor=0B1C2C" /></a>
  <a href="https://tanvir-ahmed-siddique-ctrl.github.io/Sepsis/"><img alt="GitHub Pages" src="https://img.shields.io/badge/Docs_site-GitHub_Pages-1B6CA8?style=for-the-badge&labelColor=0B1C2C" /></a>
  <a href="https://hub.docker.com/r/tanvirdoc02/predictrx-sentinel"><img alt="Docker Hub" src="https://img.shields.io/badge/Docker-tanvirdoc02%2Fpredictrx--sentinel-2496ED?style=for-the-badge&labelColor=0B1C2C" /></a>
</p>

<p align="center">
  <img alt="Model" src="https://img.shields.io/badge/Active_model-LightGBM_Run_4-0B1C2C?style=flat-square&labelColor=2A9D8F" />
  <img alt="Version" src="https://img.shields.io/badge/Version-v0.2.0--202609281906-1B6CA8?style=flat-square" />
  <img alt="Holdout" src="https://img.shields.io/badge/Dataset_B_AUROC-0.808-2A9D8F?style=flat-square" />
  <img alt="Utility" src="https://img.shields.io/badge/B_utility-0.238-C45C26?style=flat-square" />
  <img alt="Status" src="https://img.shields.io/badge/Clinical_use-Not_approved-B00020?style=flat-square" />
  <img alt="Demo data" src="https://img.shields.io/badge/Public_demo-Synthetic_%2F_PhysioNet-5C6BC0?style=flat-square" />
</p>

> **Research prototype — not approved for clinical use.**  
> Public demo = synthetic / PhysioNet replay only. Scores support judgment; they do not replace it.  
> Not validated on Bangladeshi patients. No claim of lives saved, paid pilots, or regulatory approval.

---

## Production model — promoted · frozen · hash-locked

<p align="center">
  <img alt="Frozen" src="https://img.shields.io/badge/ACTIVE-Run_4_only-2A9D8F?style=for-the-badge&labelColor=0B1C2C" />
  <img alt="Not Qwen" src="https://img.shields.io/badge/Qwen-Mapping_side--branch_only-5C6BC0?style=for-the-badge&labelColor=0B1C2C" />
  <img alt="No Transformer" src="https://img.shields.io/badge/Transformer-Not_trained-B00020?style=for-the-badge&labelColor=0B1C2C" />
</p>

The live scorer is **only** Frozen LightGBM **Run 4** — not Qwen, not a Transformer, not any challenger.

| Field | Value |
|:------|:------|
| **Version** | `v0.2.0-202609281906` (`RUN4-FROZEN`) |
| **Family** | LightGBM + **isotonic** calibration + TreeSHAP drivers |
| **SHA-256** | `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d` |
| **Pointer** | `ml/artifacts/models/ACTIVE.json` → `run4_frozen/model.joblib` |
| **Train** | PhysioNet Challenge 2019 **Dataset A** · patient-wise split · seed **42** |
| **Features** | **673** past-only temporal / missingness / rate features (no future leak) |
| **Internal test (A)** | AUROC **0.821** · AUPRC **0.109** · high-risk utility **0.244** |
| **Holdout Dataset B** *(once after freeze)* | AUROC **0.808** · AUPRC **0.079** · utility **0.238** |
| **Baselines on B** | Clinical-rule **0.053** · logistic **0.124** → Run 4 wins |
| **Calibration honesty** | B slope ~**0.80** → **local recalibration required** before any live use |

**Rejected for production** (ledgered; never on `ACTIVE.json`): 36-trial LightGBM/CatBoost · GRU-D · TCN · Graph-Hazard · Run4+TCN blend · Residual-Hazard · 5-member bootstrap.  
**Not claimed:** trained time-series Transformer. **Qwen 3.5 4B** = Bangla/local → LOINC only.

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#2A9D8F','primaryTextColor':'#0B1C2C','primaryBorderColor':'#0B1C2C','lineColor':'#1B6CA8','secondaryColor':'#E8F4F1','tertiaryColor':'#F4E6DC'}}}%%
flowchart LR
  A["Dataset A<br/>train / select / calibrate"] --> F["Freeze Run 4<br/>hash-locked"]
  F --> B["Dataset B<br/>one-shot eval"]
  F --> P["Production score path"]
  C["Challengers"] -.->|rejected| X["Not ACTIVE"]
```

Evidence: [EXPERIMENT_MATRIX](docs/EXPERIMENT_MATRIX.md) · [model-card](docs/model-card.md) · [data-card](docs/data-card.md) · [ledger](docs/experiment-ledger.md)

---

## Quick links

| | |
|:--|:--|
| **Live demo** | https://predictrx-sentinel-demo.onrender.com |
| **In-app docs** | `/docs` (live model hash + architecture) |
| **API OpenAPI** | Demo `/api/docs` |
| **GitHub Pages** | https://tanvir-ahmed-siddique-ctrl.github.io/Sepsis/ |
| **Docker Hub** | `tanvirdoc02/predictrx-sentinel` (`latest` · `judge` · git SHA) |
| **Challenge** | HealthSphere AI · PredictRx · International AI Builders Congress 2026 |

---

## Documentation pack (everything we published)

All engineering docs stay as **full files**; this README is the colorful landing page that points into them.

| Badge | Doc | What it is |
|:------|:----|:-----------|
| ![](https://img.shields.io/badge/hub-teal?style=flat-square&color=2A9D8F) | [DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md) | Audience map — judges / ML / IT / FDE |
| ![](https://img.shields.io/badge/layers-navy?style=flat-square&color=0B1C2C) | [LAYERS.md](docs/LAYERS.md) | Mermaid system / role / safety diagrams |
| ![](https://img.shields.io/badge/matrix-blue?style=flat-square&color=1B6CA8) | [EXPERIMENT_MATRIX.md](docs/EXPERIMENT_MATRIX.md) | Verified model comparison + disposition |
| ![](https://img.shields.io/badge/gaps-amber?style=flat-square&color=C45C26) | [GAPS_AND_RISKS.md](docs/GAPS_AND_RISKS.md) | Open history / risks / honesty register |
| ![](https://img.shields.io/badge/pages-indigo?style=flat-square&color=5C6BC0) | [docs/index.html](docs/index.html) + [_sidebar.md](docs/_sidebar.md) | Docsify GitHub Pages hub |
| ![](https://img.shields.io/badge/arch-slate?style=flat-square&color=455A64) | [architecture.md](docs/architecture.md) | Backend / frontend / security planes |
| ![](https://img.shields.io/badge/trust-teal?style=flat-square&color=2A9D8F) | [trustgate-layers.md](docs/trustgate-layers.md) | Alert / Watch / Verify / Abstain |
| ![](https://img.shields.io/badge/judge-gold?style=flat-square&color=B8860B) | [judge-evidence-matrix.md](docs/judge-evidence-matrix.md) | Claim → evidence file map |
| ![](https://img.shields.io/badge/safety-crimson?style=flat-square&color=B00020) | [safety-ethics.md](docs/safety-ethics.md) | Clinical + research boundaries |
| ![](https://img.shields.io/badge/agents-green?style=flat-square&color=2E7D32) | [AGENTS.md](AGENTS.md) | Repo operator / agent conventions |

**Core set (kept as links + sections below):**  
[LAYERS](docs/LAYERS.md) · [EXPERIMENT_MATRIX](docs/EXPERIMENT_MATRIX.md) · [DOCUMENTATION_INDEX](docs/DOCUMENTATION_INDEX.md) · [GAPS_AND_RISKS](docs/GAPS_AND_RISKS.md) · [architecture](docs/architecture.md) · [trustgate](docs/trustgate-layers.md) · [judge-evidence-matrix](docs/judge-evidence-matrix.md) · [safety-ethics](docs/safety-ethics.md) · [AGENTS.md](AGENTS.md)

Also useful: [model-card](docs/model-card.md) · [data-card](docs/data-card.md) · [experiment-ledger](docs/experiment-ledger.md) · [operations](docs/operations.md) · [operator-guide](docs/operator-guide.md) · [business-model](docs/business/business-model.md) · [REAL_WORLD_ACTION_PLAN](REAL_WORLD_ACTION_PLAN.md)

---

## What it is

Auralis is an **on-premises decision-support stack** for adult ICU early warning:

1. **Connect** hospital feeds (FHIR R4, HL7 v2, CSV) with unit/LOINC quarantine  
2. **Score** with the **frozen** LightGBM Run 4 model above  
3. **Guard** with **TrustGate** (Alert / Watch / Verify data / Abstain)  
4. **Work** in role-separated doctor, nurse, admin, and clinical-IT surfaces  
5. **Deploy** site-by-site via forward-deployed engineering  

---

## System architecture

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#2A9D8F','primaryTextColor':'#0B1C2C','primaryBorderColor':'#0B1C2C','lineColor':'#1B6CA8','secondaryColor':'#E8F4F1','tertiaryColor':'#F4E6DC','background':'#F7FAFC'}}}%%
flowchart TB
  subgraph HOSPITAL["Hospital boundary — LAN / on-prem"]
    SRC["Monitors · LIS · HIS · Bedside"]
    CONN["Connectors<br/>FHIR · HL7 · CSV"]
    MAP["Map + quarantine"]
    FEAT["Past-only features"]
    ML["Frozen LightGBM Run 4<br/>+ TreeSHAP"]
    TG["TrustGate"]
    UI["ICU · Patient · Alerts · Handoff"]
    DB[("Local DB + hash-chained audit")]
    SRC --> CONN --> MAP --> FEAT --> ML --> TG --> UI
    FEAT --> DB
    ML --> DB
    TG --> DB
    UI --> DB
  end

  subgraph SIDE["Side branch — never edits sepsis probability"]
    BN["Bangla / local names"]
    QW["Optional Qwen 3.5 4B + hybrid RAG"]
    LO["LOINC candidates · human SHA sign-off"]
    BN --> QW --> LO -.-> MAP
  end

  subgraph VENDOR["Vendor plane — metadata only"]
    FLEET["Fleet · licences · readiness<br/>no patient payload"]
  end
  UI -.-> FLEET
```

---

## Core set · LAYERS

Full diagrams: **[docs/LAYERS.md](docs/LAYERS.md)**

| Layer | Color cue | Responsibility | Evidence |
|:------|:----------|:---------------|:---------|
| **L1 Connect** | ![](https://img.shields.io/badge/-L1-1B6CA8?style=flat-square) | FHIR / HL7 / CSV, quarantine | `backend/app/integrations/` |
| **L2 Map** | ![](https://img.shields.io/badge/-L2-5C6BC0?style=flat-square) | Local/Bangla → LOINC (proposal) | `backend/app/integrations/copilot.py` |
| **L3 Features** | ![](https://img.shields.io/badge/-L3-00897B?style=flat-square) | Past-only 24h window | `ml/`, `engine.py` |
| **L4 Score** | ![](https://img.shields.io/badge/-L4-2A9D8F?style=flat-square) | Frozen Run 4 + TreeSHAP | `ml/artifacts/models/run4_frozen/` |
| **L5 Guard** | ![](https://img.shields.io/badge/-L5-C45C26?style=flat-square) | TrustGate Verify / Abstain | `backend/app/trustgate.py` |
| **L6 Mode** | ![](https://img.shields.io/badge/-L6-B8860B?style=flat-square) | demo · silent · gates | `site.py`, `pilot.py` |
| **L7 Work** | ![](https://img.shields.io/badge/-L7-455A64?style=flat-square) | Role workspaces + audit | `frontend/app/` |

---

## Core set · EXPERIMENT_MATRIX

Full table: **[docs/EXPERIMENT_MATRIX.md](docs/EXPERIMENT_MATRIX.md)**

| Family | Status |
|:-------|:-------|
| Clinical-rule + logistic baselines | ![](https://img.shields.io/badge/reference-1B6CA8?style=flat-square) |
| 36-trial LightGBM / CatBoost | ![](https://img.shields.io/badge/rejected-B00020?style=flat-square) |
| 5-member Run 4 bootstrap | ![](https://img.shields.io/badge/rejected-B00020?style=flat-square) |
| GRU-D · TCN · Graph-Hazard · blend | ![](https://img.shields.io/badge/rejected-B00020?style=flat-square) |
| Residual-Hazard | ![](https://img.shields.io/badge/rejected-B00020?style=flat-square) |
| Time-series Transformer | ![](https://img.shields.io/badge/not_run-455A64?style=flat-square) |
| Qwen 3.5 4B | ![](https://img.shields.io/badge/mapping_only-5C6BC0?style=flat-square) |
| **Frozen LightGBM Run 4** | ![](https://img.shields.io/badge/ACTIVE-2A9D8F?style=flat-square) |

---

## Core set · DOCUMENTATION_INDEX

**[docs/DOCUMENTATION_INDEX.md](docs/DOCUMENTATION_INDEX.md)** — who opens what.

| Audience | Start here |
|:---------|:-----------|
| Judges (3 min) | This README → LAYERS → EXPERIMENT_MATRIX → live demo |
| ML / research | model-card · data-card · ledger · matrix |
| Hospital IT | architecture · integration · operations |
| Clinical safety | trustgate · safety-case · safety-ethics |
| FDE / commercial | `docs/business/*` *(hypothesis-aware)* |
| Pages hub | [github.io/Sepsis](https://tanvir-ahmed-siddique-ctrl.github.io/Sepsis/) |

---

## Core set · GAPS_AND_RISKS

**[docs/GAPS_AND_RISKS.md](docs/GAPS_AND_RISKS.md)**

| Highlight | Label |
|:----------|:------|
| Challenger artifacts mostly gitignored | ![](https://img.shields.io/badge/by_design-1B6CA8?style=flat-square) |
| Transfer Shield S7 | ![](https://img.shields.io/badge/docs_%2F_audit-C45C26?style=flat-square) — not a separate auto-stop service |
| Public demo ≠ live EHR | ![](https://img.shields.io/badge/policy_closed-2A9D8F?style=flat-square) |
| Pricing / paid pilots / grants | ![](https://img.shields.io/badge/hypothesis-5C6BC0?style=flat-square) |
| Scratch logs removed from git | ![](https://img.shields.io/badge/cleaned-2E7D32?style=flat-square) · keep `eval_log_setB.txt` |

---

## Core set · architecture

**[docs/architecture.md](docs/architecture.md)** · [current-state-audit](docs/architecture/current-state-audit.md)

| Plane | Stack | Notes |
|:------|:------|:------|
| Clinical API | FastAPI · SQLAlchemy | `/v1/*`, OpenAPI at API `/docs` |
| UI | Next.js · Tailwind · ECharts | Public + hospital + vendor |
| Auth | Local / OIDC / demo roles | Doctor · nurse · admin · clinical IT |
| Audit | Hash-chained | Hospital-local |
| MCP | 3 read-only servers | Ops · docs · mapping — **no PHI tools** |
| Edge | Optional HL7 MLLP | `edge/` |

---

## Core set · trustgate

**[docs/trustgate-layers.md](docs/trustgate-layers.md)** · code `backend/app/trustgate.py`

| State | Meaning |
|:------|:--------|
| ![](https://img.shields.io/badge/Alert-B00020?style=flat-square) | Interruptive path allowed (data + model agree) |
| ![](https://img.shields.io/badge/Watch-C45C26?style=flat-square) | Elevated — monitor, not necessarily interrupt |
| ![](https://img.shields.io/badge/Verify_data-B8860B?style=flat-square) | Quality / freshness / unit issue |
| ![](https://img.shields.io/badge/Abstain-455A64?style=flat-square) | Do not interrupt — insufficient trustworthy input |

Honest limit: false-alert *benefit* at matched sensitivity is **not** statistically established.  
Transfer Shield / readiness: [innovation-adoption-barriers](docs/innovation-adoption-barriers.md).

---

## Core set · judge-evidence-matrix

**[docs/judge-evidence-matrix.md](docs/judge-evidence-matrix.md)** — claim → proof file. Use before inventing metrics.

---

## Core set · safety-ethics

**[docs/safety-ethics.md](docs/safety-ethics.md)** · [safety-case](docs/safety-case.md)

- Decision support only · clinicians remain accountable  
- No Bangladesh patient validation claimed  
- Patient data is never a product for sale  
- Public demo = PhysioNet / synthetic only  

---

## Core set · AGENTS.md

**[AGENTS.md](AGENTS.md)** — public repo conventions (prompt packs stay local / `LOCAL_ONLY/`).

---

## Local terminology AI (isolated)

| | |
|:--|:--|
| Runtime | Optional Ollama `qwen3.5:4b` |
| Job | Bangla / BD lab aliases → LOINC candidates |
| Isolation | Score path **never** calls the LLM |
| Bench | [copilot-retrieval-bench-v1.json](docs/evaluation/copilot-retrieval-bench-v1.json) |

---

## Synthetic demo vs hospital-local

| | Public demo | Intended hospital install |
|:--|:------------|:--------------------------|
| Data | PhysioNet + synthetic | Hospital-local only |
| Mode | `demo` | Silent → gated live |
| EHR | **Not** live hospital integration | FHIR / HL7 / CSV on LAN |
| Image | `tanvirdoc02/predictrx-sentinel` | Same pattern · site compose / FDE |

---

## FDE service lifecycle

| Stage | Intent | Label |
|:------|:-------|:------|
| Discover | Readiness | Implemented surfaces |
| Bridge Start | CSV / batch | Implemented |
| Bridge Connect | HL7 / FHIR | Implemented + edge |
| Validated Evaluation | Silent / retrospective | Protocol — **no paid pilot claimed** |
| Clinical Workflow Licence | Annual site | ![](https://img.shields.io/badge/hypothesis-5C6BC0?style=flat-square) |
| Managed Edge | Local ops | Playbooks / FDE |
| Expansion | More sites | Roadmap |

[business-model](docs/business/business-model.md) · [fde-delivery-playbook](docs/business/fde-delivery-playbook.md) · [REAL_WORLD_ACTION_PLAN](REAL_WORLD_ACTION_PLAN.md)

---

## Repo layout

```
backend/        FastAPI · TrustGate · connectors · scoring
frontend/       Next.js · Auralis UI · /docs hub
ml/             Pipeline · frozen Run 4 · (local) challengers
docs/           Cards · ledger · layers · Pages hub · FDE
mcp-server/     Read-only MCP (ops · docs · mapping)
control-plane/  Patient-free vendor fleet
infra/          Docker · Congress preflight
edge/           Optional HL7 edge relay
demo/           Replay assets
```

---

## Quick start

```powershell
Set-Location "…\PredictRx Sentinel"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r ml\requirements.txt
pip install -e .\ml
pip install -r backend\requirements.txt

# API
Set-Location backend
alembic upgrade head
uvicorn app.main:app --reload

# UI (other terminal)
Set-Location frontend
npm ci
npm run dev
```

- UI → http://localhost:3000  
- API OpenAPI → http://localhost:8000/docs  
- Tests → `cd backend && pytest -q` · `cd frontend && npm test`  
- Demo image → `docker build --platform linux/amd64 -f infra/Dockerfile.demo -t tanvirdoc02/predictrx-sentinel:latest .`

---

## Limitations & roadmap

- US PhysioNet ≠ Bangladesh ICU reality  
- No clinical outcome improvement claimed  
- TrustGate alert-burden benefit unproven at matched sensitivity  
- Live HIS needs MoU + legal basis + FDE work outside this repo  
- Frozen Run 4 is **immutable** until a new ledgered promotion  

---

## Disclaimer

Trained on publicly available US ICU data. **Not** for clinical use. **Not** a live hospital EHR integration on the public demo. Patient data is never a product for sale.
