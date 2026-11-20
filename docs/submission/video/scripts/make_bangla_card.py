"""Bangla → LOINC mapping callout for the Clinical IT demo beat."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frames" / "03_bangla_map.png"
W, H = 1920, 1080
img = Image.new("RGB", (W, H), (244, 250, 246))
d = ImageDraw.Draw(img)

def f(size, bold=False):
    # Segoe UI supports Bangla well on Windows
    p = r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"
    return ImageFont.truetype(p, size)

d.rectangle([0, 0, 18, H], fill=(47, 138, 99))
d.text((72, 40), "DEMO / FLOW · CLINICAL IT", fill=(47, 138, 99), font=f(22, True))
d.text((72, 130), "Local terms mapped. Risk score untouched.", fill=(18, 32, 48), font=f(48, True))

# three boxes
boxes = [
    (72, 320, "Local field", "নাড়ি", "Bangla bedside term"),
    (680, 320, "Mapping copilot", "Local LLM + retrieval", "Human sign-off required"),
    (1288, 320, "Standard code", "LOINC / HR", "Ready for TrustGate"),
]
for x, y, title, big, sub in boxes:
    d.rounded_rectangle([x, y, x + 560, y + 320], radius=22, fill=(255, 255, 255), outline=(201, 230, 214), width=3)
    d.text((x + 36, y + 40), title.upper(), fill=(47, 138, 99), font=f(22, True))
    d.text((x + 36, y + 110), big, fill=(18, 32, 48), font=f(40, True))
    d.text((x + 36, y + 220), sub, fill=(74, 99, 86), font=f(24))

for x in (640, 1248):
    d.polygon([(x, 460), (x + 28, 470), (x, 480)], fill=(47, 138, 99))

d.rounded_rectangle([72, 720, 1848, 900], radius=20, fill=(216, 239, 227), outline=(201, 230, 214), width=2)
d.text((110, 770), "FHIR R4  ·  HL7 v2  ·  CSV", fill=(18, 32, 48), font=f(32, True))
d.text((110, 830), "Quarantine holds bad feeds. Mapping LLM never changes the sepsis score.", fill=(74, 99, 86), font=f(26))

img.save(OUT)
print("wrote", OUT)
