"""Pure renderer: data dict + palette + portrait runs -> tmux-styled hero SVG.

No network, no files. `today.py` feeds it real numbers; tests feed it fixtures.
"""
from xml.sax.saxutils import escape as _esc

W, H = 900, 540
TITLE_H, STATUS_H = 32, 34
LEFT_W, SPLIT_Y = 330, 278
LINE, FONT = 19, 12
PAD = 14
CHAR = 7.2  # approx advance of one glyph at FONT px in the Consolas-ish stack
TRACK_W = 300
MSG_MAX = 58

PALETTES = {
    "dark": dict(name="dark", bg="#0d1117", pane="#161b22", border="#30363d", fg="#e6edf3", muted="#8b949e",
                 accent="#9370db", key="#ffa657", value="#a5d6ff", green="#3fb950", red="#f85149",
                 yellow="#d29922", blue="#58a6ff"),
    "light": dict(name="light", bg="#ffffff", pane="#f6f8fa", border="#d0d7de", fg="#1f2328", muted="#656d76",
                  accent="#6f42c1", key="#953800", value="#0a3069", green="#1a7f37", red="#cf222e",
                  yellow="#9a6700", blue="#0969da"),
}

PROFILE = {
    "Role": "SDE-2 · Healthlane Technologies",
    "Core": "Zango — Django framework (AZ, Pfizer, BMS, Roche, MSD)",
    "Building": "Igris — governance for AI agents (policy · audit · MCP)",
    "Uptime": None,  # filled from data["uptime"]
    "Langs": "Python, TypeScript, JavaScript",
    "Web": "React, Next.js, Django, Node.js",
    "Human": "English, Hindi, Gujarati",
    "Contact": "ravipatel288.jobs@gmail.com · in/ravipatel8407",
    "Site": "ravip-portfolio.vercel.app · igrisecurity.com",
}
PROMPT_CMD = 'echo "framework internals → AI governance"'

FONT_FACE = """@font-face {
  src: local('Consolas'), local('Consolas Bold');
  font-family: 'ConsolasFallback';
  font-display: swap;
  -webkit-size-adjust: 109%;
  size-adjust: 109%;
}"""


def esc(s) -> str:
    return _esc(str(s), {'"': "&quot;"})


def theme_color(hex_color: str, palette: dict) -> str:
    if palette["name"] != "light":
        return hex_color
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * 0.6), int(g * 0.6), int(b * 0.6))


def _text(x, y, content, cls="", fill=None, extra=""):
    attrs = f' x="{x}" y="{y}"'
    if cls:
        attrs += f' class="{cls}"'
    if fill:
        attrs += f' fill="{fill}"'
    return f"<text{attrs}{extra}>{content}</text>"


def _pane_title(x, y, label, suffix, p):
    return _text(x, y, f'<tspan class="m">┌ </tspan><tspan class="a">{esc(label)}</tspan><tspan class="m"> ─ {esc(suffix)}</tspan>')


def _portrait_pane(portrait, p):
    parts = [_pane_title(PAD, TITLE_H + 20, "0:portrait", "cat ravi.ascii", p)]
    cols = portrait["cols"]
    cell_w, cell_h = portrait.get("cell", [5, 10])
    top = TITLE_H + 34
    width = cols * cell_w
    parts.append(f'<g clip-path="url(#portrait-clip)" font-size="{cell_h - 1}px" font-weight="bold">')
    for i, runs in enumerate(portrait["rows_runs"]):
        spans = "".join(f'<tspan fill="{theme_color(color, p)}">{esc(text)}</tspan>' for text, color in runs)
        parts.append(f'<text x="{PAD}" y="{top + i * cell_h}" textLength="{width}" lengthAdjust="spacing">{spans}</text>')
    parts.append("</g>")
    return parts, top + len(portrait["rows_runs"]) * cell_h


def _kv(x, y, key, value, key_w=9):
    dots = "." * max(1, key_w - len(key))
    return _text(x, y, f'<tspan class="k">{esc(key)}</tspan><tspan class="m"> {dots} </tspan><tspan class="v">{esc(value)}</tspan>')


def _neofetch_pane(data, p):
    x = LEFT_W + PAD
    y = TITLE_H + 20
    parts = [_pane_title(x, y, "1:neofetch", "", p).replace(" ─ </tspan>", "</tspan>")]
    y += LINE + 4
    parts.append(_text(x, y, f'<tspan class="a" font-weight="bold">ravi@{esc(data["login"])}</tspan><tspan class="m"> {"─" * 46}</tspan>'))
    for key, value in PROFILE.items():
        y += LINE
        parts.append(_kv(x, y, key, data["uptime"] if key == "Uptime" else value))
    return parts


def _htop_pane(data, p):
    x = LEFT_W + PAD
    y = SPLIT_Y + 20
    parts = [_pane_title(x, y, "2:htop", "languages · public repos", p)]
    y += LINE + 2
    track_x = x + 12 * CHAR
    for i, lang in enumerate(data["languages"][:4]):
        w = round(TRACK_W * lang["pct"] / 100, 1)
        parts.append(_text(x, y, esc(lang["name"][:11])))
        parts.append(f'<rect x="{track_x:.0f}" y="{y - 9}" width="{TRACK_W}" height="9" rx="1" fill="{p["pane"]}" stroke="{p["border"]}"/>')
        parts.append(f'<rect class="bar-fill" x="{track_x:.0f}" y="{y - 9}" width="{w}" height="9" rx="1" fill="{p["accent"]}">'
                     f'<animate attributeName="width" from="0" to="{w}" dur="1.2s" begin="{i * 0.15:.2f}s" fill="freeze"/></rect>')
        parts.append(_text(f"{track_x + TRACK_W + 44:.0f}", y, f'{lang["pct"]}%', cls="m", extra=' text-anchor="end"'))
        y += LINE
    y += 6
    rows = list(data["commits_recent"][:2]) + [None] * (2 - len(data["commits_recent"][:2]))
    for c in rows:
        if c:
            msg = c["msg"] if len(c["msg"]) <= MSG_MAX else c["msg"][:MSG_MAX - 1] + "…"
            parts.append(_text(x, y, f'<tspan fill="{p["yellow"]}">{esc(c["sha"])}</tspan> {esc(msg)}<tspan class="m"> · {esc(c["age"])}</tspan>'))
        y += LINE
    y += 4
    prefix = f'ravi@{data["login"]}:~$ '
    cmd_x = x + len(prefix) * CHAR
    cmd_w = len(PROMPT_CMD) * CHAR + 4
    parts.append(f'<clipPath id="prompt-clip"><rect x="{cmd_x:.1f}" y="{y - 14}" width="0" height="{LINE}">'
                 f'<animate attributeName="width" from="0" to="{cmd_w:.1f}" dur="2.4s" begin="0.8s" fill="freeze"/></rect></clipPath>')
    parts.append(_text(x, y, f'<tspan fill="{p["green"]}">ravi@{esc(data["login"])}</tspan>:<tspan fill="{p["blue"]}">~</tspan>$ '))
    parts.append(_text(f"{cmd_x:.1f}", y, esc(PROMPT_CMD), extra=' clip-path="url(#prompt-clip)"'))
    parts.append(f'<text x="{cmd_x:.1f}" y="{y}" fill="{p["fg"]}">▍'
                 f'<animate attributeName="x" from="{cmd_x:.1f}" to="{cmd_x + cmd_w - 4:.1f}" dur="2.4s" begin="0.8s" fill="freeze"/>'
                 f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></text>')
    return parts


def _status_bar(data, p):
    y0 = H - STATUS_H
    ty = y0 + 22
    parts = [f'<rect x="0" y="{y0}" width="{W}" height="{STATUS_H}" fill="{p["accent"]}"/>']
    x = PAD
    tabs = [(f'[{data["login"]}]', False), ("0:portrait", False), ("1:neofetch*", True), ("2:htop", False)]
    for label, active in tabs:
        w = (len(label) + 2) * CHAR
        if active:
            parts.append(f'<rect x="{x:.0f}" y="{y0 + 6}" width="{w:.0f}" height="{STATUS_H - 12}" rx="2" fill="{p["fg"]}"/>')
        parts.append(_text(f"{x + CHAR:.0f}", ty, esc(label), fill=p["bg"] if active else p["bg"], extra=' font-weight="bold"' if active else ""))
        x += w + CHAR
    right = f'{data["commits"]:,} commits · {data["stars"]}★ · {data["followers"]} followers · {data["generated"]}'
    parts.append(_text(W - PAD, ty, esc(right), fill=p["bg"], extra=' text-anchor="end"'))
    return parts


def _left_footer(data, p, y):
    loc = data["loc"]
    y = max(y + LINE + 6, H - STATUS_H - 3 * LINE)
    return [
        _text(PAD, y, f'<tspan class="m">└ </tspan><tspan class="k">loc</tspan><tspan class="m"> ..... </tspan>'
                      f'<tspan class="v">{loc["net"]:,}</tspan><tspan class="m"> (</tspan><tspan fill="{p["green"]}">{loc["add"]:,}++</tspan>'
                      f'<tspan class="m">, </tspan><tspan fill="{p["red"]}">{loc["del"]:,}--</tspan><tspan class="m">)</tspan>'),
        _text(PAD, y + LINE, f'<tspan class="m">  </tspan><tspan class="k">repos</tspan><tspan class="m"> ... </tspan>'
                             f'<tspan class="v">{data["repos"]}</tspan><tspan class="m"> · contributed </tspan><tspan class="v">{data["contrib_repos"]}</tspan>'),
    ]


def render(data: dict, palette: dict, portrait: dict) -> str:
    p = palette
    out = [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'font-family="ConsolasFallback, Consolas, &quot;JetBrains Mono&quot;, Menlo, monospace" font-size="{FONT}px" fill="{p["fg"]}">',
        f"<style>{FONT_FACE}\n.k{{fill:{p['key']}}} .v{{fill:{p['value']}}} .m{{fill:{p['muted']}}} .a{{fill:{p['accent']}}} "
        f"text,tspan{{white-space:pre}}</style>",
        f'<defs><clipPath id="portrait-clip"><rect x="0" y="{TITLE_H + 24}" width="{LEFT_W}" height="{H - STATUS_H - TITLE_H - 24 - 3 * LINE}"/></clipPath></defs>',
        f'<rect width="{W}" height="{H}" rx="8" fill="{p["bg"]}"/>',
        f'<rect x="0" y="0" width="{W}" height="{TITLE_H}" rx="8" fill="{p["pane"]}"/>',
        f'<rect x="0" y="{TITLE_H - 8}" width="{W}" height="8" fill="{p["pane"]}"/>',
        '<circle cx="16" cy="16" r="5" fill="#ff5f57"/><circle cx="32" cy="16" r="5" fill="#febc2e"/><circle cx="48" cy="16" r="5" fill="#28c840"/>',
        _text(W // 2, 20, f'ravi@{esc(data["login"])}: ~ — tmux', cls="m", extra=' text-anchor="middle"'),
        f'<g stroke="{p["border"]}" stroke-width="1"><line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}"/>'
        f'<line x1="{LEFT_W}" y1="{TITLE_H}" x2="{LEFT_W}" y2="{H - STATUS_H}"/>'
        f'<line x1="{LEFT_W}" y1="{SPLIT_Y}" x2="{W}" y2="{SPLIT_Y}"/></g>',
    ]
    portrait_parts, portrait_bottom = _portrait_pane(portrait, p)
    out += portrait_parts
    out += _left_footer(data, p, portrait_bottom)
    out += _neofetch_pane(data, p)
    out += _htop_pane(data, p)
    out += _status_bar(data, p)
    out.append("</svg>")
    return "\n".join(out) + "\n"
