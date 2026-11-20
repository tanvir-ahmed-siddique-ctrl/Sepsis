# CapCut polish guide (optional pass over the assembled MP4)

Submission-ready file already exists:

`docs/submission/video/export/Auralis_180s_Congress_Pitch.mp4` (~178s, 1080p30)

Use CapCut only if you want harder keyword pops, auto captions, or OBS screen-recording replacements.

## Import

1. New project → 16:9 → 1080p → 30fps  
2. Import:
   - `export/Auralis_180s_Congress_Pitch.mp4` (base cut), **or** rebuild from:
   - `audio/*.wav` (5 VO clips)
   - `screens/*.png` + `frames/*.png`
3. Tracks: V1 screens/frames · V2 zoom frames · V3 keyword pops · A1 VO · A2 music (−18 dB)

## Segment labels (keep on screen)

| Time | Label |
|------|--------|
| 0:00–0:30 | PROBLEM |
| 0:30–1:00 | SOLUTION |
| 1:00–2:00 | DEMO / FLOW · Synthetic data · Not a live hospital connection |
| 2:00–2:20 | AI APPROACH |
| 2:20–3:00 | IMPACT, BUSINESS & NEXT STEP |

## Demo keyword pops (green `#2F8A63` on white)

- SYNTHETIC DEMO DATA  
- DOCTOR · NURSE · ADMIN · CLINICAL IT · VENDOR  
- ROLE-SEPARATED ACCESS  
- ON-PREM · PATIENT DATA STAYS LOCAL · WORKS OFFLINE  
- 6-HOUR SEPSIS RISK · FRESHNESS PER BED  
- PROBABILITY · TREND · EXPLAINABLE DRIVERS (SHAP)  
- TRUSTGATE — BEFORE ANY ALERT  
- ALERT OWNER · SLA TIMER · SHIFT HANDOFF  
- WARD NEWS2  
- ADMIT + CHART IN SECONDS  
- FHIR R4 · HL7 v2 · CSV · BANGLA → LOINC · QUARANTINE  
- BOOK A SITE ASSESSMENT  

## Transitions / captions

- Blur or Dissolve only, 0.3s  
- Auto captions English; keep `নাড়ি` as hard on-screen text  
- Export 1080p 30fps MP4 ≤ 181s  

## Rebuild from assets

```bash
python docs/submission/video/scripts/generate_voiceover.py
python docs/submission/video/scripts/generate_graphics.py
python docs/submission/video/scripts/assemble_video.py
```
