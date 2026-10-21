import json, pathlib
from lxml import etree
import render_tmux as rt

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "fixtures/sample.json").read_text())


def svg(data=DATA, pal="dark"):
    return rt.render(data, rt.PALETTES[pal])


def test_well_formed_and_sized():
    root = etree.fromstring(svg().encode())
    assert root.tag.endswith("svg") and root.get("width") == "900" and root.get("height") == "540"


def test_pane_titles_and_status_bar():
    s = svg()
    for t in ("0:banner", "1:neofetch", "2:htop", "[cybertron288]", "1,284 commits", "318★", "2026-10-19"):
        assert t in s


def test_language_bars_proportional():
    root = etree.fromstring(svg().encode())
    bars = root.xpath('//*[@class="bar-fill"]')
    assert len(bars) == 4
    widths = [float(b.get("width")) for b in bars]
    assert abs(widths[0] / widths[-1] - 31 / 46) < 0.02    # TypeScript first, Python last


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


def test_banner_replaces_portrait():
    s = svg()
    assert "portrait" not in s and "figlet ravi" in s


def test_banner_lines_share_width_and_fit_pane():
    root = etree.fromstring(svg().encode())
    rows = root.xpath('//*[@class="banner"]/*[local-name()="text"]')
    assert len(rows) == len(rt.BANNER) == 6
    assert {r.get("textLength") for r in rows} == {str(rt.BANNER_W)}
    assert rt.PAD + rt.BANNER_W <= rt.LEFT_W - rt.PAD
    assert len({len(line) for line in rt.BANNER}) == 1      # equal columns keep letters aligned


def test_banner_uses_theme_accent():
    for pal in ("dark", "light"):
        g = etree.fromstring(svg(pal=pal).encode()).xpath('//*[@class="banner"]')[0]
        assert g.get("fill") == rt.PALETTES[pal]["accent"]


def test_banner_tagline_and_projects():
    s = svg()
    assert "framework internals" in s and "AI governance" in s and "zango · igris · nova-memory" in s


def test_active_tab_text_uses_attribute_fill():
    root = etree.fromstring(svg().encode())
    tab = [t for t in root.iter("{http://www.w3.org/2000/svg}text") if (t.text or "").strip() == "1:neofetch*"]
    assert len(tab) == 1 and tab[0].get("fill") == rt.PALETTES["dark"]["bg"]
    style = root.find("{http://www.w3.org/2000/svg}style").text
    assert "text{fill" not in style.replace(" ", "")


def test_neofetch_values_fit_pane():
    assert all(v is None or len(v) <= 56 for v in rt.PROFILE.values())


def test_portfolio_link_in_neofetch():
    assert "ravip-portfolio.vercel.app" in svg()


def test_languages_ordered_python_last():
    langs = [{"name": n, "pct": p} for n, p in (("Python", 46), ("TypeScript", 31), ("CSS", 9), ("JavaScript", 14), ("Shell", 1))]
    assert [l["name"] for l in rt.ordered_languages(langs)] == ["TypeScript", "JavaScript", "CSS", "Python"]
    assert "TypeScript, JavaScript, Python" in svg()
