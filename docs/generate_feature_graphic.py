"""
Generates a 1024x500 Play Store feature graphic in Murmur style.
Run: python docs/generate_feature_graphic.py
Output: docs/current/murmur-feature-graphic.png
"""
from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 500
DARK    = (28, 28, 30)       # #1c1c1e
AMBER   = (200, 146, 42)     # #C8922A
AMBER_D = (120, 87, 25)      # darker amber for shadow bars
WHITE   = (255, 255, 255)
GRAY    = (174, 174, 178)    # #aeaeb2

img = Image.new("RGB", (W, H), DARK)
draw = ImageDraw.Draw(img)

# --- Waveform bars ---
# 7 bars, bar_w=40, gap=20, total width=400
# Centered horizontally, centered vertically at y=210
BAR_W   = 40
GAP     = 20
STEP    = BAR_W + GAP
CENTER_Y = 210
CENTER_X = W // 2 - 3 * STEP - BAR_W // 2  # leftmost bar x (centered)

# Heights proportional to murmur.svg (46,82,119,156,119,82,46 scaled to max=200)
raw = [46, 82, 119, 156, 119, 82, 46]
max_raw = max(raw)
MAX_H = 200
heights = [int(v / max_raw * MAX_H) for v in raw]

RADIUS = BAR_W // 2

# Draw faint ghost bars behind (depth effect)
for i, h in enumerate(heights):
    x = CENTER_X + i * STEP
    y = CENTER_Y - h // 2
    ghost = (
        int(DARK[0] + (AMBER_D[0] - DARK[0]) * 0.35),
        int(DARK[1] + (AMBER_D[1] - DARK[1]) * 0.35),
        int(DARK[2] + (AMBER_D[2] - DARK[2]) * 0.35),
    )
    offset = 8
    draw.rounded_rectangle(
        [x + offset, y + offset, x + BAR_W + offset, y + h + offset],
        radius=RADIUS, fill=ghost
    )

# Draw main waveform bars
for i, h in enumerate(heights):
    x = CENTER_X + i * STEP
    y = CENTER_Y - h // 2
    draw.rounded_rectangle(
        [x, y, x + BAR_W, y + h],
        radius=RADIUS, fill=AMBER
    )

# --- Text ---
font_title = None
font_tag   = None
for path in [
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]:
    try:
        if font_title is None:
            font_title = ImageFont.truetype(path, 72)
        if font_tag is None:
            font_tag = ImageFont.truetype(path, 26)
        break
    except OSError:
        continue
if font_title is None:
    font_title = ImageFont.load_default()
if font_tag is None:
    font_tag = ImageFont.load_default()

title = "Murmur"
tag   = "Voice dictation. Your server. Your data."

draw.text((W // 2, 375), title, font=font_title, fill=WHITE, anchor="mm")
draw.text((W // 2, 450), tag,   font=font_tag,   fill=GRAY,  anchor="mm")

out = "docs/current/murmur-feature-graphic.png"
img.save(out)
print(f"Saved: {out}  ({W}x{H}px)")
