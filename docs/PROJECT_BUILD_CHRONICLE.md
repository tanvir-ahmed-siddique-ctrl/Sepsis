# Auralis / PredictRx Sentinel — full build chronicle

**Purpose.** One place that tells the whole story: research before code, model experiments (wins and rejects), architecture growth, product/UI, deployment business, Congress wrap-up, and a cleaned archive of the founder prompts that drove the work.

**Truth rules.** Research prototype. Not approved for clinical use. Public demo = synthetic / PhysioNet replay. No fake hospital customers, no outcome claims, no “saves lives,” no auto-retrain. Dataset B was never used for model/feature/threshold selection.

**Visual layers companion:** [LAYERS.md](LAYERS.md)

---

## 0. Pre-build research (before / beside first training)

### Problem framed
- Sepsis can worsen quickly in adult ICU; early warning is useful only if the **score is trustworthy** and the **hospital can actually run the system**.
- Global literature and competition briefs pushed “AI-native” products; HealthSphere / PredictRx track asked for ICU early warning with responsible AI and data sovereignty.
- Founder constraint: Bangladesh / LMIC hospitals often lack clean FHIR, need HL7/CSV/Bangla terms, on-prem data, and human-in-the-loop alerts — a **model API alone is not a product**.

### Research inputs that shaped design
| Theme | What we took | What we refused |
|-------|----------------|-----------------|
| PhysioNet 2019 Challenge | Public ICU sepsis labels, reproducible holdout story | Claiming BD clinical validity |
| External sepsis CDS failures (e.g. published Epic sepsis model critiques) | Alert burden + transfer risk matter | Claiming we “beat Epic” |
| WHO / CDS guidance | Human oversight, transparency | Regulatory approval language |
| LMIC HIS reality | FHIR + HL7 + CSV + Bangla mapping | “We replace your EHR” |
| Care-process leakage on PhysioNet | TrustGate + local recalibration mandatory | Blind go-live |

### Early product thesis (locked)
1. Freeze a strong, explainable tabular model.  
2. Surround it with **TrustGate**, connectors, silent evaluation, and audit.  
3. Sell **deployment** (FDE), not magic accuracy.  
4. Mapping LLM / RAG is a **side branch** — never edits the risk score.

---

## 1. Model journey (small → large → frozen)

### 1.1 Data
- **Source:** PhysioNet Challenge 2019 (CC BY 4.0).  
- **Scale:** ~40,000 ICU stays; Dataset A ~790k hourly rows; Dataset B ~761k hourly rows (~1.55M hours total).  
- **Rebuild (DATA-REBUILD-01, 2026-09-30):** truncated Parquet fixed with streaming writer; Run 4 parity restored.  
- **Integrity audit:** no A/B patient ID overlap; chronological hours; incident targets 1/3/6/12 h prepared (research).

### 1.2 Primary model — RUN4-FROZEN
| Field | Value |
|-------|--------|
| Version | `v0.2.0-202609281906` |
| Type | LightGBM (7 leaves) + isotonic calibration |
| Features | 673 past-only (values, missingness, measurement frequency, trends, SOFA-lite / SIRS) |
| Target | Challenge-compatible early-warning label (positive from 6 h before onset onward) |
| Dataset B (once) | AUROC **0.808** (CI 0.797–0.820); AUPRC 0.079; high-risk utility 0.238 |
| Explainability | Grouped TreeSHAP |
| Latency | ~5 ms / prediction CPU |

### 1.3 Baselines (Dataset B, preregistered once)
| Model | AUROC | High-risk utility |
|-------|-------|-------------------|
| Clinical rule | 0.657 | 0.053 |
| Logistic regression | 0.714 | 0.124 |
| **LightGBM Run 4** | **0.808** | **0.238** |

Release rule passed. Calibration slope on B ≈ **0.80** → **local recalibration required** before any clinical use.

### 1.4 Challengers tried and rejected
| Experiment | What | Decision |
|------------|------|----------|
| RUN4-BOOTSTRAP-ENSEMBLE | 5-member same-family LightGBM average | Rejected (worse utility) |
| TABULAR-AONLY-01 | 36-trial LightGBM/CatBoost + ablations | Winner lost to Run 4 on locked A test → reject |
| GRAPH-HAZARD-01 | GRU-D, TCN, Graph-Hazard ladder + Run4+TCN blend | No utility beat → reject |
| RESIDUAL-HAZARD-01 | Healthy-reference residuals | Lost Dataset B utility vs Run 4 → reject |
| LOWRES-FALLBACK-01 | No-lab LightGBM | Candidate only; not deployed as primary |
| Feature ablations | Care-process alone ≈ 89% of CV utility | Honest finding → motivates TrustGate + local validation |

**Ensemble / disagreement today:** a rejected bootstrap ensemble’s spread is shown as **display-only model disagreement** — not a CI and not used by TrustGate.

### 1.5 TrustGate evidence
- Robustness sims (delays, missing labs, dropout) → Verify / Abstain retained.  
- Cohort test: false-alert benefit **not statistically established** at matched sensitivity — presented as **data-quality safety**, not proven fatigue cure.

### 1.6 Recalibration policy (future, not automatic)
Documented control path: consented local data → clinical review → site calibration / controlled update → rollout/rollback. **No auto-retrain in production.**

Full ledger: [experiment-ledger.md](experiment-ledger.md) · [model-card.md](model-card.md) · [data-card.md](data-card.md)

---

## 2. Architecture build (layers added over time)

```text
Feeds → Connectors → Mapping/Quarantine → Features → Frozen ML → TrustGate → Site mode → Clinical UI
                                         ↘ Local LLM+RAG → LOINC (never touches score)
Vendor/fleet ─────────────────────────────────────────── metadata only (outside patient plane)
```

| Era | What was built |
|-----|----------------|
| Core API | FastAPI observation engine, predictions, alerts, audit hash chain |
| TrustGate | Alert / Watch / Verify / Abstain on freshness, units, gaps, stability |
| Connectors | FHIR R4, HL7 v2, CSV, vendor adapter, spool, circuit breaker, quarantine |
| Edge | Optional on-site MLLP relay / IEEE 11073 normalization |
| Pilot / readiness | Silent metrics, gates, passport, habit fingerprint |
| Identity | Local accounts, roles, TOTP/PIN, workspace separation |
| Control plane | Vendor fleet CRM — patient-free |
| Mapping copilot | Bangla + local terms → LOINC via dictionary + retrieval / optional local LLM |
| Knowledge / Aurie | Guideline retrieval — context only; **never changes probability** |
| Ward | Deterministic NEWS2 (not the ICU sepsis model) |
| Ops | Docker Compose, site override, backup/restore, Prometheus metrics, CI frozen-hash checks |

Detail: [architecture.md](architecture.md) · [LAYERS.md](LAYERS.md)

---

## 3. Product & brand (frontend)

| Wave | Delivered |
|------|-----------|
| ICU cockpit | Board, patient risk + drivers, alerts SLA, handoff, ownership |
| Nurse / ward | Charting, NEWS2 |
| Admin / IT | Staff, pilot, integration, deploy console |
| Public site | Auralis marketing: hero, connect orbit, FDE, booking `/contact` |
| Localization | EN + Bangla clinical copy paths |
| Judge tour | `/judge` rubric walkthrough |
| Brand polish | Splash every homepage visit, living green mist, integration orbit, honest mottos (“Connect the feeds. Earn the right to alert.”) |
| Demo ops | Docker Hub `tanvirdoc02/predictrx-sentinel`, Render demo, seeded ICU replay |

Honesty: demo banners / synthetic labels where required; no fabricated BD validation.

---

## 4. Business & deployment innovation

| Piece | Content |
|-------|---------|
| Packages | Discover → Bridge Start → Bridge Connect → Validated Evaluation → Clinical Licence (+ Managed Edge) |
| FDE lifecycle | Assess · Equipment · Integrate · Deploy · Silent eval · Train · Support · Partner |
| Tracks | Small/mid = enable infrastructure; large = integrate existing EHR |
| Revenue | Readiness assessment · implementation · annual site licence · managed support |
| Governance | Privacy · residency · ethics · regulatory **mapped per country** |
| Next horizon | Worldwide site-by-site integration; each site makes the path easier; consented evidence enables recalibration and governed research partners — **without selling patient data** |

See `docs/business/*`.

---

## 5. Congress readiness map

| Rubric need | Artifact |
|-------------|---------|
| Problem / users | Product brief + pitch |
| AI-native | Frozen ML + TrustGate + Bangla RAG mapping |
| Input → AI → output | LAYERS.md + live ICU demo |
| Bangla | Mapping copilot + BN copy |
| KPIs | Feed uptime, alerts/patient-day, review time, local calibration |
| Sovereignty | On-prem, vendor metadata-only, DPIA |
| Demo | https://predictrx-sentinel-demo.onrender.com |
| Pitch video | Kept **local** under `docs/submission/video/` (not in Git) |

Checklist: [submission/WRAP_UP_CHECKLIST.md](submission/WRAP_UP_CHECKLIST.md)

---

## 6. Founder prompt archive (cleaned)

Original prompts were often short, Banglish, or messy. Below: **intent preserved**, wording cleaned for a permanent record. Chronological by work era (reconstructed from session history + repo decisions).

### Era A — Foundation & honesty
1. **Lock a research prototype, not a fake product.** Build ICU sepsis early warning with clear “not for clinical use” everywhere.  
2. **Freeze the best honest model.** Prefer a reproducible LightGBM with holdout metrics over flashy deep models that lose utility.  
3. **Never use Dataset B for shopping.** Train/select on A; score B once under preregistered rules.  
4. **Keep a ledger of failures.** Ensembles, CatBoost searches, temporal/graph models — if they lose, document and reject.  
5. **Explain every score.** TreeSHAP / drivers for clinicians; no black-box demo.

### Era B — Trust & integration
6. **Build TrustGate.** Stale labs, wrong units, gaps → Verify or Abstain — not a confident false alarm.  
7. **Connect real hospital pipes.** FHIR, HL7, CSV, quarantine, feed health — not hardcoded patients only.  
8. **Bangla and local lab names.** Mapping copilot with retrieval/RAG to LOINC; LLM must not touch the sepsis score.  
9. **Silent evaluation before live alerts.** Readiness gates, pilot metrics, habit/fingerprint monitoring.  
10. **On-prem / data sovereignty.** Patient data stays in the hospital; vendor sees metadata only.

### Era C — Clinical product surface
11. **Role-separated workspaces.** Doctor, nurse, admin, clinical IT, vendor — never the same screens.  
12. **Full ICU workflow.** Board → patient trend/drivers → alerts with owner/SLA → shift handoff → ward NEWS2 → bedside chart.  
13. **Fix blank boards and empty charts.** Polling/cache/unit defaults must be reliable for judges.  
14. **Remove fake “not a real patient” clutter where it hurts the product feel** — but never invent live hospital claims.  
15. **Make it beautiful and clinical.** Premium Auralis UI, not student-demo sloppy; living green, calm motion.

### Era D — Brand, narrative, deploy
16. **Brand as Auralis.** Splash every homepage visit; bigger mark; no content flash before splash finishes.  
17. **Tell the real gap:** strong holdout model exists; **hospital deployment** is the hard part — say that everywhere.  
18. **Hero / motto:** punchy, ask if needed, ship one line that can win a glance.  
19. **Push Docker / GitHub when I say “opush” / push.** Keep Render/demo warm for judges.  
20. **Judge tour + competition alignment.** Map UI and docs to Congress rubric; give a genuine score, not flattery.

### Era E — Business & pitch
21. **Business is FDE/deployment, not “just a model.”** Packages, readiness fees, licence, managed support.  
22. **No doctor gifts / free machines / replace EHR / saves lives / approved / auto-retrains.**  
23. **Small hospitals → consented local evidence → recalibrate under review → governed research with larger partners** — without selling patient data.  
24. **Next is worldwide:** integrate hospital by hospital; make each integration path easier.  
25. **180s video structure:** keep five official segments; expand business time; shorten AI; English VO; Bangla on screen; synthetic only.  
26. **AI VO: dense keywords, ~22–25s.** Freeze, PhysioNet A/B, AUROC 0.81, challengers rejected, TrustGate, Bangla LLM+RAG, score path sealed — rest on screen cards.  
27. **Wrap-up for submit:** layers visual on GitHub; full chronicle; do **not** put the pitch video in the git repo.

### Era F — Meta / process
28. **Implement the attached plan fully; don’t edit the plan file; finish all todos.**  
29. **When I paste Banglish, extract intent and execute** — don’t stall on grammar.  
30. **If something is missing in the record, write the truthful reconstruction** from artifacts and ledger — label provenance when reconstructed.

---

## 7. What “done” means for this chronicle

- [x] Research thesis and refuse-list written  
- [x] Model win + reject table  
- [x] Architecture growth eras  
- [x] Product / brand / business eras  
- [x] Cleaned prompt archive  
- [x] Links to deep evidence docs  
- [x] Video excluded from GitHub on founder request  

**Living document.** Append new experiments and prompts at the bottom; do not erase rejected runs.

---

## 8. Quick index

| Need | Go to |
|------|--------|
| Pictures of layers | [LAYERS.md](LAYERS.md) |
| Locked product cuts | [DECISIONS.md](DECISIONS.md) |
| Every ML run | [experiment-ledger.md](experiment-ledger.md) |
| Metrics claim sheet | [model-card.md](model-card.md) |
| Data provenance | [data-card.md](data-card.md) |
| Safety case | [safety-case.md](safety-case.md) · [safety-ethics.md](safety-ethics.md) |
| Business | [business/business-model.md](business/business-model.md) |
| Submit checklist | [submission/WRAP_UP_CHECKLIST.md](submission/WRAP_UP_CHECKLIST.md) |
