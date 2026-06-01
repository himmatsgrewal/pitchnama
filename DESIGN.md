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
| **Contrast colour** | GOLD — `#e0a92e` (warm amber-gold; chosen by eyeball test on dark) |
| **Colour meaning** | Green vs Gold = batter vs bowler in all head-to-head visuals |
| **Landing page** | Bright WHITE base · GREEN header bar (brand identity, "real cricket site" feel) · green/gold accents · headline "Every matchup, decoded." · two-player input (batter green / bowler gold) + format selector · stat line (4.4M deliveries · 9,366 matches · 7 competitions). Light landing → dark floodlit analysis arc preserved. |
| **Analysis screen** | Dark / floodlit · vivid green + gold data glowing on near-black · big broadcast-style numbers |

### The "floodlit transition"
The signature moment: landing is light and inviting (not intimidating to newcomers);
when the user hits **Analyse**, the screen transitions smoothly to dark — like a
day match becoming a night match under floodlights. The contrast between the
welcoming light landing and the dramatic dark analysis is the core experience.

### Colour hexes (chosen via on-screen eyeball test)
- **Green (batter):** `#2ecc71` — vivid pitch green, pops on dark
- **Gold (bowler):** `#e0a92e` — warm amber-gold (rejected `#f5c518` as too
  "warning-yellow"; this is richer/premium while still legible on near-black)
- **Background (floodlit dark):** `#0d1117` near-black; card surfaces `#141b24`
- These are starting values confirmed in a mockup; fine-tune live during build if needed.

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

## 4. The "Upper Hand" Feature (DESIGNED — flagship)

**Measures (equally weighted):**
- **Scoring axis** — how far the batter's strike rate & average diverge from their
  own baseline (same scope) in this matchup.
- **Dismissal axis** — matchup balls-per-dismissal vs the batter's baseline
  balls-per-dismissal.
- All relative to the batter's OWN baseline (the credible, analyst-correct approach).

**Visual:** a TILT METER — needle leans toward GREEN (batter) or GOLD (bowler).
Below it, a short "why" line, e.g. *"Bowler edge — strike rate down 22%,
dismissed every 18 balls."*

**Honesty rules (non-negotiable for credibility):**
- Under ~30 balls → needle shown FAINT + "small sample" label. Never a confident
  verdict on thin data.
- "Never dismissed" → handled cleanly (no divide-by-zero; counts as batter edge on
  the dismissal axis).
- Most meaningful within a single format; same-scope baseline handles this.

**Why it's the signature:** the needle is exciting (instant "who's winning" for
newcomers); the "why" makes it credible (real reasoning, not fake precision).
Fun + authority in one feature.

**Data source (Stage 1):** the `/compare` API endpoint already returns the
matchup-vs-baseline numbers (scoring + dismissal axes, per format) this meter
reads. `matchup_avg: null` from the engine means "never dismissed" — handle as
the batter-edge case above, never a crash.

### 4a-i. Tilt formula — DRAFT (not yet calibrated)

Core principle confirmed with Himmat: **the needle's tilt must match how one-sided
the contest actually is.** Big domination → big tilt; slight edge → slight tilt.
A glance at the angle should *feel* true before any number is read. Output is a
single needle value from −100 (full gold / bowler) to +100 (full green / batter),
0 = even.

Two axes, equally weighted, both vs the batter's OWN baseline (same scope):

- **Scoring axis = strike rate only.** `(matchup_sr / baseline_sr − 1) × 100`.
  DECISION: use SR only, NOT average — average folds dismissals into it and would
  double-count with the dismissal axis. SR-only keeps the axes clean and honest.
- **Dismissal axis = balls per dismissal.**
  `(matchup_bpd / baseline_bpd − 1) × 100`, where bpd = balls / dismissals.
  Batter survives longer than baseline → positive (batter edge); gets out more
  often → negative (bowler edge). "Never dismissed" (0 outs) → bpd is infinite →
  cap at max positive (strong batter edge), never divide by zero.

Raw needle = mean of the two axes. BUT raw % is lopsided (SR can fall 100% but rise
past 100%), so the raw value must be **shaped** before display so tilt matches
intuition (≈10% = slight, ≈80% = lopsided). Shaping approach NOT yet chosen —
options on the table: (A) cap-and-scale, (B) smooth curve / sigmoid [Claude's lean],
(C) calibrate against known pairs [do regardless, as validation].

**Worked example — RG Sharma vs PJ Cummins, all formats (verified data):**
- Scoring: matchup SR 77.07 / baseline SR 94.23 = 0.818 → −18.2
- Dismissal: matchup bpd 532/15 = 35.5 / baseline bpd 28686/684 = 41.9 = 0.847 → −15.3
- Raw needle ≈ −16.75 → modest GOLD (bowler) edge.
- "Why" line: *"Bowler edge — strike rate down 18%, dismissed every 36 balls vs his usual 42."*
- Sanity check: a modest-but-clear Cummins edge matches cricket reality. ✅

**NEXT for this feature:** pick the shaping approach (A/B/C) and CALIBRATE against
~5–6 known pairs (a known domination, a known even contest, a known slight edge)
until the needle agrees with cricket reality in all of them. Only then lock the
formula. This is a dedicated session, not a quick add-on.

### 4a-ii. Tilt meter — look & motion (CONFIRMED via concept mockup)

Concept confirmed by Himmat against a live mockup — "yes EXACTLY this." Target:
- Semicircular gauge: GREEN (batter) left half, GOLD (bowler) right half, needle
  from centre pivot. Straight up = even; lean = edge; lean amount = one-sidedness.
- **THE RULE (Himmat's words):** the needle leans TOWARD WHOEVER HAS THE ADVANTAGE.
  Batter on top → leans to the batter's (green/left) side. Bowler on top → leans to
  the bowler's (gold/right) side. Amount of lean = size of the advantage. The
  needle direction and the verdict ("why" line) MUST ALWAYS AGREE — sanity-check
  every render: if the text says "bowler edge," the needle must point at the bowler.
  (Caught in mockup: a draw had "bowler edge" text but the needle leaning at the
  batter — wrong. Always verify needle vs verdict.)
- On the floodlit DARK screen (`#0d1117`): green + gold GLOW on near-black.
- **Needle ANIMATES:** sweeps from centre, slight overshoot, then settles at its
  angle (broadcast "powering up" feel). Verdict + headline numbers fade in after
  the needle lands.
- Below needle: verdict line (e.g. "Bowler edge · modest") + the "why" line.
- Below that: headline numbers (avg · SR · dismissals · etc).
- Build PLAIN + correct first, THEN add glow/animation (function before polish).
- Will be data-driven from `/compare` (redraws for any matchup), not hardcoded.

## 4b. Analysis-Screen Layout (DESIGNED)

The dark / floodlit screen, top to bottom:
1. **Matchup title** (e.g. "Kohli vs Cummins")
2. **Tilt meter (HERO — always visible)** — needle green↔gold + the "why" line
3. **Headline numbers (always visible)** — balls · runs · avg · SR · matches
4. **Tabs (for depth):** Charts · Phases · Report (bilingual EN+Hindi)
5. **Action button:** Generate Card

Reasoning: hero (meter + key numbers) is always visible so newcomers can't miss
the signature; deeper detail lives in tabs so it doesn't overwhelm. Single
cinematic story continues from the floodlit reveal into the hero.

## 4c. Shareable Card (DESIGNED — last design piece)

The "Generate shareable card" output — a branded image for Instagram/WhatsApp.

**Approach: "rich" (option A)** — shows depth, signals serious analytics.
- **Hero (top):** matchup title (batter green / bowler gold) + the tilt meter +
  verdict ("Bowler edge · strong")
- **Below:** a clean, well-spaced stat grid (balls, avg, SR, outs, matches, SR-drop)
- **Branding:** "PitchNama" wordmark (gold "Nama") top; footer
  "pitchnama.com · the chronicle of every contest"
- **Colours:** dark/floodlit background, green+gold, matches the analysis screen
- **NO player photos** — data graphics + branding only

**Build note:** rich must read as *authoritative/premium*, NOT cluttered. Keep the
hero clearly dominant, generous spacing in the stat grid. Watch busyness.

**Sizes:** build SQUARE (1:1, Instagram feed) first and perfect it; then add a
PORTRAIT (4:5 / 9:16 story-reel) version of the same design.

(Stage 0 design COMPLETE. Stage 1 FastAPI wrapper COMPLETE — see §5. Tilt-meter
concept + look/motion confirmed; formula drafted, calibration pending — see §4a.
Next: Stage 2 — front-end fundamentals + Node.js.)

## 5. The Build Path — "Path B" (custom web front-end)

**Decision:** replace the Streamlit front-end with a custom cinematic web app
(HTML/CSS/JS, likely React). **The Python engine stays 100% untouched** — it gets
wrapped in a FastAPI layer so the new site can call it. Himmat is learning
front-end as part of this (by choice — it's part of the goal).

Streamlit was rejected for the final product because it can't deliver the cinematic
vision, and polishing it would be throwaway work.

| Stage | What | Notes |
|---|---|---|
| 0 | Design decisions | ✅ DONE — brand, colours, tilt meter, layout, cards all locked |
| 1 | FastAPI wrapper around engine | ✅ DONE — `api.py` at repo root; endpoints `/matchup`, `/baseline`, `/compare` return JSON; verified vs known-good; committed |
| 2 | Front-end fundamentals + install Node.js | ◀ NEXT — the real learning curve |
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
  Known-good: 532 balls all-formats / 46 IPL / 225 Test / 15 dismissals all-formats.
- Licensing: code MIT; data credits Cricsheet (CC BY-SA 4.0) + cricketdata (GPL-3).

---

## 8. What's Already Done

**The engine (COMPLETE, do not rebuild):**
4.4M+ deliveries · 9,366 matches · 7 competitions · 3 formats (Cricsheet).
Modular Python package (cache, matchup, scout_report, players, charts, data_loader).
Format-aware phases (T20 / ODI / Test ball-age). Bilingual EN+Hindi reports.
Full player names + countries (cricketdata player_meta, joined on cricsheet_id) +
~374 curated overrides + multi-field search. Dismissal logic fixed (bowler-credited
only; run-outs excluded). Plotly matchup-vs-baseline chart. Live on Streamlit Cloud.
Working GitHub Actions daily auto-update. pitchnama.com owned (URL-forwarding for now).

**Stage 1 — the API bridge (COMPLETE):**
`api.py` at repo root wraps the untouched engine in FastAPI. Three endpoints, all
returning JSON, all verified against known-good and committed to GitHub:
- `/matchup?batter=&bowler=` → head-to-head (calls `analyze_matchup`)
- `/baseline?batter=` → batter's own baseline (calls `analyze_batter_overall`)
- `/compare?batter=&bowler=` → matchup vs baseline, feeds the tilt meter (calls `compare_matchup_to_baseline`)
Web layer uses `match_format` param → passed to engine's `format` (avoids the
Python `format` builtin clash). Run locally: `python -m uvicorn api:app --reload`.