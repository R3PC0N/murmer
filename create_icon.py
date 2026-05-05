"""Run this script once to generate murmur.ico, murmur.svg, and Android launcher icons."""
import os
from PIL import Image, ImageDraw


def _draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    margin = max(1, size // 32)
    radius = max(4, int(size * 0.18))
    d.rounded_rectangle(
        [margin, margin, size - margin - 1, size - margin - 1],
        radius=radius,
        fill="#1c1c1e",  # matches live site (index-alt.html)
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


def _make_svg(size: int = 256, bg_color: str = "#1a1a1e", bar_color: str = "#C8922A") -> str:
    """Generate a scalable SVG of the waveform icon using the same parameters as _draw()."""
    heights_ratio = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25]
    n = len(heights_ratio)

    margin  = max(1, size // 32)
    radius  = max(4, int(size * 0.18))
    bar_w   = max(2, int(size * 0.08))
    gap     = max(1, int(size * 0.045))
    total_w = n * bar_w + (n - 1) * gap
    sx      = (size - total_w) // 2
    cy      = size // 2
    inner_h = size * 0.72
    bar_r   = max(1, bar_w // 2)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg"',
        f'     viewBox="0 0 {size} {size}" width="{size}" height="{size}">',
        f'  <!-- background -->',
        f'  <rect x="{margin}" y="{margin}"',
        f'        width="{size - 2 * margin}" height="{size - 2 * margin}"',
        f'        rx="{radius}" ry="{radius}" fill="{bg_color}"/>',
        f'  <!-- waveform bars -->',
    ]

    for i, ratio in enumerate(heights_ratio):
        h = max(2, int(inner_h * ratio))
        x = sx + i * (bar_w + gap)
        y = cy - h // 2
        parts.append(
            f'  <rect x="{x}" y="{y}" width="{bar_w}" height="{h}"'
            f' rx="{bar_r}" ry="{bar_r}" fill="{bar_color}"/>'
        )

    parts.append('</svg>')
    return '\n'.join(parts)


sizes = [16, 24, 32, 48, 64, 128, 256]
images = [_draw(s) for s in sizes]
images[0].save(
    "murmur.ico",
    format="ICO",
    append_images=images[1:],
    sizes=[(s, s) for s in sizes],
)
print("murmur.ico gegenereerd.")

# ── SVG variants ─────────────────────────────────────────────────────────────
SVG_VARIANTS = [
    ("murmur.svg",            "#1c1c1e", "#C8922A"),  # app grey (matches live site + .ico)
    ("murmur-warm-dark.svg",  "#100B07", "#C8923A"),  # warm dark (landing page dark theme)
    ("murmur-light.svg",      "#F5EADA", "#8B5820"),  # warm light (landing page light theme)
]

for filename, bg, bars in SVG_VARIANTS:
    with open(filename, "w", encoding="utf-8") as f:
        f.write(_make_svg(256, bg_color=bg, bar_color=bars))
    print(f"{filename} gegenereerd.")


# ── Android launcher icons ────────────────────────────────────────────────────
def _rounded_rect_path(x, y, w, h, r):
    """Android vector path data for a rounded rectangle."""
    return (
        f"M {x+r},{y} L {x+w-r},{y} Q {x+w},{y} {x+w},{y+r} "
        f"L {x+w},{y+h-r} Q {x+w},{y+h} {x+w-r},{y+h} "
        f"L {x+r},{y+h} Q {x},{y+h} {x},{y+h-r} "
        f"L {x},{y+r} Q {x},{y} {x+r},{y} Z"
    )


def _generate_android_icons(project_root):
    """Write Android launcher PNGs + adaptive icon XMLs into mobile/android/…/res/."""
    bar_color = "#C8922A"
    bg_color  = "#1c1c1e"
    res_dir   = os.path.join(
        project_root, "mobile", "android", "app", "src", "main", "res"
    )

    # ── Legacy PNGs (one per density) ────────────────────────────────────────
    densities = {
        "mipmap-mdpi":    48,
        "mipmap-hdpi":    72,
        "mipmap-xhdpi":   96,
        "mipmap-xxhdpi":  144,
        "mipmap-xxxhdpi": 192,
    }
    for density, size in densities.items():
        out_dir = os.path.join(res_dir, density)
        os.makedirs(out_dir, exist_ok=True)
        _draw(size).save(os.path.join(out_dir, "ic_launcher.png"))
        print(f"  {density}/ic_launcher.png  ({size}x{size})")

    # ── Adaptive icon foreground vector (108×108dp viewport, bars only) ───────
    vp = 108
    heights_ratio = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25]
    n       = len(heights_ratio)
    # Scale all dimensions uniformly so proportions match the logo exactly,
    # but smaller to fit within the adaptive icon safe zone (18dp margin each side).
    # At fg_scale=0.65: bars span x=27..80, well inside the 18-90 safe zone.
    fg_scale = 0.65
    bar_w   = max(2, int(vp * 0.08  * fg_scale))  # 5
    gap     = max(1, int(vp * 0.045 * fg_scale))  # 3
    total_w = n * bar_w + (n - 1) * gap
    sx      = (vp - total_w) // 2
    cy      = vp // 2
    inner_h = vp * 0.72 * fg_scale                # 50.5
    bar_r   = max(1, bar_w // 2)                  # 2

    path_elements = []
    for i, ratio in enumerate(heights_ratio):
        h = max(2, int(inner_h * ratio))
        x = sx + i * (bar_w + gap)
        y = cy - h // 2
        pd = _rounded_rect_path(x, y, bar_w, h, bar_r)
        path_elements.append(
            f'  <path android:fillColor="{bar_color}"\n'
            f'        android:pathData="{pd}"/>'
        )

    drawable_dir = os.path.join(res_dir, "drawable")
    os.makedirs(drawable_dir, exist_ok=True)

    foreground_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<vector xmlns:android="http://schemas.android.com/apk/res/android"\n'
        f'    android:width="{vp}dp"\n'
        f'    android:height="{vp}dp"\n'
        f'    android:viewportWidth="{vp}"\n'
        f'    android:viewportHeight="{vp}">\n'
        + "\n".join(path_elements) + "\n"
        "</vector>"
    )
    with open(os.path.join(drawable_dir, "ic_launcher_foreground.xml"), "w") as f:
        f.write(foreground_xml)
    print("  drawable/ic_launcher_foreground.xml")

    # ── Adaptive icon background (solid colour) ───────────────────────────────
    background_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<shape xmlns:android="http://schemas.android.com/apk/res/android">\n'
        f'    <solid android:color="{bg_color}"/>\n'
        "</shape>"
    )
    with open(os.path.join(drawable_dir, "ic_launcher_background.xml"), "w") as f:
        f.write(background_xml)
    print("  drawable/ic_launcher_background.xml")

    # ── Adaptive icon manifest (API 26+) ──────────────────────────────────────
    anydpi_dir = os.path.join(res_dir, "mipmap-anydpi-v26")
    os.makedirs(anydpi_dir, exist_ok=True)
    adaptive_xml = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@drawable/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@drawable/ic_launcher_foreground"/>\n'
        "</adaptive-icon>"
    )
    with open(os.path.join(anydpi_dir, "ic_launcher.xml"), "w") as f:
        f.write(adaptive_xml)
    print("  mipmap-anydpi-v26/ic_launcher.xml")


print("\nAndroid launcher icons:")
_generate_android_icons(os.path.dirname(os.path.abspath(__file__)))
