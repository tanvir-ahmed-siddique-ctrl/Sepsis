"""Generate timed English voiceover WAVs for the 180s pitch via edge-tts."""
from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

OUT = Path(__file__).resolve().parent.parent / "audio"
VOICE = "en-US-AndrewNeural"  # calm, confident male
RATE = "-5%"  # slightly deliberate for clarity

SEGMENTS: list[tuple[str, str]] = [
    (
        "01_problem",
        "Sepsis can worsen quickly. Yet ICU decisions depend on observations, handovers, devices and records that may not speak to one another. "
        "Doctors and nurses need timely signals. Hospital IT teams need safe integration. Administrators need evidence and accountable operations. "
        "In Bangladesh, and across diverse health systems, an AI model alone cannot solve that last-mile gap. "
        "The problem is not only prediction. It is deployment.",
    ),
    (
        "02_solution",
        "Auralis predicts six-hour sepsis risk — with probability, trends and explainable drivers. "
        "TrustGate validates the data. Clinical mapping standardizes local terms and codes. "
        "We connect FHIR, HL7, CSV and vendor feeds, with quarantine safeguards. "
        "Our Forward Deployed Engineers assess infrastructure, connect devices, deploy on-site, and support silent evaluation, governance and ongoing operations. "
        "Beyond prediction, we deliver real-world integration.",
    ),
    (
        "03_demo",
        "This is Auralis running on synthetic ICU data — no real patients. "
        "One sign-in, separate workspaces: doctor, nurse, hospital admin, clinical IT and our vendor team never share the same screens. "
        "Everything runs on the hospital's own server. Patient data stays inside the hospital. "
        "The ICU board ranks every bed by six-hour sepsis risk, with data freshness beside it. "
        "Open a patient: probability, trend, and the drivers behind the score — vitals and labs the model actually used. "
        "Before any alert reaches a nurse, TrustGate checks the data. Stale labs, wrong units or gaps mean Verify or Abstain — not a false alarm. "
        "Alerts carry an owner and a timer. Handoff carries them into the next shift. Wards get NEWS2. New admissions and bedside charting take seconds. "
        "Behind this: the admin console sets staff and units, silent evaluation and readiness gates. "
        "Clinical IT maps FHIR, HL7 and Bangla lab terms, with quarantine. "
        "And hospitals book us directly — our engineers take it from there.",
    ),
    (
        "04_ai",
        "Under the hood: a frozen LightGBM model on past-only features, with TreeSHAP explanations. "
        "It was trained on PhysioNet 2019 and evaluated once on a separate hospital set: AUROC 0.81. "
        "A local LLM maps Bangla and local lab terms to LOINC — it never touches the risk score.",
    ),
    (
        "05_business",
        "Our business is deployment, not just a model. "
        "For small and mid-size hospitals, Forward Deployed Engineers assess what exists — monitors, records, network — and coordinate what's missing. "
        "We install locally, train doctors, nurses and IT, run silent evaluation, and support operations long term. "
        "Revenue: paid readiness assessment, implementation, an annual site licence, and managed support. "
        "Each country's privacy, data-residency and clinical approvals are mapped before go-live — never assumed. "
        "Over time, consented local data lets each site recalibrate under clinical review. "
        "We'll track feed uptime, alert burden, review time and local performance. "
        "Next: one Bangladesh design-partner ICU.",
    ),
]


async def synth(name: str, text: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{name}.mp3"
    communicate = edge_tts.Communicate(text, VOICE, rate=RATE)
    await communicate.save(str(path))
    print(f"wrote {path.name}")
    return path


async def main() -> None:
    for name, text in SEGMENTS:
        await synth(name, text)


if __name__ == "__main__":
    asyncio.run(main())
