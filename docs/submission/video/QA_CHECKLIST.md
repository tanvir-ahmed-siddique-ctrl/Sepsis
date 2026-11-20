# Final QA — Auralis 180s pitch

**File:** `export/Auralis_180s_Congress_Pitch.mp4`  
**Duration:** 177.91s (portal limit 181s) — PASS  
**Format:** 1920×1080 H.264 + AAC, 30fps — PASS  

## Official 5 segments (titles on frames)

| # | Segment | Timing | Asset signal | Status |
|---|---------|--------|--------------|--------|
| 1 | Problem | ~0:00–0:30 | `seg_problem.png` + VO | PASS |
| 2 | Solution | ~0:30–1:00 | clinical / integration / enable flows | PASS |
| 3 | Demo / Flow | ~1:00–2:00 | live screens + on-prem + TrustGate + Bangla | PASS |
| 4 | AI Approach | ~2:00–2:20 | LightGBM + TrustGate flow; LLM side-branch | PASS |
| 5 | Impact / Business | ~2:20–3:00 | packages, FDE road, tracks, KPIs, governance, endcard | PASS |

Business/FDE airtime ≈ Solution 30s + Demo hospital journey ~18s + Business 40s ≈ 88s.

## 7 mandatory requirements

1. **Problem / users** — doctors, nurses, IT, administrators named — PASS  
2. **AI-native** — frozen LightGBM + TrustGate + mapping LLM — PASS  
3. **Input → AI → output** — vitals/labs → model/TrustGate → score/drivers — PASS  
4. **Demo** — ICU board, patient, drivers, alerts, handoff, ward, chart, booking — PASS  
5. **Bangla** — `নাড়ি` → LOINC card on screen — PASS  
6. **KPIs** — feed uptime, alerts/patient-day, review time, local calibration — PASS  
7. **≤ 3 minutes** — 177.91s — PASS  

## Forbidden claims (must be absent)

Checked against `scripts/full_180s_script.md` and on-screen graphics:

- [x] No “saves lives” / mortality reduction  
- [x] No “approved” / DGDA / FDA / CE  
- [x] No “connected to hospitals” / live patient data (synthetic stated)  
- [x] No “auto-retrains”  
- [x] No “free machines” / “replace your EHR”  
- [x] No doctor gifts / sponsored trips  

## Asset inventory

- Voice: `audio/01_problem` … `05_business` (mp3 + wav)  
- Screens: `screens/s00_*` … `s10_*` from live Render demo  
- Graphics: on-prem, TrustGate, Bangla map, AI flow, packages, FDE road, tracks, KPIs, governance, endcard  
- CapCut polish notes: `CAPCUT_EDIT_GUIDE.md`  

## Upload

Submit `export/Auralis_180s_Congress_Pitch.mp4`. Optional CapCut pass for auto-captions only — do not push length over 181s.
