"""Run this script once to generate murmer.ico."""
from PIL import Image, ImageDraw


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = max(1, size // 32)
    radius = max(4, int(size * 0.18))
    d.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius,
        fill="#1a1a1e",
    )

    bar_color = "#C8922A"
    heights_ratio = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25]
    n = len(heights_ratio)
    bar_w = max(2, int(size * 0.08))
    gap = max(1, int(size * 0.045))
    total_w = n * bar_w + (n - 1) * gap
    sx = (size - total_w) // 2
    cy = size // 2
    inner_h = size * 0.72
    bar_r = max(1, bar_w // 2)

    for i, ratio in enumerate(heights_ratio):
        h = max(2, int(inner_h * ratio))
        x = sx + i * (bar_w + gap)
        d.rounded_rectangle(
            [x, cy - h // 2, x + bar_w - 1, cy + h // 2],
            radius=bar_r,
            fill=bar_color,
        )

    return img


sizes = [16, 24, 32, 48, 64, 128, 256]
images = [_draw(s) for s in sizes]
images[0].save(
    "murmer.ico",
    format="ICO",
    append_images=images[1:],
    sizes=[(s, s) for s in sizes],
)
print("murmer.ico gegenereerd.")
