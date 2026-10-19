import json, pathlib
from lxml import etree
import render_tmux as rt

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "fixtures/sample.json").read_text())
PORTRAIT = {"cols": 4, "rows": 2, "cell": [7, 13], "rows_runs": [[["@@", "#ffaa00"], ["  ", "#000000"]], [["    ", "#000000"]]]}


def svg(data=DATA, pal="dark", portrait=PORTRAIT):
    return rt.render(data, rt.PALETTES[pal], portrait)


def test_well_formed_and_sized():
    root = etree.fromstring(svg().encode())
    assert root.tag.endswith("svg") and root.get("width") == "900" and root.get("height") == "540"


def test_pane_titles_and_status_bar():
    s = svg()
    for t in ("0:portrait", "1:neofetch", "2:htop", "[cybertron288]", "1,284 commits", "318★", "2026-10-19"):
        assert t in s


def test_language_bars_proportional():
    root = etree.fromstring(svg().encode())
    bars = root.xpath('//*[@class="bar-fill"]')
    assert len(bars) == 4
    widths = [float(b.get("width")) for b in bars]
    assert abs(widths[0] / widths[1] - 46 / 31) < 0.02


def test_smil_animations_present():
    s = svg()
    assert s.count("<animate") >= 6                   # 4 bars + prompt clip + cursor
    assert 'dur="2.4s"' in s and 'begin="0.8s"' in s and 'values="1;0;1"' in s


def test_no_external_refs():
    s = svg()
    assert "http://" not in s.replace("http://www.w3.org", "") and "https://" not in s


def test_theme_color():
    assert rt.theme_color("#ffaa00", rt.PALETTES["dark"]) == "#ffaa00"
    assert rt.theme_color("#ffaa00", rt.PALETTES["light"]) == "#996600"


def test_empty_languages_and_commits():
    d = dict(DATA, languages=[], commits_recent=[])
    root = etree.fromstring(svg(d).encode())
    assert root.xpath('//*[@class="bar-fill"]') == []


def test_commit_message_escaped():
    d = dict(DATA, commits_recent=[{"sha": "abc1234", "msg": "fix <a> & \"b\"", "repo": "x/y", "age": "1h"}])
    etree.fromstring(svg(d).encode())          # must not raise
    assert "&lt;a&gt; &amp;" in svg(d)


def test_portrait_clipped_and_colored():
    s = svg(pal="light")
    assert 'clip-path="url(#portrait-clip)"' in s and "#996600" in s


def test_active_tab_text_uses_attribute_fill():
    root = etree.fromstring(svg().encode())
    tab = [t for t in root.iter("{http://www.w3.org/2000/svg}text") if (t.text or "").strip() == "1:neofetch*"]
    assert len(tab) == 1 and tab[0].get("fill") == rt.PALETTES["dark"]["bg"]
    style = root.find("{http://www.w3.org/2000/svg}style").text
    assert "text{fill" not in style.replace(" ", "")


def test_neofetch_values_fit_pane():
    assert all(v is None or len(v) <= 56 for v in rt.PROFILE.values())
