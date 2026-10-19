"""One-off: turn a photo into color ASCII runs for the tmux hero.

Usage: python scripts/portrait.py <photo> <out.json> [l,t,r,b crop fractions]

Requires rembg + Pillow (only at generation time; CI never runs this).
Output shape: {"cols", "rows", "cell": [w, h], "rows_runs": [[[text, "#rrggbb"], ...], ...]}
"""
import colorsys
import json
import sys

from PIL import Image, ImageOps

COLS = 60
MAX_ROWS = 32
CELL = (5, 10)
RAMP = " .:-=+*#%@"
OPAQUE_RAMP = RAMP[1:]  # an opaque pixel is never rendered blank
ALPHA_MIN = 60
BLANK = (" ", "#000000")


def boost_rgb(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Lift for dark backgrounds while keeping (even increasing) saturation."""
    h, s, v = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    r, g, b = colorsys.hsv_to_rgb(h, min(1.0, s * 1.35), v)
    return tuple(min(255, int(40 + c * 255 * 0.84)) for c in (r, g, b))


def image_to_cells(img: Image.Image, cols: int = COLS, max_rows: int = MAX_ROWS,
                   crop: tuple[float, float, float, float] | None = None) -> list[list[tuple[str, str]]]:
    """`crop` = (l, t, r, b) fractions of the alpha bounding box to keep, e.g. (0, 0, 0.7, 1)."""
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a >= ALPHA_MIN else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    if crop:
        w, h = img.size
        img = img.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
    w, h = img.size
    rows = max(1, round(h * cols / w * CELL[0] / CELL[1]))
    img = img.resize((cols, rows), Image.LANCZOS)
    if rows > max_rows:
        img = img.crop((0, 0, cols, max_rows))  # keep the top (head) when too tall
        rows = max_rows
    rgb = ImageOps.autocontrast(img.convert("RGB"))
    lum = rgb.convert("L")
    out = []
    for y in range(rows):
        row = []
        for x in range(cols):
            if img.getpixel((x, y))[3] < ALPHA_MIN:
                row.append(BLANK)
                continue
            glyph = OPAQUE_RAMP[min(len(OPAQUE_RAMP) - 1, lum.getpixel((x, y)) * len(OPAQUE_RAMP) // 256)]
            r, g, b = boost_rgb(rgb.getpixel((x, y)))
            row.append((glyph, f"#{r:02x}{g:02x}{b:02x}"))
        out.append(row)
    return out


def cells_to_runs(cells: list[tuple[str, str]]) -> list[list[str]]:
    runs: list[list[str]] = []
    for glyph, color in cells:
        if runs and runs[-1][1] == color:
            runs[-1][0] += glyph
        else:
            runs.append([glyph, color])
    return runs


def main(src: str, out: str, crop: tuple[float, float, float, float] | None = None) -> None:
    from rembg import remove  # heavy import; generation time only

    cutout = remove(Image.open(src))
    rows = image_to_cells(cutout, COLS, MAX_ROWS, crop=crop)
    data = {"cols": COLS, "rows": len(rows), "cell": list(CELL), "rows_runs": [cells_to_runs(r) for r in rows]}
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"{out}: {COLS}x{len(rows)}, {sum(len(r) for r in data['rows_runs'])} runs")


if __name__ == "__main__":
    # optional 3rd arg: crop fractions "l,t,r,b" of the subject box, e.g. "0,0,0.72,1"
    box = tuple(float(v) for v in sys.argv[3].split(",")) if len(sys.argv) > 3 else None
    main(sys.argv[1], sys.argv[2], box)
