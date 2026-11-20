"""TrustGate callout card used when live Verify/Abstain bed is sparse."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "frames" / "03_trustgate.png"
W, H = 1920, 1080
img = Image.new("RGB", (W, H), (244, 250, 246))
d = ImageDraw.Draw(img)

def f(size, bold=False):
    p = r"C:\Windows\Fonts\segoeuib.ttf" if bold else r"C:\Windows\Fonts\segoeui.ttf"
    return ImageFont.truetype(p, size)

d.rectangle([0, 0, 18, H], fill=(47, 138, 99))
d.text((72, 40), "DEMO / FLOW · TRUSTGATE", fill=(47, 138, 99), font=f(22, True))
d.text((72, 140), "Before any alert reaches a nurse.", fill=(18, 32, 48), font=f(52, True))

d.rounded_rectangle([72, 280, 1848, 520], radius=24, fill=(255, 255, 255), outline=(201, 230, 214), width=3)
d.text((110, 330), "TRUSTGATE — BEFORE ANY ALERT", fill=(47, 138, 99), font=f(36, True))
d.text((110, 400), "Stale labs, wrong units or gaps  →  Verify or Abstain  →  not a false alarm", fill=(74, 99, 86), font=f(28))

chips = ["STALE DATA", "UNIT MISMATCH", "MISSING VITALS"]
for i, c in enumerate(chips):
    x = 110 + i * 420
    d.rounded_rectangle([x, 580, x + 380, 680], radius=16, fill=(255, 255, 255), outline=(201, 230, 214), width=2)
    d.text((x + 40, 610), c, fill=(18, 32, 48), font=f(26, True))

# strike false alarm
d.rounded_rectangle([72, 760, 700, 900], radius=18, fill=(255, 235, 235), outline=(200, 80, 80), width=2)
d.text((130, 805), "FALSE ALARM", fill=(160, 40, 40), font=f(36, True))
# strike line
d.line([120, 830, 650, 830], fill=(160, 40, 40), width=6)

d.rounded_rectangle([760, 760, 1848, 900], radius=18, fill=(216, 239, 227), outline=(201, 230, 214), width=2)
d.text((820, 805), "Clinician still owns every decision.", fill=(18, 32, 48), font=f(32, True))

img.save(OUT)
print("wrote", OUT)
