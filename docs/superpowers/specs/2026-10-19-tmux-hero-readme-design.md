# Profile README — "tmux Session" hero

**Date:** 2026-10-19
**Status:** Approved (direction B picked from mockups: https://claude.ai/artifact/6nSQS6ihs2tJJXthfykpJm)
**Branch:** feat/update-profile-readme

## Intent

Replace the current README top (typing header + neofetch card + stats widgets) with one
self-generated hero SVG that looks like a real tmux window: ASCII portrait pane, neofetch
pane, htop-style language pane with a live git log and an animated typing prompt, and a
tmux status bar carrying real GitHub numbers. Regenerated daily by the existing
`today.py` pipeline. Dark and light variants.

Why: research of standout profiles (Sharann-del, galaxy-profile, Andrew6rant,
MahyudeenShahid) shows the ones people remember generate their own SVG panels and commit
to one metaphor. Stock github-readme-stats cards now read as the default. The terminal
metaphor fits "framework internals → AI governance" and reuses what already exists.

## Goals

- One hero SVG, 900×~540px, `<picture>` dark/light, renders natively in GitHub README.
- Every number in it is real and refreshed daily (commits, stars, followers, LOC, repo count,
  account uptime, top languages, last commits).
- Looks like tmux: three panes, box-drawing borders, pane titles, status bar with window
  tabs, prompt with blinking cursor, typing animation (SMIL, which GitHub renders).
- Keep what the user explicitly added: skillicons stack rows, contribution snake, find-me
  badges, WakaTime section.

## Non-goals / anti-goals

- No third-party stat widgets (github-readme-stats, streak-stats, trophies, visitor counter).
  They are the "2026 default" and contradict the custom-SVG direction.
- No typing-svg header (the hero's prompt replaces it).
- No DOB-based "uptime"; use GitHub account age (honest, no placeholder).
- No badge wall. Three find-me badges max.
- No external fonts or images inside the SVG (GitHub proxies SVG; externals are stripped).

## Layout (design width 900)

```
┌ ravi@cybertron288: ~ — tmux ───────────────────────────────────── 900×540 ┐
│ 0:portrait            │ 1:neofetch                                        │
│  <color ASCII         │  ravi@cybertron288 ──────────────                 │
│   portrait,           │  Role ....... SDE-2 · Healthlane Technologies     │
│   ~48 cols × 30 rows> │  Core ....... Zango — Django framework (AZ…MSD)   │
│                       │  Building ... Igris — governance for AI agents    │
│                       │  Uptime ..... N years, N months, N days (on GitHub)│
│                       │  Langs ...... Python, TypeScript, JavaScript      │
│                       │  Web ........ React, Next.js, Django, Node.js     │
│                       │  Human ...... English, Hindi, Gujarati            │
│                       │  Contact .... email · in/ravipatel8407 · igris    │
│                       ├───────────────────────────────────────────────────┤
│                       │ 2:htop — languages · all public repos             │
│                       │  Python     [██████████░░░░░░░░░░]  46%           │
│                       │  TypeScript [██████░░░░░░░░░░░░░░]  31%  (×4 bars)│
│                       │  a1f3c2e feat(igris): …           · 2d            │
│                       │  7b9e0d1 fix(zango): …            · 5d            │
│                       │  ravi@cybertron288:~$ echo "framework internals → AI governance"▍
├───────────────────────┴───────────────────────────────────────────────────┤
│[cybertron288] 0:portrait 1:neofetch* 2:htop        1,284 commits · 318★ · 2026-10-19│
└───────────────────────────────────────────────────────────────────────────┘
```

Palette, dark (matches current card / GitHub dark): bg `#0d1117`, pane `#161b22`,
border `#30363d`, fg `#e6edf3`, muted `#8b949e`, accent `#9370db`, key `#ffa657`,
value `#a5d6ff`, green `#3fb950`, red `#f85149`, yellow `#d29922`, blue `#58a6ff`.
Light: bg `#ffffff`, pane `#f6f8fa`, border `#d0d7de`, fg `#1f2328`, muted `#656d76`,
accent `#6f42c1`, key `#953800`, value `#0a3069`, green `#1a7f37`, red `#cf222e`,
yellow `#9a6700`, blue `#0969da`. Portrait colors are lifted for dark, darkened for light.

Font stack inside SVG: `ConsolasFallback, Consolas, "JetBrains Mono", Menlo, monospace`
with the existing `@font-face` size-adjust trick from `dark_mode.svg`. 13px body, 11px
portrait glyphs. All text `white-space: pre`.

## Animations (SMIL only; no CSS keyframes needed)

- Typing prompt: command text inside a `<clipPath>` whose rect `width` animates
  `0 → full` over ~2.4s, `begin="0.8s"`, `fill="freeze"`.
- Cursor: `▍` opacity `1;0;1` dur 1s, indefinite.
- htop bars: each filled rect `width` animates `0 → value` over 1.2s, staggered 0.15s,
  `fill="freeze"`.
- Nothing else moves. Respect restraint.

## Data pipeline

Existing `today.py` (Andrew6rant-derived) already computes: account id/createdAt, LOC
add/del/net via cached per-repo walk, commit total, stars, repo count, contrib repos,
followers. Extend it with:

- `uptime` = relativedelta(now, account createdAt) formatted `N years, N months, N days`
  (replaces DOB placeholder).
- `languages` = top 4 by bytes across owned public repos (GraphQL
  `repositories(ownerAffiliations: OWNER, isFork: false) { languages(first: 10, orderBy: {field: SIZE}) { edges { size node { name } } } }`),
  as percentages of the sum.
- `recent_commits` = last 2 commit messages the user authored, from REST
  `GET /users/{login}/events/public` PushEvents (sha7, first line of message, repo,
  relative age). Fall back to empty rows if none.
- Render: `render_tmux.render(data, palette, portrait) -> str` builds the SVG from a
  Python template; `today.py` writes `assets/tmux-dark.svg` and `assets/tmux-light.svg`.
  Keep writing `dark_mode.svg`/`light_mode.svg` untouched? **No** — delete them and the
  neofetch section they served; the tmux hero supersedes. Remove from workflow `git add`.

## Portrait (one-off, committed artifact)

- Source: GitHub avatar `https://github.com/cybertron288.png?size=1024` (460×460; the
  original photo from July is no longer on disk).
- `scripts/portrait.py`: rembg (u2net, model already cached at `~/.u2net`) → alpha crop →
  resize to 48 columns (cell 7×13px at 11px font) → luminance → ramp `" .:-=+*#%@"` →
  per-cell RGB. Output `assets/portrait.json`:
  `{"cols":48,"rows":N,"rows_runs":[[["@@##",  "#aabbcc"], ...], ...]}` with consecutive
  same-color cells merged into runs (same trick as the July SVG: ~65% fewer tspans).
- Runs in a throwaway `uv venv` in the scratchpad; rembg is **not** added to
  `requirements.txt` (CI never regenerates the portrait).
- `render_tmux` turns runs into `<tspan>`s per row, applying the theme color transform.

## README structure after change

1. `<picture>` dark/light → `assets/tmux-dark.svg` / `assets/tmux-light.svg`, `width="100%"`.
2. `### \`whoami\`` — keep the existing text code block + Zango/Igris links (short).
3. `### \`stack\`` — existing skillicons rows, unchanged.
4. WakaTime section markers, unchanged.
5. `### \`contribution snake\`` — unchanged.
6. `### \`find me\`` — three badges (LinkedIn, Gmail, Igris). Drop komarev views counter.

Removed: typing-svg header, neofetch `<picture>` (old card), `### stats` block
(github-readme-stats ×2, streak-stats).

## Workflow changes

`.github/workflows/stats-card.yml`: rename to `hero.yml` (job "Generate tmux hero"),
`git add -A assets/tmux-dark.svg assets/tmux-light.svg cache`, commit message
`chore: refresh tmux hero [skip ci]`. Keep daily cron + manual dispatch + push-to-main.
It needs the `ACCESS_TOKEN` repo secret (fine-grained PAT; see comment atop `today.py`).
Verify the secret exists with `gh secret list`; if absent, say so in the final report —
the user must add it.

## Verification

- Unit tests (pytest, in `tests/`): `render_tmux.render` returns well-formed XML
  (lxml parse), contains the three pane titles, status bar numbers, four language bars with
  widths proportional to percentages, SMIL `<animate>` elements for prompt/cursor/bars,
  and no external `href`s. Portrait run-merging test on a tiny synthetic image.
- `today.py` can be exercised locally with a fixture `data` dict (no network) via
  `python today.py --render-only fixtures/sample.json` → writes SVGs. Add that flag.
- Visual check: open each SVG in Chrome (file://) and screenshot; also render the final
  README branch on GitHub after push for one screenshot in both themes.

## Left to the builder

- Exact pane proportions and glyph metrics (tune so the portrait fills the left pane
  without clipping; aim portrait pane ≈ 330px wide).
- Relative-age formatting for commits (`2d`, `5h`).
- How to abbreviate long commit messages (truncate to pane width with `…`).
