from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Assets" / "AppIcon.iconset"
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 1024
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# Soft navy app tile.
d.rounded_rectangle((52, 52, 972, 972), radius=225, fill="#0A2342")
# Subtle inner lift.
d.rounded_rectangle((88, 88, 936, 936), radius=194, fill="#123458")

# Router body with friendly proportions.
d.rounded_rectangle((260, 474, 764, 750), radius=86, fill="#F8FBFD")
d.rounded_rectangle((302, 526, 722, 684), radius=52, fill="#EAF3FA")
# Device LEDs.
for x, color in [(350, "#1464A5"), (410, "#29976D"), (470, "#53A5DC")]:
    d.ellipse((x-14, 636-14, x+14, 636+14), fill=color)
# Navy lower vent.
d.rounded_rectangle((552, 624, 672, 650), radius=13, fill="#0A2342")

# Signal waves: broad arcs above router.
wave_color = "#53A5DC"
for box, width in [((250, 198, 774, 610), 38), ((332, 274, 692, 566), 36), ((414, 354, 610, 530), 34)]:
    d.arc(box, start=205, end=335, fill=wave_color, width=width)
# Signal origin.
d.ellipse((490, 433, 534, 477), fill="#1464A5")

master = OUT / "icon_512x512@2x.png"
img.save(master)
for name, px in [
    ("icon_16x16.png", 16), ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32), ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128), ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256), ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
]:
    img.resize((px, px), Image.Resampling.LANCZOS).save(OUT / name)
print(OUT)
