"""
Generates murmur-logo-email.png for use in HTML emails.
Run from the repo root: python docs/generate_logo.py
Output: docs/current/murmur-logo-email.png (2x / 320x48px for retina)
"""
from PIL import Image, ImageDraw, ImageFont

SCALE = 2
W, H = 160 * SCALE, 24 * SCALE
AMBER = (200, 146, 42, 255)
WHITE = (255, 255, 255, 255)

img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Waveform bars (center-aligned within 24px, scaled 2x)
bars = [
    (0,  9, 4, 6),
    (7,  6, 4, 11),
    (14, 4, 4, 16),
    (21, 2, 4, 20),
    (28, 4, 4, 16),
    (35, 6, 4, 11),
    (42, 9, 4, 6),
]
for x, y, w, h in bars:
    x, y, w, h = x*SCALE, y*SCALE, w*SCALE, h*SCALE
    draw.rounded_rectangle([x, y, x+w-1, y+h-1], radius=4, fill=AMBER)

# "Murmur" text — try Segoe UI, fall back to Arial, then default
font = None
for path in [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]:
    try:
        font = ImageFont.truetype(path, 18 * SCALE)
        break
    except OSError:
        continue
if font is None:
    font = ImageFont.load_default()

text_x = 56 * SCALE
text_y = H // 2
draw.text((text_x, text_y), "Murmur", font=font, fill=WHITE, anchor="lm")

out = "docs/current/murmur-logo-email.png"
img.save(out)
print(f"Saved: {out}  ({W}x{H}px)")
