"""One-off: turn a photo into color ASCII runs for the tmux hero.

Usage: python scripts/portrait.py <photo> <out.json>

Requires rembg + Pillow (only at generation time; CI never runs this).
Output shape: {"cols", "rows", "cell": [w, h], "rows_runs": [[[text, "#rrggbb"], ...], ...]}
"""
import json
import sys

from PIL import Image, ImageOps

COLS = 44
MAX_ROWS = 32
CELL = (7, 13)
RAMP = " .:-=+*#%@"
ALPHA_MIN = 60
BLANK = (" ", "#000000")


def _boost(c: int) -> int:
    return min(255, int(60 + c * 0.76))


def image_to_cells(img: Image.Image, cols: int = COLS, max_rows: int = MAX_ROWS) -> list[list[tuple[str, str]]]:
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a >= ALPHA_MIN else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
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
            glyph = RAMP[min(len(RAMP) - 1, lum.getpixel((x, y)) * len(RAMP) // 256)]
            r, g, b = (_boost(c) for c in rgb.getpixel((x, y)))
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


def main(src: str, out: str) -> None:
    from rembg import remove  # heavy import; generation time only

    cutout = remove(Image.open(src))
    rows = image_to_cells(cutout, COLS, MAX_ROWS)
    data = {"cols": COLS, "rows": len(rows), "cell": list(CELL), "rows_runs": [cells_to_runs(r) for r in rows]}
    with open(out, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    print(f"{out}: {COLS}x{len(rows)}, {sum(len(r) for r in data['rows_runs'])} runs")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
