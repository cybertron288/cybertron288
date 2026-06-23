# GitHub Profile README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the old GitHub profile README with the approved minimal, ambitious design.

**Architecture:** Single file replacement — `README.md` at repo root. No dependencies, no build step. Branch off main, update file, commit, push, open PR.

**Tech Stack:** Git, Markdown, GitHub profile README (cybertron288/cybertron288 repo)

## Global Constraints

- NEVER commit to main — work on `feat/update-profile-readme`
- No co-author signatures in commit messages
- Exact content from spec — do not improvise or add anything

---

### Task 1: Create feature branch and update README

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: approved design from `docs/superpowers/specs/2026-06-23-github-profile-readme-design.md`
- Produces: updated `README.md` on `feat/update-profile-readme`

- [ ] **Step 1: Create feature branch**

```bash
git checkout -b feat/update-profile-readme
```

Expected: `Switched to a new branch 'feat/update-profile-readme'`

- [ ] **Step 2: Replace README.md with approved content**

Write the following exact content to `README.md`:

```markdown
# Ravi Patel

> Building software that ships at scale — from framework internals to AI governance infrastructure.

SDE-2 at **Healthlane Technologies** · Core contributor to [Zango](https://github.com/Healthlane-Technologies/Zango), an open-source Django framework powering enterprise healthcare apps across pharma giants like AstraZeneca, Pfizer, BMS, Roche, and MSD.

Outside work: building **[Igris](https://igrisecurity.com/)** — a governance layer for AI agents: policy engine, audit trail, and access control across LLM and MCP calls.

---

## Stack

**Frontend** · React · TypeScript · Next.js · Tailwind · GSAP · Three.js · Redux  
**Backend** · Node.js · Hono · Express · Django/Zango  
**Data** · PostgreSQL · Drizzle  
**Mobile** · React Native · Expo  
**Tooling** · Bun · Vite · Docker · Git · Figma

---

## Find Me

[![LinkedIn](https://img.shields.io/badge/LinkedIn-0077B5?style=flat-square&logo=linkedin&logoColor=white)](https://www.linkedin.com/in/ravipatel8407/)
[![Email](https://img.shields.io/badge/Gmail-D14836?style=flat-square&logo=gmail&logoColor=white)](mailto:ravipatel288.jobs@gmail.com)
[![Igris](https://img.shields.io/badge/Igris-000000?style=flat-square)](https://igrisecurity.com/)

---

![Top Languages](https://github-readme-stats.vercel.app/api/top-langs/?username=cybertron288&layout=compact&langs_count=8&bg_color=0D1117&text_color=ffffff&title_color=9370db&hide_border=true)

![GitHub Streak](https://streak-stats.demolab.com?user=cybertron288&theme=dark&hide_border=true&background=0D1117&ring=9370db&fire=9370db&currStreakLabel=9370db)
```

- [ ] **Step 3: Verify diff looks correct**

```bash
git diff README.md
```

Expected: old bio/badges removed, new content in place.

- [ ] **Step 4: Stage and commit**

```bash
git add README.md docs/superpowers/specs/2026-06-23-github-profile-readme-design.md docs/superpowers/plans/2026-06-23-github-profile-readme.md
git commit -m "feat: update GitHub profile README with professional redesign"
```

- [ ] **Step 5: Push branch**

```bash
git push -u origin feat/update-profile-readme
```

- [ ] **Step 6: Open PR**

```bash
gh pr create --title "Update GitHub profile README" --body "$(cat <<'EOF'
## Summary
- Replace old emoji-heavy bio with minimal, professional profile
- Manifesto header with Igris callout as primary CTA
- Clean stack section and Find Me links
- GitHub stats: top languages + streak (dark/purple theme)

## Test plan
- [ ] Visit https://github.com/cybertron288 after merge — profile renders correctly
- [ ] Igris link resolves to https://igrisecurity.com/
- [ ] Zango link resolves to correct GitHub repo
- [ ] LinkedIn + email badges render
- [ ] Stats cards load (may take a few seconds)
EOF
)"
```
