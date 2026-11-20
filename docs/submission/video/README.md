# Auralis 180-second Congress pitch — production package

## Submit this file

**`export/Auralis_180s_Congress_Pitch.mp4`** — ~178 seconds, 1080p30.

## What was built

| Folder | Contents |
|--------|----------|
| `scripts/` | Full VO script, TTS generator, graphics generator, ffmpeg assembler |
| `audio/` | 5 English VO clips (Problem → Business) |
| `frames/` | Segment titles + on-prem, TrustGate, Bangla map, AI, packages, FDE, KPIs, endcard |
| `screens/` | Live Render screenshots (splash, sign-in, ICU, patient, drivers, alerts, handoff, ward, chart, contact) |
| `export/` | Final MP4 + intermediate clips |

Timing follows the approved plan: Problem 30s · Solution 30s · Demo 58s · AI 20s · Business 40s.

## Rebuild

```bash
python docs/submission/video/scripts/generate_graphics.py
python docs/submission/video/scripts/assemble_video.py
```

Optional CapCut polish: see `CAPCUT_EDIT_GUIDE.md`.  
QA record: `QA_CHECKLIST.md`.
