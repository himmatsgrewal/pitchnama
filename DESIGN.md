# PitchNama — Design Constitution

> This file is the permanent record of PitchNama's brand, design, and build plan.
> It exists so that decisions survive across work sessions and are never lost.
> If resuming work in a new session: **read this file first.**

**Tagline:** *The chronicle of every contest.*

---

## 1. What PitchNama Is

Open-source cricket **matchup** analytics — for a given batter vs a given bowler,
it tells the story of that contest: head-to-head stats, format-aware phase splits,
who holds the edge, and a bilingual scout report. The name = *pitch* + *nama*
(chronicle, as in Akbarnama). It chronicles contests.

**Goal:** exciting and genuinely fun even for people with ZERO cricket knowledge,
while being credible enough to impress professional cricket-data employers
(SportsMechanics / CricViz / BCCI / IPL).

---

## 2. Brand & Visual Identity (LOCKED)

| Element | Decision |
|---|---|
| **Tagline** | "The chronicle of every contest" |
| **Vibe** | Broadcast sports energy (Star/Sky TV) + chronicle authority underneath |
| **Emotional arc** | LIGHT, welcoming landing page → smooth transition → DARK "floodlit stadium" analysis screen |
| **Primary colour** | Vivid pitch GREEN (locked) |
| **Contrast colour** | Bright GOLD (locked as concept; exact hex = TBD, see below) |
| **Colour meaning** | Green vs Gold = batter vs bowler in all head-to-head visuals |
| **Landing page** | Full-screen hero · stylised/illustrated pitch background (NOT a photo) · huge name + logo · input (2 players + format) front-and-centre |
| **Analysis screen** | Dark / floodlit · vivid green + gold data glowing on near-black · big broadcast-style numbers |

### The "floodlit transition"
The signature moment: landing is light and inviting (not intimidating to newcomers);
when the user hits **Analyse**, the screen transitions smoothly to dark — like a
day match becoming a night match under floodlights. The contrast between the
welcoming light landing and the dramatic dark analysis is the core experience.

### Gold — open spec (NOT yet locked to a hex)
Gold is the hardest colour to get right; a gold that looks rich in theory can turn
muddy/mustard on near-black. **Do not lock a gold hex from memory.** Requirement:
a *bright, legible* gold that pops on the dark analysis background, used for the
bowler side of head-to-head visuals. **Decide the exact hex by eyeballing it
rendered on the real dark screen** during the build — not in this file.

### Hard rule — NO photos
No player photos and no copyrighted/stadium photos ANYWHERE (site, charts, cards,
Instagram). Reasons: copyright risk + it signals data-ethics awareness to employers.
All visuals = original brand graphics + data. The illustrated pitch background is
brand-owned art, not a stock/real photo.

---

## 3. Full Feature Vision (the AIM — every item must ship)

- Exciting / appealing / FUN for total newcomers
- Smooth light→dark colour transition on "Analyse"
- LIVE / ANIMATED graphs in bright colours
- Charts: matchup-vs-baseline · phase breakdowns (per format) · per-format comparison
- **FLAGSHIP: "Who has the upper hand"** gauge / dominance visual
  (MUST be methodologically sound — a real dominance score, not fake-precise)
- Bilingual scout report (English + Hindi) — already built
- Buttons including "Generate shareable card"
- Shareable cards = branded DATA-GRAPHICS (no photos) for Instagram (@pitchnama reserved)

---

## 4. Open Design Questions (still to decide)

1. **The "upper hand" feature** — (a) methodology: what does the % / score actually
   measure? (likely a blend of how far the batter's avg & strike rate diverge from
   their baseline, with sample-size honesty). (b) visual: gauge? meter? bar?
2. **Analysis-screen layout** — after it goes dark, what does the user see
   first / second / third? (headline numbers → gauge → charts → report?)
3. **Shareable card design** — layout, what data it shows, branding.

---

## 5. The Build Path — "Path B" (custom web front-end)

**Decision:** replace the Streamlit front-end with a custom cinematic web app
(HTML/CSS/JS, likely React). **The Python engine stays 100% untouched** — it gets
wrapped in a FastAPI layer so the new site can call it. Himmat is learning
front-end as part of this (by choice — it's part of the goal).

Streamlit was rejected for the final product because it can't deliver the cinematic
vision, and polishing it would be throwaway work.

| Stage | What | Notes |
|---|---|---|
| 0 | Design decisions | Mostly done; finish gauge + layout + cards |
| 1 | FastAPI wrapper around engine | Python — comfortable ground |
| 2 | Front-end fundamentals + install Node.js | The real learning curve |
| 3 | Build the site | Landing, transition, analysis screen, charts, gauge, cards |
| 4 | Deploy + clean hosting + Instagram prep | The ~$5/mo hosting moment |

**Estimate:** ~8–12 weeks of near-daily 2–3 hr sessions to full completion.

---

## 6. Standing Duties (must be flagged proactively)

1. **Clean hosting trigger** — when Himmat is about to put pitchnama.com on his
   CV, send it to a recruiter, or launch Instagram / share widely → STOP and set up
   clean ~$5/month hosting (no-sleep, clean URL, real custom domain). Streamlit free
   tier sleeps ("Zzzz") and can't do clean custom domains. Flag all costs BEFORE
   they happen.
2. **Write decisions down** — keep this file and the repo updated so nothing is lost
   across sessions.
3. **Fresh-chat handoff** — when a chat gets slow/large, write a full handoff message.
4. **README is stale** — update it during a dedicated README pass (old tagline,
   wrong match count, T20-only phases, "scout reports in development", "Streamlit
   planned"). Don't put repo link on CV until done.

---

## 7. Working Habits & Reference

- Start each session with `git pull` (daily auto-update robot pushes data).
- Spoon-fed steps: COMPLETE files to paste, one edit at a time, confirm before big changes.
- Direct, honest collaboration; push back on bad ideas; MCQ-style choices when deciding.
- Verify cricket facts against data, not memory. Verify numbers before committing.
- Lowercase/snake_case Python, type hints, imperative commits, DRY. Delete scratch files before commit.
- **Test pair:** Rohit Sharma (RG Sharma) vs Pat Cummins (PJ Cummins).
  Known-good: 532 balls all-formats / 46 IPL / 225 Test.
- Licensing: code MIT; data credits Cricsheet (CC BY-SA 4.0) + cricketdata (GPL-3).

---

## 8. What's Already Done (the engine — COMPLETE, do not rebuild)

4.4M+ deliveries · 9,366 matches · 7 competitions · 3 formats (Cricsheet).
Modular Python package (cache, matchup, scout_report, players, charts, data_loader).
Format-aware phases (T20 / ODI / Test ball-age). Bilingual EN+Hindi reports.
Full player names + countries (cricketdata player_meta, joined on cricsheet_id) +
~374 curated overrides + multi-field search. Dismissal logic fixed (bowler-credited
only; run-outs excluded). Plotly matchup-vs-baseline chart. Live on Streamlit Cloud.
Working GitHub Actions daily auto-update. pitchnama.com owned (URL-forwarding for now).