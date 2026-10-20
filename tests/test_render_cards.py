import json, pathlib
from lxml import etree
import render_cards as rc
from render_tmux import PALETTES

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "fixtures/sample.json").read_text())
NS = "{http://www.w3.org/2000/svg}"


def parse(s):
    return etree.fromstring(s.encode())


def test_cards_well_formed_and_sized():
    for key in rc.PROJECTS:
        root = parse(rc.render_card(key, DATA, PALETTES["dark"]))
        assert root.get("width") == str(rc.CARD_W) and root.get("height") == str(rc.CARD_H)


def test_repo_cards_show_live_stars_and_repo():
    s = rc.render_card("nova-memory", DATA, PALETTES["dark"])
    assert "★ 1" in s and "cybertron288/nova-memory" in s and "MCP" in s
    s = rc.render_card("contrib-matrix", DATA, PALETTES["dark"])
    assert "★ 0" in s and "WLED" in s


def test_zango_packages_card_has_status_no_stars():
    s = rc.render_card("zango-packages", DATA, PALETTES["dark"])
    assert "9 packages" in s and "@zango-core" in s and "★" not in s and "building" not in s


def test_four_cards_two_repo_backed():
    assert list(rc.PROJECTS) == ["zango-packages", "igris", "nova-memory", "contrib-matrix"]
    assert [k for k, v in rc.PROJECTS.items() if "repo" in v] == ["nova-memory", "contrib-matrix"]


def test_igris_card_status_and_site():
    s = rc.render_card("igris", DATA, PALETTES["dark"])
    assert "building" in s and "igrisecurity.com" in s


def test_card_flow_boxes_fit_inside_card():
    for key in rc.PROJECTS:
        root = parse(rc.render_card(key, DATA, PALETTES["dark"]))
        boxes = root.xpath('//*[@class="flow-box"]')
        assert len(boxes) == 4
        for b in boxes:
            assert float(b.get("x")) >= rc.PAD and float(b.get("x")) + float(b.get("width")) <= rc.CARD_W - rc.PAD


def test_card_header_title_sub_and_badge_do_not_overlap():
    for key in rc.PROJECTS:
        sub_end, badge_start = rc.header_span(key, DATA, PALETTES["dark"])
        assert sub_end + 8 <= badge_start, key


def test_card_text_lines_fit_inside_card():
    for key in rc.PROJECTS:
        for line in rc.card_lines(key, DATA):
            assert rc.PAD + len(line) * rc.CHAR <= rc.CARD_W - rc.PAD, line


def test_card_without_cards_data_falls_back():
    d = {k: v for k, v in DATA.items() if k != "cards"}
    s = rc.render_card("nova-memory", d, PALETTES["dark"])
    parse(s)
    assert "★" not in s and "open source" in s


def test_activity_one_bar_per_week_tallest_at_peak():
    root = parse(rc.render_activity(DATA, PALETTES["dark"]))
    bars = root.xpath('//*[@class="week"]')
    weekly = DATA["activity"]["weekly"]
    assert len(bars) == len(weekly)
    heights = [float(b.get("height")) for b in bars]
    assert heights.index(max(heights)) == weekly.index(max(weekly))
    assert all(h > 0 for h in heights)


def test_activity_caption_and_axis():
    text = "".join(parse(rc.render_activity(DATA, PALETTES["dark"])).itertext())
    assert "3,253 contributions" in text and "Oct ’25" in text and "Oct ’26" in text


def test_activity_stack_tokens_fit_width():
    root = parse(rc.render_activity(DATA, PALETTES["dark"]))
    toks = root.xpath('//*[@class="tok"]')
    assert len(toks) == sum(len(t) for _, t in rc.STACK)
    for t in toks:
        assert float(t.get("x")) + float(t.get("width")) <= rc.STRIP_W - rc.PAD


def test_activity_without_data_still_renders_stack():
    d = {k: v for k, v in DATA.items() if k != "activity"}
    root = parse(rc.render_activity(d, PALETTES["light"]))
    assert root.xpath('//*[@class="week"]') == [] and root.xpath('//*[@class="tok"]')


def test_bars_animate_and_no_external_refs():
    s = rc.render_activity(DATA, PALETTES["dark"])
    assert s.count("<animate") >= 2 * len(DATA["activity"]["weekly"])
    for key in rc.PROJECTS:
        s += rc.render_card(key, DATA, PALETTES["light"])
    assert "https://" not in s and "http://" not in s.replace("http://www.w3.org", "")


def test_light_palette_differs():
    assert rc.render_card("igris", DATA, PALETTES["dark"]) != rc.render_card("igris", DATA, PALETTES["light"])
