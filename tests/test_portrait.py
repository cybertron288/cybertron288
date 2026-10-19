import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
from PIL import Image
import portrait


def test_cells_to_runs_merges_same_color():
    cells = [("@", "#ffffff"), ("#", "#ffffff"), (" ", "#000000"), ("@", "#ffffff")]
    assert portrait.cells_to_runs(cells) == [["@#", "#ffffff"], [" ", "#000000"], ["@", "#ffffff"]]


def test_image_to_cells_shape_and_transparency():
    img = Image.new("RGBA", (88, 52), (0, 0, 0, 0))
    for x in range(44, 88):
        for y in range(52):
            img.putpixel((x, y), (200, 120, 60, 255))
    img.putpixel((0, 51), (200, 120, 60, 255))  # anchor bbox at x=0 so the top-left corner stays transparent
    rows = portrait.image_to_cells(img, cols=portrait.COLS, max_rows=portrait.MAX_ROWS)
    assert all(len(r) == portrait.COLS for r in rows)
    assert len(rows) <= portrait.MAX_ROWS
    assert rows[0][0][0] == " "          # transparent -> blank
    assert rows[0][-1][0] != " "         # opaque -> glyph


def test_rows_capped():
    img = Image.new("RGBA", (44, 2000), (255, 255, 255, 255))
    rows = portrait.image_to_cells(img, cols=portrait.COLS, max_rows=portrait.MAX_ROWS)
    assert len(rows) == portrait.MAX_ROWS
