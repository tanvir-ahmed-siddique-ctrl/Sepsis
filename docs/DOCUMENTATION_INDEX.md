# Documentation index

Single map for judges, researchers, hospital IT, and partners.  
Everything below is either **measured**, **implemented**, or clearly labeled **hypothesis**.

> Research prototype — **not approved for clinical use**. Public demo = synthetic / PhysioNet replay only.

## Start here

| Audience | Open first |
|----------|------------|
| Judges (3-minute orientation) | [README](../README.md) → [LAYERS](LAYERS.md) → [EXPERIMENT_MATRIX](EXPERIMENT_MATRIX.md) → live demo |
| ML / research review | [model-card](model-card.md) · [data-card](data-card.md) · [experiment-ledger](experiment-ledger.md) · [matrix](EXPERIMENT_MATRIX.md) |
| Hospital IT / security | [architecture](architecture.md) · [integration](integration.md) · [operations](operations.md) · [operator-guide](operator-guide.md) |
| Clinical safety | [trustgate-layers](trustgate-layers.md) · [safety-case](safety-case.md) · [safety-ethics](safety-ethics.md) |
| FDE / commercial (hypothesis-aware) | [business-model](business/business-model.md) · [fde-delivery-playbook](business/fde-delivery-playbook.md) · [deployment-innovation-plan](business/deployment-innovation-plan.md) |

In-product docs (live readiness hash): `/docs` on the running app or [demo](https://predictrx-sentinel-demo.onrender.com/docs).  
Navigable GitHub Pages hub (Docsify): [tanvir-ahmed-siddique-ctrl.github.io/Sepsis](https://tanvir-ahmed-siddique-ctrl.github.io/Sepsis/).  
API reference (Swagger): demo [`/api/docs`](https://predictrx-sentinel-demo.onrender.com/api/docs) → FastAPI `/docs`.

## Engineering layers (source-linked)

| Layer | Job | Code / docs |
|-------|-----|-------------|
| L1 Connect | FHIR / HL7 / CSV / quarantine | `backend/app/integrations/` · [integration](integration.md) |
| L2 Map | Bangla/local → LOINC (side branch) | `backend/app/integrations/copilot.py` · MCP `mcp-server/predictrx_mapping_mcp.py` |
| L3 Features | Past-only 24h window | `ml/` · `backend/app/services/engine.py` |
| L4 Score | Frozen LightGBM Run 4 + TreeSHAP | `ml/artifacts/models/run4_frozen/` · [model-card](model-card.md) |
| L5 Guard | TrustGate Verify / Abstain | `backend/app/trustgate.py` · [trustgate-layers](trustgate-layers.md) |
| L6 Mode | demo / silent / live gates | `backend/app/site.py`, `pilot.py` · [operations](operations.md) |
| L7 Work | ICU · patient · alerts · handoff | `frontend/app/` · [frontend-how-to-use](frontend-how-to-use.md) |
| Vendor | Patient-free fleet / CRM | `control-plane/` · [fleet](fleet-enrolment-and-release-rings.md) |

Full Mermaid diagrams: [LAYERS.md](LAYERS.md).

## Evidence & honesty boundaries

| Claim type | Where |
|------------|--------|
| Measured Set B metrics | [EXPERIMENT_MATRIX](EXPERIMENT_MATRIX.md), [judge-evidence-matrix](judge-evidence-matrix.md) |
| Rejected challengers | Same matrix + [experiment-ledger](experiment-ledger.md) |
| Transfer Shield / readiness | [innovation-adoption-barriers](innovation-adoption-barriers.md) — note S7 is primarily audit documentation, not a separate auto-stop module |
| Pricing / market / grants | Hypothesis unless cited; see `docs/business/pricing-assumptions.md` |
| Gaps / unresolved history | [GAPS_AND_RISKS](GAPS_AND_RISKS.md) |
| Outside-repo work | [REAL_WORLD_ACTION_PLAN.md](../REAL_WORLD_ACTION_PLAN.md) |

## MCP (operator / docs / mapping)

| Server | Purpose | Path |
|--------|---------|------|
| `predictrx-sentinel` | Readiness / model card / ops metadata | `mcp-server/predictrx_mcp.py` |
| `predictrx-docs` | Docs resources only | `mcp-server/predictrx_docs_mcp.py` |
| `predictrx-mapping` | Mapping registry / unmapped codes | `mcp-server/predictrx_mapping_mcp.py` |

No patient-chart tools. Example: `mcp-server/mcp.example.json`.
