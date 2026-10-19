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


def test_opaque_dark_pixel_never_blank():
    img = Image.new("RGBA", (44, 20), (8, 8, 8, 255))
    rows = portrait.image_to_cells(img, cols=portrait.COLS, max_rows=portrait.MAX_ROWS)
    assert all(cell[0] != " " for row in rows for cell in row)


def test_portrait_fills_pane_width():
    assert portrait.COLS * portrait.CELL[0] <= 308 and portrait.COLS * portrait.CELL[0] >= 290


def test_crop_fraction_limits_to_left_part():
    img = Image.new("RGBA", (100, 40), (255, 255, 255, 255))
    for x in range(70, 100):
        for y in range(40):
            img.putpixel((x, y), (0, 0, 0, 255))   # right 30% is black
    black = "#%02x%02x%02x" % portrait.boost_rgb((0, 0, 0))
    uncropped = {cell[1] for row in portrait.image_to_cells(img, cols=10, max_rows=32) for cell in row}
    cropped = {cell[1] for row in portrait.image_to_cells(img, cols=10, max_rows=32, crop=(0.0, 0.0, 0.7, 1.0)) for cell in row}
    assert black in uncropped and black not in cropped


def test_boost_rgb_keeps_saturation():
    r, g, b = portrait.boost_rgb((200, 30, 30))
    assert r - g >= 150 and r > 200
