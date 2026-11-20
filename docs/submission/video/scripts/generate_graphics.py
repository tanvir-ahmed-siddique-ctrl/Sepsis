"""Generate CapCut-ready / ffmpeg title cards and motion stills (1920x1080)."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frames"
W, H = 1920, 1080
BG = (244, 250, 246)
INK = (18, 32, 48)
GREEN = (47, 138, 99)
GREEN_SOFT = (216, 239, 227)
MUTED = (74, 99, 86)
WHITE = (255, 255, 255)
CARD = (255, 255, 255)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf",
        r"C:\Windows\Fonts\arialbd.ttf" if bold else r"C:\Windows\Fonts\arial.ttf",
    ]
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default()


def base(label: str | None = None) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # soft mist blobs
    d.ellipse([-200, -120, 700, 500], fill=(232, 245, 238))
    d.ellipse([1200, 600, 2100, 1200], fill=(216, 239, 227))
    d.rectangle([0, 0, 18, H], fill=GREEN)
    if label:
        d.text((72, 40), label.upper(), fill=GREEN, font=font(22, True))
    return img, d


def wrap(d: ImageDraw.ImageDraw, text: str, f, max_w: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if d.textlength(trial, font=f) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def card_title(name: str, eyebrow: str, title: str, lines: list[str]) -> None:
    img, d = base(eyebrow)
    d.text((72, 160), title, fill=INK, font=font(56, True))
    y = 280
    body = font(32)
    for line in lines:
        for wl in wrap(d, line, body, W - 160):
            d.text((72, y), wl, fill=MUTED, font=body)
            y += 48
        y += 12
    d.text((72, H - 70), "Auralis · Research prototype · Synthetic demo data", fill=GREEN, font=font(22))
    img.save(OUT / name)
    print("wrote", name)


def flow_row(name: str, eyebrow: str, title: str, steps: list[tuple[str, str]]) -> None:
    img, d = base(eyebrow)
    d.text((72, 120), title, fill=INK, font=font(48, True))
    n = len(steps)
    gap = 24
    box_w = (W - 144 - gap * (n - 1)) // n
    y0 = 280
    for i, (label, detail) in enumerate(steps):
        x = 72 + i * (box_w + gap)
        d.rounded_rectangle([x, y0, x + box_w, y0 + 320], radius=20, fill=WHITE, outline=(201, 230, 214), width=2)
        d.rounded_rectangle([x + 24, y0 + 28, x + 72, y0 + 76], radius=10, fill=GREEN)
        d.text((x + 38, y0 + 36), str(i + 1), fill=WHITE, font=font(24, True))
        d.text((x + 24, y0 + 110), label, fill=INK, font=font(26, True))
        yy = y0 + 160
        for wl in wrap(d, detail, font(20), box_w - 48):
            d.text((x + 24, yy), wl, fill=MUTED, font=font(20))
            yy += 30
        if i < n - 1:
            ax = x + box_w + 4
            d.polygon([(ax, y0 + 150), (ax + 14, y0 + 160), (ax, y0 + 170)], fill=GREEN)
    img.save(OUT / name)
    print("wrote", name)


def kpi_grid(name: str) -> None:
    img, d = base("2:20–3:00 · Impact KPIs")
    d.text((72, 120), "What we measure.", fill=INK, font=font(48, True))
    tiles = [
        ("FEED UPTIME", "Source-to-score latency & continuity"),
        ("ALERTS / PATIENT-DAY", "Alert burden before go-live"),
        ("REVIEW TIME", "Time to clinician acknowledgement"),
        ("LOCAL CALIBRATION", "Site performance under review"),
    ]
    positions = [(72, 260), (980, 260), (72, 620), (980, 620)]
    for (title, body), (x, y) in zip(tiles, positions):
        d.rounded_rectangle([x, y, x + 860, y + 280], radius=24, fill=WHITE, outline=(201, 230, 214), width=2)
        d.text((x + 40, y + 50), title, fill=GREEN, font=font(28, True))
        d.text((x + 40, y + 120), body, fill=MUTED, font=font(28))
    img.save(OUT / name)
    print("wrote", name)


def onprem(name: str) -> None:
    img, d = base("DEMO · Data plane")
    d.text((72, 140), "Patient data stays local.", fill=INK, font=font(52, True))
    # hospital box
    d.rounded_rectangle([520, 320, 1400, 820], radius=28, fill=WHITE, outline=GREEN, width=4)
    d.text((700, 380), "HOSPITAL BOUNDARY", fill=GREEN, font=font(28, True))
    d.rounded_rectangle([700, 460, 1220, 700], radius=20, fill=GREEN_SOFT, outline=(201, 230, 214), width=2)
    d.text((780, 520), "Auralis on-prem server", fill=INK, font=font(32, True))
    d.text((800, 580), "ICU scores · chart · audit", fill=MUTED, font=font(24))
    # lock badge
    d.ellipse([1280, 360, 1380, 460], fill=GREEN)
    d.text((1310, 388), "LOCK", fill=WHITE, font=font(18, True))
    for i, label in enumerate(["ON-PREM", "NO PATIENT DATA LEAVES", "WORKS OFFLINE"]):
        d.rounded_rectangle([72, 340 + i * 90, 460, 410 + i * 90], radius=16, fill=WHITE, outline=(201, 230, 214), width=2)
        d.text((100, 358 + i * 90), label, fill=INK, font=font(24, True))
    img.save(OUT / name)
    print("wrote", name)


def packages(name: str) -> None:
    img, d = base("Business · Packages")
    d.text((72, 110), "Deployment-led commercial path.", fill=INK, font=font(44, True))
    steps = [
        "Discover",
        "Bridge Start",
        "Bridge Connect",
        "Validated Evaluation",
        "Clinical Licence",
    ]
    y = 280
    for i, s in enumerate(steps):
        x = 72 + i * 360
        if i < 4:
            d.line([x + 280, y + 50, x + 340, y + 50], fill=GREEN, width=4)
        d.rounded_rectangle([x, y, x + 280, y + 140], radius=18, fill=WHITE, outline=(201, 230, 214), width=2)
        d.text((x + 24, y + 30), f"{i+1}", fill=GREEN, font=font(22, True))
        # wrap long names
        words = s.split()
        if len(words) > 1:
            d.text((x + 24, y + 60), words[0], fill=INK, font=font(24, True))
            d.text((x + 24, y + 92), " ".join(words[1:]), fill=INK, font=font(24, True))
        else:
            d.text((x + 24, y + 70), s, fill=INK, font=font(26, True))
    d.rounded_rectangle([72, 520, 1848, 720], radius=20, fill=GREEN_SOFT, outline=(201, 230, 214), width=2)
    d.text((110, 560), "Optional Managed Edge", fill=INK, font=font(32, True))
    d.text((110, 620), "Hardware coordination · backup · managed local infrastructure · staff training", fill=MUTED, font=font(26))
    # compress to 5 boxes that fit - redraw simpler
    img2, d2 = base("Business · Packages")
    d2.text((72, 110), "Deployment-led commercial path.", fill=INK, font=font(44, True))
    steps2 = [
        ("1 Discover", "Readiness assessment"),
        ("2 Bridge Start", "Basic / paper-heavy sites"),
        ("3 Bridge Connect", "Approved interfaces"),
        ("4 Validated Eval", "Silent pilot"),
        ("5 Clinical Licence", "After approvals"),
    ]
    for i, (t, b) in enumerate(steps2):
        x = 72 + (i % 5) * 360
        yy = 280
        d2.rounded_rectangle([x, yy, x + 340, yy + 220], radius=18, fill=WHITE, outline=(201, 230, 214), width=2)
        d2.text((x + 24, yy + 40), t, fill=GREEN, font=font(26, True))
        for wl in wrap(d2, b, font(22), 290):
            d2.text((x + 24, yy + 110), wl, fill=MUTED, font=font(22))
    d2.rounded_rectangle([72, 560, 1848, 760], radius=20, fill=GREEN_SOFT, outline=(201, 230, 214), width=2)
    d2.text((110, 610), "+ Managed Edge  ·  hardware coordination, backup, training, long-term support", fill=INK, font=font(28, True))
    d2.text((110, 680), "Revenue: readiness · implementation · annual site licence · managed support", fill=MUTED, font=font(24))
    img2.save(OUT / name)
    print("wrote", name)


def tracks(name: str) -> None:
    img, d = base("Business · Two tracks")
    d.text((72, 120), "Small to large — segmented by readiness.", fill=INK, font=font(44, True))
    d.rounded_rectangle([72, 280, 920, 860], radius=24, fill=WHITE, outline=GREEN, width=3)
    d.rounded_rectangle([1000, 280, 1848, 860], radius=24, fill=WHITE, outline=GREEN, width=3)
    d.text((110, 320), "SMALL / MID HOSPITALS", fill=GREEN, font=font(28, True))
    d.text((1040, 320), "LARGE / MATURE HOSPITALS", fill=GREEN, font=font(28, True))
    left = [
        "Assess what exists",
        "Coordinate missing devices",
        "Local install + training",
        "Silent evaluation first",
        "Long-term managed support",
    ]
    right = [
        "Integrate existing EHR / HIS",
        "Map FHIR · HL7 · CSV",
        "Quarantine bad feeds",
        "Governed go-live",
        "Metadata-only vendor ops",
    ]
    for i, t in enumerate(left):
        d.text((110, 420 + i * 70), f"•  {t}", fill=INK, font=font(26))
    for i, t in enumerate(right):
        d.text((1040, 420 + i * 70), f"•  {t}", fill=INK, font=font(26))
    img.save(OUT / name)
    print("wrote", name)


def governance(name: str) -> None:
    img, d = base("Business · Country governance")
    d.text((72, 120), "Mapped per country. Never assumed.", fill=INK, font=font(48, True))
    chips = ["PRIVACY", "DATA RESIDENCY", "ETHICS", "REGULATORY", "CLINICAL GOVERNANCE"]
    for i, c in enumerate(chips):
        x = 72 + (i % 3) * 600
        y = 300 + (i // 3) * 220
        d.rounded_rectangle([x, y, x + 560, y + 160], radius=20, fill=WHITE, outline=(201, 230, 214), width=2)
        d.text((x + 40, y + 55), c, fill=INK, font=font(32, True))
    d.rounded_rectangle([72, 760, 700, 900], radius=18, fill=GREEN)
    d.text((120, 805), "MAPPED PER COUNTRY", fill=WHITE, font=font(28, True))
    img.save(OUT / name)
    print("wrote", name)


def endcard(name: str) -> None:
    img, d = base(None)
    d.text((72, 320), "AURALIS", fill=INK, font=font(96, True))
    d.text((72, 460), "Beyond prediction.", fill=GREEN, font=font(48, True))
    d.text((72, 540), "Built for real hospital deployment.", fill=MUTED, font=font(40))
    d.text((72, 700), "https://predictrx-sentinel-demo.onrender.com", fill=INK, font=font(28))
    d.text((72, 780), "Next: one Bangladesh design-partner ICU.", fill=MUTED, font=font(26))
    d.text((72, H - 70), "Research prototype · Not approved for clinical use", fill=MUTED, font=font(22))
    img.save(OUT / name)
    print("wrote", name)


def ai_flow(name: str) -> None:
    img, d = base("2:00–2:20 · AI Approach")
    d.text((72, 100), "Frozen model. Separate mapping LLM.", fill=INK, font=font(44, True))
    boxes = [
        (72, 280, "Vitals + Labs", "Past-only features"),
        (620, 280, "LightGBM + TrustGate", "Frozen · explainable"),
        (1200, 280, "Score + Drivers", "Clinician review"),
    ]
    for x, y, t, b in boxes:
        d.rounded_rectangle([x, y, x + 480, y + 220], radius=20, fill=WHITE, outline=(201, 230, 214), width=2)
        d.text((x + 30, y + 50), t, fill=INK, font=font(28, True))
        d.text((x + 30, y + 120), b, fill=MUTED, font=font(24))
    for x in (560, 1120):
        d.polygon([(x, 380), (x + 40, 390), (x, 400)], fill=GREEN)
    # side branch
    d.rounded_rectangle([72, 580, 1848, 900], radius=20, fill=GREEN_SOFT, outline=(201, 230, 214), width=2)
    d.text((110, 630), "Side branch (never changes the risk score)", fill=GREEN, font=font(24, True))
    d.text((110, 700), "Bangla / local lab terms  →  Local LLM + retrieval  →  LOINC mapping  →  Human sign-off", fill=INK, font=font(28))
    d.text((110, 780), "PhysioNet 2019 · Dataset B AUROC ~0.81 · TreeSHAP drivers", fill=MUTED, font=font(24))
    img.save(OUT / name)
    print("wrote", name)


def fde_road(name: str) -> None:
    flow_row(
        name,
        "FDE lifecycle",
        "How Auralis reaches a hospital.",
        [
            ("Assess", "Site & data readiness"),
            ("Equip", "Coordinate devices"),
            ("Integrate", "FHIR / HL7 / CSV"),
            ("Deploy", "On-prem install"),
            ("Silent", "Shadow evaluation"),
            ("Train", "Doctors · nurses · IT"),
            ("Support", "Managed ops"),
            ("Partner", "Long-term site"),
        ],
    )


def segment_labels() -> None:
    for name, title, sub in [
        ("seg_problem.png", "PROBLEM", "0:00 – 0:30"),
        ("seg_solution.png", "SOLUTION", "0:30 – 1:00"),
        ("seg_demo.png", "DEMO / FLOW", "1:00 – 2:00"),
        ("seg_ai.png", "AI APPROACH", "2:00 – 2:20"),
        ("seg_business.png", "IMPACT & BUSINESS", "2:20 – 3:00"),
    ]:
        img, d = base(sub)
        d.text((72, 420), title, fill=INK, font=font(72, True))
        img.save(OUT / name)
        print("wrote", name)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    card_title(
        "01_problem.png",
        "0:00–0:30 · Problem",
        "The problem is not only prediction.\nIt is deployment.",
        [
            "Sepsis worsens quickly while ICU data stays fragmented.",
            "Doctors, nurses, IT and administrators all feel the gap.",
            "An AI model alone cannot close the last mile.",
        ],
    )
    # keep earlier solution frames if present; regenerate branded ones
    flow_row(
        "02_solution_clinical.png",
        "0:30–1:00 · Solution",
        "We build clinical intelligence.",
        [
            ("Vitals", "Quality + Bangla mapping"),
            ("ML", "Frozen LightGBM"),
            ("Risk", "6-hour sepsis score"),
            ("Drivers", "Explainable SHAP"),
            ("Review", "Clinician owns it"),
        ],
    )
    flow_row(
        "02_solution_integration.png",
        "0:30–1:00 · Solution",
        "We engineer hospital integration.",
        [
            ("Sources", "Monitors · HIS · LIS"),
            ("Bridge", "FHIR · HL7 · CSV"),
            ("Trust", "Quarantine + feed health"),
            ("Deploy", "On-site Auralis"),
        ],
    )
    flow_row(
        "02_solution_enable.png",
        "0:30–1:00 · Solution",
        "We enable hospitals beyond deployment.",
        [
            ("Assess", "FDE readiness"),
            ("Equip", "Device coordination"),
            ("Train", "Clinical + IT"),
            ("Support", "Managed ops"),
            ("Partner", "Long-term site"),
        ],
    )
    onprem("03_onprem.png")
    ai_flow("04_ai_flow.png")
    packages("05_packages.png")
    fde_road("05_fde_road.png")
    tracks("05_tracks.png")
    kpi_grid("05_kpis.png")
    governance("05_governance.png")
    endcard("06_endcard.png")
    segment_labels()
    print("graphics done →", OUT)


if __name__ == "__main__":
    main()
