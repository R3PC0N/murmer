"""
Generates Android ic_launcher.png at all mipmap densities.
Run: python docs/generate_mipmap_icons.py
Outputs to: mobile/android/app/src/main/res/mipmap-*/ic_launcher.png

Uses the same Murmur waveform design as the 512x512 Play Store icon,
scaled down to each density size.
"""
from PIL import Image, ImageDraw
import os

DARK  = (28, 28, 30)    # #1c1c1e  (used as solid RGB background)
AMBER = (200, 146, 42)  # #C8922A

# Design is defined in a 256×256 coordinate space (same as murmur.svg)
BASE = 256

# (x, y, width, height) for each waveform bar
BASE_BARS = [
    (25,  105, 20,  46),
    (56,   87, 20,  82),
    (87,   69, 20, 119),
    (118,  50, 20, 156),
    (149,  69, 20, 119),
    (180,  87, 20,  82),
    (211, 105, 20,  46),
]
BASE_BAR_R = 10  # corner radius

DENSITIES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

# Path to the Android res directory (relative to repo root)
RES_DIR = os.path.join(
    os.path.dirname(__file__), "..",
    "mobile", "android", "app", "src", "main", "res"
)

for density, size in DENSITIES.items():
    scale = size / BASE

    # Solid dark background — no transparent corners.
    # Transparent corners cause white border artifacts in Android Settings UI
    # (which renders the legacy PNG against its own background color).
    # On Android 8+ the adaptive icon XML is used for the launcher anyway.
    img  = Image.new("RGB", (size, size), (28, 28, 30))
    draw = ImageDraw.Draw(img)

    # Waveform bars
    bar_r = max(1, int(BASE_BAR_R * scale))
    for bx, by, bw, bh in BASE_BARS:
        x = int(bx * scale)
        y = int(by * scale)
        w = max(1, int(bw * scale))
        h = max(1, int(bh * scale))
        draw.rounded_rectangle([x, y, x + w, y + h], radius=bar_r, fill=AMBER)

    out_dir  = os.path.join(RES_DIR, density)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ic_launcher.png")
    img.save(out_path)
    print(f"Saved: {out_path}  ({size}×{size}px)")

print("Done — rebuild the Flutter app to pick up the new icons.")
