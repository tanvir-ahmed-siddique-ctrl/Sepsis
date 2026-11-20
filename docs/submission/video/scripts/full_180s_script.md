# AURALIS — 180-SECOND PRELIMINARY PITCH (FINAL)

Segment titles stay on screen. English VO. Bangla terms appear as hard on-screen text.

---

## 0:00–0:30 | PROBLEM (~75 words)

Sepsis can worsen quickly. Yet ICU decisions depend on observations, handovers, devices and records that may not speak to one another.

Doctors and nurses need timely signals. Hospital IT teams need safe integration. Administrators need evidence and accountable operations.

In Bangladesh, and across diverse health systems, an AI model alone cannot solve that last-mile gap.

The problem is not only prediction. It is deployment.

---

## 0:30–1:00 | SOLUTION (~80 words) — use your existing 32s animation, trimmed to 30s

Auralis predicts six-hour sepsis risk — with probability, trends and explainable drivers.

TrustGate validates the data. Clinical mapping standardizes local terms and codes.

We connect FHIR, HL7, CSV and vendor feeds, with quarantine safeguards.

Our Forward Deployed Engineers assess infrastructure, connect devices, deploy on-site, and support silent evaluation, governance and ongoing operations.

Beyond prediction, we deliver real-world integration.

---

## 1:00–2:00 | DEMO / FLOW (~155 words)

This is Auralis running on synthetic ICU data — no real patients.

One sign-in, separate workspaces: doctor, nurse, hospital admin, clinical IT and our vendor team never share the same screens.

Everything runs on the hospital's own server. Patient data stays inside the hospital.

The ICU board ranks every bed by six-hour sepsis risk, with data freshness beside it.

Open a patient: probability, trend, and the drivers behind the score — vitals and labs the model actually used.

Before any alert reaches a nurse, TrustGate checks the data. Stale labs, wrong units or gaps mean Verify or Abstain — not a false alarm.

Alerts carry an owner and a timer. Handoff carries them into the next shift. Wards get NEWS2. New admissions and bedside charting take seconds.

Behind this: the admin console sets staff and units, silent evaluation and readiness gates.

Clinical IT maps FHIR, HL7 and Bangla lab terms, with quarantine.

And hospitals book us directly — our engineers take it from there.

---

## 2:00–2:20 | AI APPROACH (~50 words)

Under the hood: a frozen LightGBM model on past-only features, with TreeSHAP explanations. It was trained on PhysioNet 2019 and evaluated once on a separate hospital set: AUROC 0.81.

A local LLM maps Bangla and local lab terms to LOINC — it never touches the risk score.

---

## 2:20–3:00 | IMPACT, BUSINESS & NEXT STEP (~105 words)

Our business is deployment, not just a model.

For small and mid-size hospitals, Forward Deployed Engineers assess what exists — monitors, records, network — and coordinate what's missing.

We install locally, train doctors, nurses and IT, run silent evaluation, and support operations long term.

Revenue: paid readiness assessment, implementation, an annual site licence, and managed support.

Each country's privacy, data-residency and clinical approvals are mapped before go-live — never assumed.

Over time, consented local data lets each site recalibrate under clinical review.

We'll track feed uptime, alert burden, review time and local performance.

Next: one Bangladesh design-partner ICU.

---

## Forbidden claims (never say)

- Saves lives / reduces mortality
- Connected to hospitals / live patient data
- Approved / DGDA / FDA / CE
- Auto-retrains
- Free machines / replace your EHR
- Doctor gifts / sponsored trips
