# Congress wrap-up checklist (hours-to-submit)

Against `COMPETITION ALL INFO MAIN.md` §9.1–9.2, §11, §14–15.

## Preliminary 180s video — mandatory

| Requirement | Status | Where |
|-------------|--------|--------|
| ≤ 180s structured pitch (portal ≤181s) | Local file only (not in Git) | Keep MP4 on disk for portal upload; see local `docs/submission/video/` |
| Problem + users | In VO / frames | Problem segment |
| AI-native (ML + RAG mapping) | In VO / frames | AI segment + Bangla→LOINC |
| Input → AI → output | In demo + AI cards | ICU → TrustGate → score |
| Working demo | Live site + video screens | Render demo URL |
| Bangla / localization | Bangla mapping card + product | `নাড়ি` → LOINC |
| KPIs / impact | Business segment | Feed uptime · alerts/day · review time · calibration |
| No forbidden claims | QA checked | No saves lives / approved / auto-retrain / gifts |

Polish notes: `docs/submission/video/QA_CHECKLIST.md` · CapCut optional: `CAPCUT_EDIT_GUIDE.md`

## Structured package (§9.1)

| Component | Artifact |
|-----------|----------|
| Problem definition | README + product brief + pitch Problem |
| AI architecture | **[docs/LAYERS.md](../LAYERS.md)** + architecture.md + model card |
| Data & sovereignty | data-card · DPIA · on-prem boundary · vendor metadata-only |
| Demo | Live Render + 180s video |
| Scalability roadmap | scalability.md · FDE packages · worldwide site-by-site next |
| Ethical safeguards | safety-ethics · TrustGate · frozen model · honest evidence |

## Rubric hot spots (§11) — what to open if a judge asks

| 20-pt component | Point them at |
|-----------------|---------------|
| Innovation & AI-native | Frozen ML + TrustGate + Bangla RAG mapping (score sealed) |
| Technical excellence | LAYERS.md · experiment ledger · challengers rejected |
| Business / commercial | business-model · packages · FDE · revenue lines in pitch |
| Global scale & impact | Worldwide integration next · KPIs · design-partner path |
| Responsible AI & sovereignty | On-prem · consent · no patient data to vendor · model card limits |

## Portal / links to paste

- Demo: `https://predictrx-sentinel-demo.onrender.com`
- GitHub: this repo → pin **README** + **docs/LAYERS.md**
- Video file: local only — do not commit; upload MP4 from your machine to the portal
- Portal answers draft: `docs/submission/congress-portal-answers.md`

## Pre-submit last 30 minutes

1. [ ] Open demo; warm Render; ICU board loads with beds  
2. [ ] Play video end-to-end; duration ≤ 181s  
3. [ ] GitHub README shows mermaid diagrams (refresh if needed)  
4. [ ] No “approved / saves lives / connected hospitals / auto-retrains” in portal text  
5. [ ] Confirm Bangla / TrustGate / KPI appear in video or live walkthrough  

## Do not upload

- Raw PhysioNet files · `.env` / secrets · real patient data · doctor-gift language
