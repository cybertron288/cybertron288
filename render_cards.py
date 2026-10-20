"""Pure renderers for the README section under the hero: four project cards + a stack/activity strip.

No network, no files. `today.py` feeds real numbers; tests feed fixtures. Palettes come from render_tmux.
Each card is its own SVG so the README can wrap each in a link.
"""
import datetime
import math

from render_tmux import FONT_FACE, esc

PAD = 18
FONT = 11.5
CHAR = FONT * 0.6          # monospace advance at FONT px
SMALL = 10.5
CHAR_S = SMALL * 0.6

CARD_W, CARD_H = 440, 190
STRIP_W = 900
BAR_H = 64
FONT_STACK = 'ConsolasFallback, Consolas, &quot;JetBrains Mono&quot;, Menlo, monospace'

PROJECTS = {
    "zango-packages": {
        "name": "zango packages",
        "sub": "npm · @zango-core",
        "desc": ["React + TypeScript packages for the Zango framework.",
                 "Top committer on 9 @zango-core npm packages."],
        "flow": ["crud", "appbuilder", "components", "create-zango-app"],
        "hl": 0,
        "meta": "rjsf · tanstack · vite · vitest · playwright · storybook",
        "status": "9 packages · 44 releases",
    },
    "igris": {
        "name": "igris",
        "sub": "igrisecurity.com",
        "desc": ["Governance layer for AI agents: policy engine,",
                 "audit trail and access control on LLM + MCP calls."],
        "flow": ["agent", "policy ✓ / ✗", "LLM · MCP", "audit log"],
        "hl": 1,
        "meta": "policy engine · audit trail · MCP access",
        "status": "● building",
    },
    "nova-memory": {
        "name": "nova-memory",
        "sub": "cybertron288/nova-memory",
        "desc": ["Encrypted on-device memory for macOS, served",
                 "to any LLM client over MCP. Finds open loops."],
        "flow": ["capture", "encrypt", "on-device store", "LLM · MCP"],
        "hl": 1,
        "meta": "typescript · mcp · stays on the device",
        "repo": "cybertron288/nova-memory",
    },
    "contrib-matrix": {
        "name": "contrib-matrix",
        "sub": "cybertron288/contrib-matrix",
        "desc": ["GitHub contribution heatmap on a 16×8 WS2812B",
                 "LED matrix on the desk, driven by WLED."],
        "flow": ["github api", "heatmap", "WLED", "16×8 leds"],
        "hl": 2,
        "meta": "typescript · hardware · ws2812b",
        "repo": "cybertron288/contrib-matrix",
    },
}

STACK = [
    ("FE", ["react", "next.js", "typescript", "tailwind", "three.js", "redux"]),
    ("BE", ["django", "python", "node", "express"]),
    ("INFRA", ["postgres", "docker", "git", "vite", "bun"]),
    ("MOBILE", ["react-native", "expo"]),
    ("DESIGN", ["figma"]),
]


def _svg_open(w, h, p):
    return [
        "<?xml version='1.0' encoding='UTF-8'?>",
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT_STACK}" font-size="{FONT}px" fill="{p["fg"]}">',
        f"<style>{FONT_FACE}\ntext,tspan{{white-space:pre}}</style>",
    ]


def card_lines(key, data):
    """Every body-font line a card draws (used by tests to check fit)."""
    proj = PROJECTS[key]
    return proj["desc"] + [proj["meta"]]


def _corner(key, data, p):
    """(text, fill, pulse) for the top-right badge: live stars for repo-backed cards, a status word otherwise."""
    proj = PROJECTS[key]
    if "repo" in proj:
        r = (data.get("cards") or {}).get(key)
        if not r:
            return "open source", p["muted"], False
        return f'★ {r["stars"]:,}  ⑂ {r["forks"]:,}', p["yellow"], False
    status = proj.get("status", "")
    if status.startswith("●"):
        return status, p["green"], True
    return status, p["muted"], False


def render_card(key, data, palette):
    p, proj = palette, PROJECTS[key]
    out = _svg_open(CARD_W, CARD_H, p)
    out.append(f'<rect x="0.5" y="0.5" width="{CARD_W - 1}" height="{CARD_H - 1}" rx="10" fill="{p["pane"]}" stroke="{p["border"]}"/>')

    title_w = len(proj["name"]) * 18 * 0.6
    out.append(f'<text x="{PAD}" y="40" font-size="18px" font-weight="bold">{esc(proj["name"])}</text>')
    out.append(f'<text x="{PAD + title_w + 10:.1f}" y="40" font-size="{SMALL}px" fill="{p["muted"]}">{esc(proj["sub"])}</text>')

    text, fill, pulse = _corner(key, data, p)
    anim = '<animate attributeName="opacity" values="1;.35;1" dur="2s" repeatCount="indefinite"/>' if pulse else ""
    out.append(f'<text x="{CARD_W - PAD}" y="38" font-size="{SMALL}px" text-anchor="end" fill="{fill}">{esc(text)}{anim}</text>')

    for i, line in enumerate(proj["desc"]):
        out.append(f'<text x="{PAD}" y="{68 + i * 18}">{esc(line)}</text>')

    x, y, bh = PAD, 104, 24
    for i, label in enumerate(proj["flow"]):
        w = len(label) * CHAR_S + 14
        hl = i == proj["hl"]
        stroke = p["accent"] if hl else p["border"]
        pulse_box = '<animate attributeName="stroke-opacity" values="1;.35;1" dur="2.4s" repeatCount="indefinite"/>' if hl else ""
        out.append(f'<rect class="flow-box" x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bh}" rx="5" fill="{p["bg"]}" stroke="{stroke}">{pulse_box}</rect>')
        out.append(f'<text x="{x + 7:.1f}" y="{y + 16}" font-size="{SMALL}px"' + (f' fill="{p["accent"]}"' if hl else "") + f'>{esc(label)}</text>')
        x += w
        if i < len(proj["flow"]) - 1:
            out.append(f'<text x="{x + 11:.1f}" y="{y + 16}" font-size="{SMALL}px" text-anchor="middle" fill="{p["muted"]}">→</text>')
            x += 22

    out.append(f'<line x1="{PAD}" y1="146" x2="{CARD_W - PAD}" y2="146" stroke="{p["border"]}"/>')
    out.append(f'<text x="{PAD}" y="170" fill="{p["muted"]}">{esc(proj["meta"])}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def _month(iso):
    return datetime.datetime.strptime(iso, "%Y-%m-%d").strftime("%b ’%y")


def render_activity(data, palette):
    """Stack tokens (wrapped rows) above weekly contribution bars with an axis caption."""
    p = palette
    body = []
    x, y, th = PAD, 8, 22
    for group, tokens in STACK:
        gw = len(group) * CHAR_S * 1.15 + 10
        if x + gw + len(tokens[0]) * CHAR + 16 > STRIP_W - PAD:
            x, y = PAD, y + th + 8
        body.append(f'<text x="{x:.1f}" y="{y + 15}" font-size="9.5px" letter-spacing="1.2" fill="{p["muted"]}">{esc(group)}</text>')
        x += gw
        for tok in tokens:
            w = len(tok) * CHAR + 16
            if x + w > STRIP_W - PAD:
                x, y = PAD, y + th + 8
            body.append(f'<rect class="tok" x="{x:.1f}" y="{y}" width="{w:.1f}" height="{th}" rx="5" fill="none" stroke="{p["border"]}"/>')
            body.append(f'<text x="{x + 8:.1f}" y="{y + 15}">{esc(tok)}</text>')
            x += w + 6
        x += 8
    bottom = y + th

    act = data.get("activity")
    if act and act.get("weekly"):
        weekly = act["weekly"]
        peak = max(weekly) or 1
        top = bottom + 26
        base = top + BAR_H
        n, gap = len(weekly), 3
        bw = (STRIP_W - 2 * PAD - gap * (n - 1)) / n
        for i, v in enumerate(weekly):
            h = max(2.0, round(BAR_H * math.sqrt(v / peak), 1))
            bx = PAD + i * (bw + gap)
            begin = f"{i * 0.012:.3f}s"
            body.append(
                f'<rect class="week" x="{bx:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h}" rx="1" fill="{p["accent"]}" fill-opacity="0.85">'
                f'<animate attributeName="height" from="0" to="{h}" dur="0.9s" begin="{begin}" fill="freeze"/>'
                f'<animate attributeName="y" from="{base}" to="{base - h:.1f}" dur="0.9s" begin="{begin}" fill="freeze"/></rect>')
        ay = base + 18
        body.append(f'<text x="{PAD}" y="{ay}" font-size="{SMALL}px" fill="{p["muted"]}">{esc(_month(act["start"]))}</text>')
        body.append(f'<text x="{STRIP_W / 2:.0f}" y="{ay}" font-size="{SMALL}px" text-anchor="middle" fill="{p["muted"]}">'
                    f'<tspan fill="{p["fg"]}">{act["total"]:,}</tspan> contributions · weekly, last 12 months</text>')
        body.append(f'<text x="{STRIP_W - PAD}" y="{ay}" font-size="{SMALL}px" text-anchor="end" fill="{p["muted"]}">{esc(_month(act["end"]))}</text>')
        bottom = ay + 4

    h = int(bottom + 8)
    return "\n".join(_svg_open(STRIP_W, h, p) + body + ["</svg>"]) + "\n"
