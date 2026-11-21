# Verified experiment matrix

Evidence-backed only. Paths relative to repo root.  
**Active clinical artifact:** Frozen LightGBM Run 4 only. Challengers below were **rejected** for production scoring.

> Research prototype — not approved for clinical use. Dataset B is PhysioNet Challenge 2019 Set B (public), scored once after freeze — not a Bangladesh hospital validation.

## Production model (retained)

| Field | Value | Evidence |
|-------|--------|----------|
| Family | LightGBM + isotonic calibration | `docs/model-card.md`, `docs/experiment-ledger.md` |
| Run / version | `v0.2.0-202609281906` (`RUN4-FROZEN`) | `ml/artifacts/models/run4_frozen/FROZEN.json` |
| Config | `ml/configs/train_lightgbm.yaml` | ledger + MANIFEST |
| Training data | PhysioNet 2019 Dataset A; patient split seed 42 | `docs/data-card.md`, `ml/configs/splits.yaml` |
| Features | 673 past-only temporal / missingness / rate features | ledger, model card |
| Label | Challenge-compatible `SepsisLabel` (positive from 6h before onset) | ledger |
| Internal test (A) | AUROC 0.821; AUPRC 0.109; high-risk utility 0.244 | `run4_frozen/metrics.json` |
| Dataset B (once) | AUROC 0.808; AUPRC 0.079; high-risk utility 0.238 | `eval_holdout.json`, ledger |
| Calibration | Isotonic on A validation; B slope ~0.80 | model card / README evidence |
| Artifact SHA-256 | `a7dcf5f4b2f00927c17d2468cba144b3db4642ccb5a9c946b484958a0413532d` | `FROZEN.json`, `ACTIVE.json`, `MANIFEST.v2.json` |
| Status | **Active** — `ACTIVE.json` → `run4_frozen/model.joblib` | do not overwrite |
| Disposition | Retain primary evidence model | ledger `RUN4-FROZEN` |

## Comparison table (research tracks)

| Family | Run ID | Config | Train data | Feature / notes | Validation / result | Calibration | Artifact hash / path | Status | Disposition |
|--------|--------|--------|------------|-----------------|---------------------|-------------|----------------------|--------|-------------|
| Clinical-rule + logistic baselines | `baselines_setb_*` | `ml/configs/baselines_setb.yaml` | Set B one-shot | Challenge baselines | Utility 0.053 (rule), 0.124 (logistic) vs Run 4 0.238 | n/a | `ml/artifacts/experiments/baselines_setb_*` (local) | Completed | Reference only |
| LightGBM / CatBoost search | `TABULAR-AONLY-01` | `challenger_tabular*.yaml` | Dataset A only (36-trial search) | Tabular GBDT | Lost to Run 4 on locked internal test | Search-time | `ml/artifacts/challengers/TABULAR-AONLY-01/` (local) | Completed | **Rejected** |
| Same-family bootstrap ensemble | `RUN4-BOOTSTRAP-ENSEMBLE` | (recorded in Run 4 metrics) | Dataset A | 5-member bootstrap LightGBM | Val utility 0.392 vs single 0.402 | n/a | Decision in `metrics.json` | Completed | **Rejected** |
| GRU-D | under `GRAPH-HAZARD-01` | `temporal_graph_hazard.yaml` | Dataset A CV | Missingness-aware RNN | Did not beat tree on utility | — | `…/grud_baseline/` (local) | Completed | **Rejected** for prod |
| TCN | under `GRAPH-HAZARD-01` | same | Dataset A | Temporal conv | Selected temporal baseline; still below tree utility | — | `…/tcn_baseline/`, `final/model.pt` (local) | Completed | **Rejected** for prod |
| Graph-Hazard ablations | `GRAPH-HAZARD-01` | same | Dataset A | Organ-graph + multi-horizon | Ablations recorded; no utility win vs tree | — | `sparse_temporal/`, `plus_organ_graph/`, … (local) | Completed | **Rejected** for prod |
| Run 4 + TCN blend | `GRAPH-HAZARD-01` final | same | A then compared | Probability/logit blend research | Test AUPRC ↑ 0.109→0.117; utility not improved | — | `GRAPH-HAZARD-01/final/` (local) | Completed | **Rejected** |
| Residual-Hazard | `RESIDUAL-HAZARD-01` | `residual_hazard.yaml` | A then Set B once | Healthy-reference residuals | Internal gate passed; Set B utility 0.109 vs Run 4 0.238 | own freeze file | `ml/artifacts/challengers/RESIDUAL-HAZARD-01/` (local) | Completed | **Rejected** — challenger `FROZEN.json` ≠ active model |
| TrustGate offline | `TRUSTGATE-ROBUSTNESS-01` | eval scripts | sims / cohorts | Verify/Abstain twin | False-alert benefit **not** statistically established | n/a | ledger + `ml/.../trustgate` | Completed | Informational |
| Time-series Transformer | — | — | — | — | **No training evidence in repo** | — | — | Not run | Do not claim |
| Qwen 3.5 4B | mapping side-branch | Ollama optional | LOINC registry only | Bangla/local → LOINC | Internal 37-case retrieval bench | n/a | `backend/app/integrations/copilot.py` | Optional runtime | **Not** the sepsis model |

## Provenance rules (do not blur)

1. **Active score path** loads only `ACTIVE.json` → Run 4 joblib + TrustGate (`backend/app/services/engine.py`, `backend/app/trustgate.py`).
2. **Residual-Hazard** has its own `final/FROZEN.json` — research freeze only; never promote without new ACTIVE pointer + ledger entry.
3. Most challenger trees are **gitignored**; local presence ≠ public GitHub contents. Cite ledger + this matrix, not “download all artifacts from GitHub.”
4. Dataset B access is append-only in `ml/artifacts/governance/evaluation_access.json`.

## Source index

| Topic | Primary docs / code |
|-------|---------------------|
| Narrative ledger | `docs/experiment-ledger.md` |
| Model card | `docs/model-card.md` |
| Data card | `docs/data-card.md` |
| Layers / diagrams | `docs/LAYERS.md` |
| Serving | `backend/app/services/engine.py` |
| Integrity CI | `.github/workflows/ci.yml` |
| Mapping LLM (isolated) | `backend/app/integrations/copilot.py` |
