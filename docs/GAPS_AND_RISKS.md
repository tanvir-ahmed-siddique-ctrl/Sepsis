# Gaps, risks, and unresolved-history register

Evidence-backed open items only. Update when closed with a ledger or PR reference.  
**Not** a claim of clinical readiness.

> Research prototype — not approved for clinical use. No Bangladesh patient validation. No paid-pilot / regulatory / outcome claims.

## Unresolved history

| ID | Item | Status | Evidence / note |
|----|------|--------|-----------------|
| H1 | Challenger artifact trees mostly gitignored | Open (by design) | Cite [EXPERIMENT_MATRIX](EXPERIMENT_MATRIX.md) + [experiment-ledger](experiment-ledger.md); do not imply GitHub hosts all joblibs |
| H2 | Exact per-trial logs for all 36 LightGBM/CatBoost trials | Partial | Search summarized under `TABULAR-AONLY-01`; full Optuna dumps may be local-only |
| H3 | Loss-function ablation (BCE / focal / patient-normalized) narrative | Partial | Described in research notes; production path is frozen Run 4 + isotonic only |
| H4 | Calibration family bake-off (Platt / beta / temperature vs isotonic) | Partial | Isotonic retained; other calibrators discussed, not all frozen as alternate ACTIVE models |
| H5 | Transfer Shield S7 as auto-stop module | Documentation-heavy | See [innovation-adoption-barriers](innovation-adoption-barriers.md); do not over-claim as a separate runtime gate |
| H6 | Public demo ≠ live hospital EHR | Closed as policy | README + `/docs` disclaimers; synthetic / PhysioNet replay only |

## Engineering gaps

| ID | Gap | Risk if ignored | Mitigation |
|----|-----|-----------------|------------|
| G1 | Render / container cold-start races | Demo briefly ECONNREFUSED | CI installs `/app/ml`; redeploy image after Dockerfile fix |
| G2 | Optional Qwen not always present | Mapping UX falls back | Copilot is side-branch; scoring never depends on LLM |
| G3 | Dataset B one-shot governance | Accidental re-tuning on B | `evaluation_access.json` append-only + ledger discipline |
| G4 | No Transformer sepsis model trained | False judge narrative | Explicit “not run” row in experiment matrix |
| G5 | Hospital-local full install untested as production site | Over-claim “deployed” | Distinguish intended architecture vs tested local/demo stack |

## Commercial / FDE (hypothesis unless evidenced)

| ID | Topic | Label |
|----|-------|-------|
| B1 | Pricing, WTP, TAM/SAM | Hypothesis — `docs/business/pricing-assumptions.md` |
| B2 | Customers / paid pilots / grants | None claimed without written evidence |
| B3 | Clinical outcome improvement | Not claimed |

## Verification checklist (docs hygiene)

- [x] Noisy root MDs + `predictrx-codex-pack` removed from git index; kept local / `LOCAL_ONLY/`
- [x] README + LAYERS + EXPERIMENT_MATRIX + DOCUMENTATION_INDEX linked
- [x] Frozen Run 4 SHA matches `ml/artifacts/models/run4_frozen/FROZEN.json`
- [ ] Docs commit/push — **only after explicit authorization**
- [ ] Optional: dedicated GitHub Pages site (deferred; in-app `/docs` + Markdown hub)
