# tmux Hero README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the README's top block with a daily-regenerated, tmux-styled hero SVG (ASCII portrait + neofetch + htop/git-log panes + status bar) in dark and light variants.

**Architecture:** A one-off `scripts/portrait.py` turns the GitHub avatar into `assets/portrait.json` (color runs). A pure `render_tmux.py` turns a `data` dict + palette + portrait into SVG text. `today.py` (existing stats fetcher) gains three data sources and calls the renderer to write `assets/tmux-dark.svg` / `assets/tmux-light.svg`; the workflow commits them daily.

**Tech Stack:** Python 3.12, requests, python-dateutil, lxml (already in `requirements.txt`); pytest for tests; rembg + Pillow only in a throwaway `uv venv` for the portrait.

**Spec:** `docs/superpowers/specs/2026-10-19-tmux-hero-readme-design.md`

## Global Constraints

- Python 3.12; CI deps stay exactly `requests`, `python-dateutil`, `lxml` (+ `pytest` for tests). rembg/Pillow are never added to `requirements.txt`.
- SVG design width 900, height 540. No external `href`/`url(http…)`, no external fonts or images.
- Font stack inside SVG: `ConsolasFallback, Consolas, "JetBrains Mono", Menlo, monospace`, with the `@font-face` size-adjust block copied from `dark_mode.svg`. All `text, tspan { white-space: pre }`.
- Palettes exactly as in spec §Layout (dark: bg `#0d1117`, pane `#161b22`, border `#30363d`, fg `#e6edf3`, muted `#8b949e`, accent `#9370db`, key `#ffa657`, value `#a5d6ff`, green `#3fb950`, red `#f85149`, yellow `#d29922`, blue `#58a6ff`; light: bg `#ffffff`, pane `#f6f8fa`, border `#d0d7de`, fg `#1f2328`, muted `#656d76`, accent `#6f42c1`, key `#953800`, value `#0a3069`, green `#1a7f37`, red `#cf222e`, yellow `#9a6700`, blue `#0969da`).
- Animations are SMIL only: prompt clip-rect width `0→full` dur `2.4s` begin `0.8s` fill freeze; cursor `▍` opacity `1;0;1` dur `1s` indefinite; bar widths `0→value` dur `1.2s` staggered `0.15s` fill freeze.
- "Uptime" = GitHub account age from `createdAt`, formatted `N years, N months, N days`. Never a DOB.
- Git rules: work on `feat/update-profile-readme`; commit per task; no push unless asked.
- Workflow commit message: `chore: refresh tmux hero [skip ci]`.

## Review Focus

1. Zero public events (new/quiet account) → `commits_recent == []`; renderer must still emit a valid SVG with two blank log rows, not crash. (Task 3 + Task 2 tests.)
2. Commit message longer than the pane (>58 chars) → truncated with `…`, never overflowing the pane border. (Task 3 test.)
3. Repos with no languages / all-zero bytes → `languages == []`; renderer draws zero bars and no division by zero. (Task 3 + Task 2 tests.)
4. Portrait rows exceeding the pane (>32 rows) → `portrait.py` caps rows; renderer clips the portrait group to the pane. (Task 1 test + Task 2 clipPath.)
5. XML-special characters in commit messages (`<`, `&`, quotes) → escaped; SVG stays well-formed. (Task 2 test.)

---

### Task 1: Portrait generator → `assets/portrait.json`

**Files:**
- Create: `scripts/portrait.py`
- Create: `assets/portrait.json` (generated artifact, committed)
- Test: `tests/test_portrait.py`

**Interfaces:**
- Produces: `assets/portrait.json` with shape
  `{"cols": 44, "rows": int, "cell": [7, 13], "rows_runs": [[[text, "#rrggbb"], ...], ...]}`.
  Each row's runs concatenate to exactly `cols` characters (spaces for transparent cells).
- Produces (importable, pure): `cells_to_runs(cells: list[tuple[str, str]]) -> list[list[str]]`
  merging consecutive cells with identical color; `image_to_cells(img: "PIL.Image.Image", cols: int, max_rows: int) -> list[list[tuple[str, str]]]`.
- Constants: `COLS = 44`, `MAX_ROWS = 32`, `CELL = (7, 13)`, `RAMP = " .:-=+*#%@"`, `ALPHA_MIN = 60`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_portrait.py
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
    rows = portrait.image_to_cells(img, cols=portrait.COLS, max_rows=portrait.MAX_ROWS)
    assert all(len(r) == portrait.COLS for r in rows)
    assert len(rows) <= portrait.MAX_ROWS
    assert rows[0][0][0] == " "          # transparent -> blank
    assert rows[0][-1][0] != " "         # opaque -> glyph

def test_rows_capped():
    img = Image.new("RGBA", (44, 2000), (255, 255, 255, 255))
    rows = portrait.image_to_cells(img, cols=portrait.COLS, max_rows=portrait.MAX_ROWS)
    assert len(rows) == portrait.MAX_ROWS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_portrait.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'portrait'`

- [ ] **Step 3: Implement `scripts/portrait.py`**

Functions: `image_to_cells(img, cols, max_rows)` — alpha-crop to bbox (`ALPHA_MIN`), resize to `cols` wide with height `round(h * cols / w * CELL[0] / CELL[1])`, then center-crop/limit to `max_rows`; per pixel: alpha < `ALPHA_MIN` → `(" ", "#000000")`, else glyph = `RAMP[int(lum / 256 * len(RAMP))]` and color = RGB boosted (autocontrast + lift: `c = int(60 + c * 0.76)`) as hex. `cells_to_runs(cells)`. `main(src: str, out: str)` — opens `src`, runs `rembg.remove` (import inside `main` so tests need no rembg), calls the two functions, writes JSON. CLI: `python scripts/portrait.py <src> <out>`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_portrait.py -v`
Expected: 3 passed

- [ ] **Step 5: Generate the artifact**

```bash
S=/private/tmp/claude-501/-Users-cybertron-Downloads-Repos-cybertron288/cf967fcc-b7ee-4f5f-820c-a9a8169d2006/scratchpad
cd "$S" && uv venv pv && uv pip install --python pv/bin/python rembg pillow onnxruntime
curl -sL "https://github.com/cybertron288.png?size=1024" -o "$S/photo/avatar.png"
cd /Users/cybertron/Downloads/Repos/cybertron288 && "$S/pv/bin/python" scripts/portrait.py "$S/photo/avatar.png" assets/portrait.json
python3 -c "import json;d=json.load(open('assets/portrait.json'));print(d['cols'],d['rows'],sum(len(r) for r in d['rows_runs']))"
```
Expected: prints `44 <rows≤32> <run count>`; rows ≥ 20 (face fills the pane). If the face is tiny or clipped, adjust the crop padding in `image_to_cells` and rerun.

- [ ] **Step 6: Commit**

```bash
git add scripts/portrait.py assets/portrait.json tests/test_portrait.py
git commit -m "feat: generate color ASCII portrait runs from GitHub avatar"
```

---

### Task 2: `render_tmux.py` — pure SVG renderer

**Files:**
- Create: `render_tmux.py`
- Create: `fixtures/sample.json` (sample `data` dict, used by tests and Task 4)
- Test: `tests/test_render_tmux.py`

**Interfaces:**
- Consumes: portrait JSON shape from Task 1.
- Produces: `PALETTES: dict[str, dict[str, str]]` with keys `"dark"`, `"light"`, each having keys `name, bg, pane, border, fg, muted, accent, key, value, green, red, yellow, blue`.
- Produces: `render(data: dict, palette: dict, portrait: dict) -> str` (SVG text, XML-declaration first line).
- Produces: `theme_color(hex: str, palette: dict) -> str` — dark: unchanged; light: each channel `int(c * 0.6)`.
- Produces: `PROFILE` constant dict with the neofetch static lines: `Role: "SDE-2 · Healthlane Technologies"`, `Core: "Zango — Django framework (AZ, Pfizer, BMS, Roche, MSD)"`, `Building: "Igris — governance for AI agents (policy · audit · MCP)"`, `Langs: "Python, TypeScript, JavaScript"`, `Web: "React, Next.js, Django, Node.js"`, `Human: "English, Hindi, Gujarati"`, `Contact: "ravipatel288.jobs@gmail.com · in/ravipatel8407 · igrisecurity.com"`, and `PROMPT_CMD = 'echo "framework internals → AI governance"'`.
- `data` dict keys (all required): `login, name, generated` (YYYY-MM-DD), `uptime` (str), `commits, stars, repos, contrib_repos, followers` (int), `loc: {add, del, net}` (int), `languages: [{name, pct}]` (≤4), `commits_recent: [{sha, msg, repo, age}]` (≤2).
- Geometry constants: `W=900, H=540, TITLE_H=32, STATUS_H=34, LEFT_W=330, SPLIT_Y=278, LINE=19, FONT=13, PORTRAIT_FONT=11`.

- [ ] **Step 1: Write `fixtures/sample.json`**

```json
{"login":"cybertron288","name":"Ravi Patel","generated":"2026-10-19",
 "uptime":"6 years, 2 months, 11 days","commits":1284,"stars":318,"repos":42,"contrib_repos":57,"followers":64,
 "loc":{"add":523178,"del":76902,"net":446276},
 "languages":[{"name":"Python","pct":46},{"name":"TypeScript","pct":31},{"name":"JavaScript","pct":14},{"name":"Other","pct":9}],
 "commits_recent":[{"sha":"a1f3c2e","msg":"feat(igris): policy evaluation for mcp tool calls","repo":"igris/policy-engine","age":"2d"},
                   {"sha":"7b9e0d1","msg":"fix(zango): tenant-aware migrations on pg15","repo":"Healthlane-Technologies/Zango","age":"5d"}]}
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_render_tmux.py
import json, pathlib, re
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_render_tmux.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'render_tmux'`

- [ ] **Step 4: Implement `render_tmux.py`**

Build the SVG as an f-string/list of parts in this order: XML decl; `<svg xmlns width height font-family font-size>`; `<style>` (font-face block, `.k{fill:key} .v{fill:value} .m{fill:muted} .a{fill:accent} text,tspan{white-space:pre}`); `<defs>` with `<clipPath id="portrait-clip">` (left pane rect) and `<clipPath id="prompt-clip">` (rect with `<animate attributeName="width" from="0" to="{full}" dur="2.4s" begin="0.8s" fill="freeze"/>`); outer `rect` bg rx 8; title bar (three dots `#ff5f57 #febc2e #28c840`, text `ravi@cybertron288: ~ — tmux`); pane borders as `line`s in `border`; pane 0: title `┌ 0:portrait ─ cat ravi.ascii` then `<g clip-path="url(#portrait-clip)" font-size="11">` with one `<text>` per row at `y = top + i*13` and `<tspan fill="{theme_color}">` per run; pane 1: `ravi@cybertron288` in accent, `──` rule, then `PROFILE` rows as `<tspan class="k">Key</tspan><tspan class="m"> ... </tspan><tspan class="v">value</tspan>` with dot padding so values align (key column width 10 chars); pane 2: four bar rows (`name` padded to 11 chars, track `rect` in `pane` fill with `border` stroke, `rect class="bar-fill"` fill accent, `width = pct/100 * 300`, with `<animate attributeName="width" from="0" to="{w}" dur="1.2s" begin="{i*0.15}s" fill="freeze"/>`, pct text right-aligned), two log rows (`sha` yellow, msg truncated at 58 chars with `…`, `· age` muted; blank row if missing), prompt row (`ravi@cybertron288` green, `:` fg, `~` blue, `$ `, then `<text clip-path="url(#prompt-clip)">{PROMPT_CMD}</text>` and cursor `<text>▍<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></text>`); status bar: `rect` fill accent, tabs `[login] 0:portrait 1:neofetch* 2:htop` with the active tab on a `fg` rect in `bg` text, right side `{commits:,} commits · {stars}★ · {followers} followers · {generated}`. Escape all dynamic strings with `xml.sax.saxutils.escape(s, {'"': "&quot;"})`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_render_tmux.py -v`
Expected: 9 passed

- [ ] **Step 6: Visual check of the fixture render**

```bash
python3 -c "
import json, render_tmux as rt
d=json.load(open('fixtures/sample.json')); p=json.load(open('assets/portrait.json'))
for t in ('dark','light'): open(f'/tmp/tmux-{t}.svg','w').write(rt.render(d, rt.PALETTES[t], p))
"
qlmanage -t -s 1800 -o /tmp /tmp/tmux-dark.svg /tmp/tmux-light.svg >/dev/null 2>&1; ls /tmp/tmux-*.png
```
Open the PNGs (Read tool). Expected: three panes with borders, portrait fills the left pane without overflow, neofetch values aligned, four bars, two log rows, prompt line, status bar. Fix geometry constants until this holds; rerun tests.

- [ ] **Step 7: Commit**

```bash
git add render_tmux.py fixtures/sample.json tests/test_render_tmux.py
git commit -m "feat: pure tmux-style hero SVG renderer with dark/light palettes"
```

---

### Task 3: `today.py` data helpers — uptime, languages, recent commits

**Files:**
- Modify: `today.py` (add functions near `follower_getter`, ~line 335; add imports)
- Test: `tests/test_today_helpers.py`

**Interfaces:**
- Consumes: nothing new; uses existing `simple_request`, `HEADERS`, `USER_NAME`, `query_count` (extend `QUERY_COUNT` with `'languages_getter': 0, 'events_getter': 0`).
- Produces (pure, no network):
  - `format_uptime(created_at: str, now: datetime.datetime) -> str` — ISO `createdAt` → `"N years, N months, N days"` with singular/plural via existing `format_plural`.
  - `languages_from_edges(repo_edges: list[dict], top: int = 4) -> list[dict]` — sums `languages.edges[].size` by `node.name` across repos, returns `[{"name", "pct"}]` sorted desc, pct = integer percent of total (sum of returned pcts may be <100; no `Other` row), `[]` when total is 0.
  - `commits_from_events(events: list[dict], login: str, now: datetime.datetime, limit: int = 2) -> list[dict]` — walks `PushEvent`s newest-first, takes commits whose `author.name`/`author.email` matches the user's login or whose event `actor.login == login`, returns `[{"sha": sha[:7], "msg": first line truncated to 58 chars with "…", "repo": repo.name, "age": relative_age}]`.
  - `relative_age(iso: str, now: datetime.datetime) -> str` — `"<1h"`, `"3h"`, `"2d"`, `"5w"`, `"3mo"`.
- Produces (network): `languages_getter() -> list[dict]` (GraphQL, `repositories(first:100, ownerAffiliations: OWNER, isFork: false)` with `languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }`, paginate, then `languages_from_edges`); `events_getter() -> list[dict]` (REST `GET https://api.github.com/users/{USER_NAME}/events/public?per_page=100`, `HEADERS`; on non-200 return `[]`).
- Importing `today.py` must not require env vars: move `HEADERS`/`USER_NAME` reads to `os.environ.get(...)` with `''` defaults (lines 12–13).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_today_helpers.py
import datetime, today

NOW = datetime.datetime(2026, 10, 19, 21, 0, 0)

def test_format_uptime():
    assert today.format_uptime("2020-08-08T10:00:00Z", NOW) == "6 years, 2 months, 11 days"

def test_languages_from_edges_percentages_and_order():
    edges = [{"node": {"languages": {"edges": [{"size": 460, "node": {"name": "Python"}}, {"size": 310, "node": {"name": "TypeScript"}}]}}},
             {"node": {"languages": {"edges": [{"size": 140, "node": {"name": "JavaScript"}}, {"size": 90, "node": {"name": "CSS"}}, {"size": 1, "node": {"name": "Shell"}}]}}}]
    out = today.languages_from_edges(edges, top=4)
    assert [l["name"] for l in out] == ["Python", "TypeScript", "JavaScript", "CSS"]
    assert out[0]["pct"] == 45 and sum(l["pct"] for l in out) <= 100

def test_languages_empty():
    assert today.languages_from_edges([]) == []
    assert today.languages_from_edges([{"node": {"languages": {"edges": []}}}]) == []

def test_relative_age():
    assert today.relative_age("2026-10-19T20:30:00Z", NOW) == "<1h"
    assert today.relative_age("2026-10-19T15:00:00Z", NOW) == "6h"
    assert today.relative_age("2026-10-17T15:00:00Z", NOW) == "2d"
    assert today.relative_age("2026-09-10T15:00:00Z", NOW) == "5w"
    assert today.relative_age("2026-06-10T15:00:00Z", NOW) == "4mo"

def test_commits_from_events_truncates_and_limits():
    long = "feat(igris): " + "x" * 80
    events = [
        {"type": "WatchEvent", "actor": {"login": "cybertron288"}, "repo": {"name": "a/b"}, "created_at": "2026-10-19T20:00:00Z", "payload": {}},
        {"type": "PushEvent", "actor": {"login": "cybertron288"}, "repo": {"name": "igris/policy-engine"}, "created_at": "2026-10-17T20:00:00Z",
         "payload": {"commits": [{"sha": "c3333333333", "message": "third (oldest)", "author": {"name": "Ravi Patel", "email": "x@y"}},
                                 {"sha": "b2222222222", "message": "second", "author": {"name": "Ravi Patel", "email": "x@y"}},
                                 {"sha": "a1f3c2e9999", "message": long + "\n\nbody", "author": {"name": "Ravi Patel", "email": "x@y"}}]}},
    ]
    out = today.commits_from_events(events, "cybertron288", NOW, limit=2)
    assert len(out) == 2
    assert out[0]["sha"] == "a1f3c2e" and out[0]["age"] == "2d" and out[0]["repo"] == "igris/policy-engine"
    assert len(out[0]["msg"]) == 58 and out[0]["msg"].endswith("…")
    assert out[1]["msg"] == "second"

def test_commits_from_events_empty():
    assert today.commits_from_events([], "cybertron288", NOW) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_today_helpers.py -v`
Expected: FAIL (either `KeyError: 'ACCESS_TOKEN'` on import, or `AttributeError: module 'today' has no attribute 'format_uptime'`)

- [ ] **Step 3: Implement the helpers and fetchers in `today.py`**

Make the env reads import-safe first (`os.environ.get`). Then add the six functions from Interfaces. `commits_from_events` orders commits within a PushEvent newest-last per GitHub's payload, so reverse each event's `commits` list before taking. `relative_age` thresholds: `<1h` under 3600s, hours under 24h, days under 14d, weeks under 60d, else months (`days // 30`).

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_today_helpers.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add today.py tests/test_today_helpers.py
git commit -m "feat: add uptime, language and recent-commit data sources to today.py"
```

---

### Task 4: Wire `today.py` main → tmux SVGs, `--render-only`, remove old cards

**Files:**
- Modify: `today.py` (`__main__` block, lines ~372–400)
- Delete: `dark_mode.svg`, `light_mode.svg`
- Create: `assets/tmux-dark.svg`, `assets/tmux-light.svg` (rendered from fixture now; CI overwrites with real data)
- Test: `tests/test_today_render.py`

**Interfaces:**
- Consumes: `render_tmux.render`, `render_tmux.PALETTES`; Task 3 fetchers.
- Produces: `build_data(now: datetime.datetime) -> dict` (does all network calls, returns the `data` dict shape from Task 2) and `write_hero(data: dict, portrait_path: str = "assets/portrait.json", out_dir: str = "assets") -> list[str]` returning the two written paths.
- CLI: `python today.py` (full run) and `python today.py --render-only fixtures/sample.json` (no network; loads the dict from the file, calls `write_hero`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_today_render.py
import json, pathlib, subprocess, sys
from lxml import etree
ROOT = pathlib.Path(__file__).resolve().parents[1]

def test_render_only_writes_both_svgs(tmp_path):
    data = json.loads((ROOT / "fixtures/sample.json").read_text())
    import today
    paths = today.write_hero(data, portrait_path=str(ROOT / "assets/portrait.json"), out_dir=str(tmp_path))
    assert sorted(pathlib.Path(p).name for p in paths) == ["tmux-dark.svg", "tmux-light.svg"]
    for p in paths:
        etree.parse(p)

def test_cli_render_only(tmp_path):
    r = subprocess.run([sys.executable, "today.py", "--render-only", "fixtures/sample.json", "--out", str(tmp_path)], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "tmux-dark.svg").exists() and (tmp_path / "tmux-light.svg").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_today_render.py -v`
Expected: FAIL with `AttributeError: module 'today' has no attribute 'write_hero'`

- [ ] **Step 3: Implement `build_data`, `write_hero`, and argparse in `today.py`**

`build_data` reuses the existing `__main__` sequence (user_getter → loc_query → commit_counter → stars/repos/contrib → followers) plus `format_uptime(acc_date, now)`, `languages_getter()`, `commits_from_events(events_getter(), USER_NAME, now)`; `generated = now.strftime("%Y-%m-%d")`, `name = "Ravi Patel"`. Keep the timing printout for the full run. `write_hero` loads the portrait JSON, renders both palettes, writes `tmux-dark.svg`/`tmux-light.svg` into `out_dir`. argparse: `--render-only PATH`, `--out DIR` (default `assets`). Delete `svg_overwrite`/`justify_format`/`find_and_replace` and the `lxml` import if nothing else uses them.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/ -v`
Expected: all passed

- [ ] **Step 5: Produce committed SVGs and delete the old cards**

```bash
python3 today.py --render-only fixtures/sample.json
git rm -q --cached dark_mode.svg light_mode.svg 2>/dev/null; rm -f dark_mode.svg light_mode.svg
ls assets/
```
Expected: `portrait.json tmux-dark.svg tmux-light.svg`

- [ ] **Step 6: Commit**

```bash
git add today.py tests/test_today_render.py assets/tmux-dark.svg assets/tmux-light.svg
git commit -m "feat: render tmux hero SVGs from today.py with --render-only mode"
```

---

### Task 5: README, workflow, visual verification

**Files:**
- Modify: `README.md` (replace lines 1–20 header/neofetch block; delete the `### \`stats\`` section lines ~60–77; drop the komarev `<img>` at the end)
- Rename+Modify: `.github/workflows/stats-card.yml` → `.github/workflows/hero.yml`
- Modify: `requirements.txt` (add `pytest`) — or keep tests dev-only via `requirements-dev.txt`; choose `requirements-dev.txt` with `pytest` and `pillow`.

**Interfaces:**
- Consumes: `assets/tmux-dark.svg`, `assets/tmux-light.svg` from Task 4.

- [ ] **Step 1: Edit README.md**

Top of file becomes:

```html
<!-- cybertron288 · GitHub profile README · hero regenerated daily by today.py -->
<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/tmux-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="./assets/tmux-light.svg" />
  <img src="./assets/tmux-dark.svg" alt="ravi@cybertron288 — tmux session: ASCII portrait, neofetch, languages, recent commits" width="100%" />
</picture>
</div>
```

Remove: the typing-svg `<a><img …readme-typing-svg…></a>`, the old `<picture>` pointing at `dark_mode.svg`/`light_mode.svg`, the whole `### \`stats\`` section (both github-readme-stats images and streak-stats), and the komarev profile-views `<img>`. Keep `whoami`, `stack`, WakaTime markers, `contribution snake`, `find me` (three badges).

- [ ] **Step 2: Workflow**

`git mv .github/workflows/stats-card.yml .github/workflows/hero.yml`; set `name: Generate tmux hero`, step name `Generate hero SVGs`, `git add -A assets/tmux-dark.svg assets/tmux-light.svg cache`, commit message `chore: refresh tmux hero [skip ci]`. Keep cron `12 0 * * *`, `workflow_dispatch`, push-to-main trigger, `ACCESS_TOKEN`/`USER_NAME` env.

- [ ] **Step 3: Dev requirements + lint check of workflow YAML**

Create `requirements-dev.txt` with `pytest` and `pillow`. Run: `python3 -c "import yaml,sys;yaml.safe_load(open('.github/workflows/hero.yml'))" 2>/dev/null || ruby -ryaml -e 'YAML.load_file(".github/workflows/hero.yml")'`
Expected: no error.

- [ ] **Step 4: Render the README locally and screenshot**

```bash
python3 -m pytest tests -q
```
Then open `file:///Users/cybertron/Downloads/Repos/cybertron288/assets/tmux-dark.svg` and `…/tmux-light.svg` in Chrome (claude-in-chrome), screenshot each after ~3s so the typing animation has run. Expected: animation completes, cursor blinks, bars filled, no clipped text, portrait inside its pane. Fix and re-render (`python3 today.py --render-only fixtures/sample.json`) if not.

- [ ] **Step 5: Commit**

```bash
git add README.md .github/workflows/hero.yml requirements-dev.txt
git commit -m "feat: tmux-session hero replaces header, neofetch card and stat widgets"
```

- [ ] **Step 6: Report**

State in the final message: branch, commits, that `ACCESS_TOKEN` repo secret is missing (`gh secret list` empty) and must be added (fine-grained PAT, permissions listed atop `today.py`) before the daily workflow can refresh real numbers; until then the committed SVGs carry fixture numbers. Offer `/shipit`.
