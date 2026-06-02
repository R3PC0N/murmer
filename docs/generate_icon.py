"""
Generates a 512x512 Play Store icon from the murmur.svg design.
Run: python docs/generate_icon.py
Output: docs/current/murmur-icon-512.png
"""
from PIL import Image, ImageDraw

SCALE = 2  # 256 -> 512
SIZE = 256 * SCALE
DARK = (28, 28, 30, 255)    # #1c1c1e
AMBER = (200, 146, 42, 255) # #C8922A
TRANSPARENT = (0, 0, 0, 0)

img = Image.new("RGBA", (SIZE, SIZE), TRANSPARENT)
draw = ImageDraw.Draw(img)

# Background rounded rect (original: x=8,y=8,w=240,h=240,rx=46)
bg_x, bg_y = 8*SCALE, 8*SCALE
bg_w, bg_h = 240*SCALE, 240*SCALE
bg_r = 46*SCALE
draw.rounded_rectangle(
    [bg_x, bg_y, bg_x + bg_w, bg_y + bg_h],
    radius=bg_r,
    fill=DARK
)

# Waveform bars (original coords from murmur.svg, scaled 2x)
bars = [
    (25,  105, 20, 46),
    (56,  87,  20, 82),
    (87,  69,  20, 119),
    (118, 50,  20, 156),
    (149, 69,  20, 119),
    (180, 87,  20, 82),
    (211, 105, 20, 46),
]
for x, y, w, h in bars:
    x, y, w, h = x*SCALE, y*SCALE, w*SCALE, h*SCALE
    draw.rounded_rectangle([x, y, x+w, y+h], radius=10*SCALE, fill=AMBER)

out = "docs/current/murmur-icon-512.png"
img.save(out)
print(f"Saved: {out}  ({SIZE}x{SIZE}px)")
