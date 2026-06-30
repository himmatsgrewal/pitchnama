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
| **Contrast colour** | GOLD — two-gold rule (see below) |
| **Colour meaning** | Green vs Gold = batter vs bowler in all head-to-head visuals |
| **Landing page** | Richer-than-white base (`#e9efec`) with green/gold radial glows + a faint green glow rising from the bottom (rejected pure white as too blank; rejected dark as it kills the floodlit reveal) · GREEN header bar (brand identity, "real cricket site" feel) · headline "Every matchup, decoded." · two-player input (batter green / bowler gold, searchable dropdowns) + format selector · Analyse button · quick-try matchup chips (Rohit Sharma vs Pat Cummins · Virat Kohli vs Kagiso Rabada · David Warner vs Stuart Broad) · live stat line (fed by `/stats`) |
| **Analysis screen** | Dark / floodlit (`#0d1117`) · vivid green + gold data glowing on near-black · big broadcast-style numbers · tilt-meter hero · tabs for depth |

### The floodlit transition (BUILT)
The signature moment: landing is light and inviting; on **Analyse**, a full-screen
black overlay fades in (500ms), the view swaps to the analysis screen behind it
while fully opaque, then the overlay fades back out — revealing the dark
floodlit screen. The viewer never sees a hard cut, only a smooth day-to-night.
Same fade on **Back**. The analysis screen then animates its own content in:
title and "why" line rise and fade in, followed by six stat cards staggered at
~70ms each. Broadcast "powering up" feel.

### Colour hexes (chosen via on-screen eyeball test)
- **Green (batter):** `#2ecc71` — vivid pitch green, pops on dark
- **Gold — the TWO-GOLD RULE:** the gold shade changes with the background it sits on.
  - **Bright gold** `#facc15` (Tailwind: `pitch-gold-bright`) — for the "Nama"
    wordmark and gold accents on LIGHT / GREEN backgrounds (e.g. the landing
    header). The warm amber-gold goes muddy on white/green; bright gold stays crisp.
  - **Warm amber-gold** `#e0a92e` (Tailwind: `pitch-gold`) — the bowler colour on
    the DARK floodlit analysis screen. Rejected `#f5c518` as too "warning-yellow";
    this is richer/premium and legible on near-black.
- **Background (floodlit dark):** `#0d1117` near-black; card surfaces `#141b24`
- **Landing base:** `#e9efec` soft off-white (with green/gold radial glows on top)
- **All five live in the Tailwind `@theme`** (`frontend/src/index.css`):
  `pitch-green` `#2ecc71` · `pitch-gold` `#e0a92e` · `pitch-gold-bright` `#facc15` ·
  `floodlit` `#0d1117` · `surface` `#141b24`.

### Hard rule — NO photos
No player photos and no copyrighted/stadium photos ANYWHERE (site, charts, cards,
Instagram). Reasons: copyright risk + it signals data-ethics awareness to employers.
All visuals = original brand graphics + data. The illustrated pitch background is
brand-owned art, not a stock/real photo.

---

## 3. Full Feature Vision (the AIM — every item must ship)

- Exciting / appealing / FUN for total newcomers
- Smooth light→dark colour transition on "Analyse" ✅
- LIVE / ANIMATED graphs in bright colours ✅
- Charts: matchup-vs-baseline ✅ · phase breakdowns (per format) ✅ · per-competition comparison ✅ · pressure cards (dot/boundary) ✅
- **FLAGSHIP: "Who has the upper hand"** gauge / dominance visual ✅ (built with DRAFT formula; calibration pending)
- Bilingual scout report (English + Hindi) ✅ — broadcast pundit voice via `/report`
- Buttons including "Generate shareable card" — DESIGNED, not yet built
- Shareable cards = branded DATA-GRAPHICS (no photos) for Instagram (@pitchnama reserved)
- **Logo (P+N monogram) — END-OF-PROJECT must-do:** a real original graphic logo,
  a P + N monogram. Original art only, no photos. Designed LATE, once the built site
  gives visual context to design against; lives in the header (replacing the current
  text "PitchNama" wordmark). Font pass happens at the same time.

---

## 3a. Post-Launch Vision (the long game)

**The end state, by ~2 years post-launch:** PitchNama is no longer just a matchup
tool. The landing page presents three top-level sections:

- **Men's cricket** — what we're launching with (matchups, stats, scout reports)
- **Women's cricket** — same depth of analytics, applied to women's data
  (Cricsheet has WT20Is, WODIs, WBBL, WPL). Underserved by current analytics tools.
- **Venues** — per-ground analysis: batting-friendly vs bowling-friendly,
  phase behaviour, historical patterns. Data already in the cache (we capture
  `venue` and `city` per delivery).

These are NOT part of v1. They are the roadmap *after* v1 ships and is stable.
Launch announcements should describe PitchNama as matchup analytics — clean, focused,
complete — with Women's and Venues listed as "coming soon" on a public roadmap.
Underpromise, overdeliver.

**Architectural implication for v1:** when we deploy at the $5 hosting moment, the
URL structure and navigation should accommodate adding top-level sections later
without redesigning everything. Small consideration now, big payoff later.

**Long-game positioning:** "I built PitchNama and have been actively developing it
for X months" is a far stronger CV story than a one-shot project. The point isn't
just to ship v1 — it's to ship v1, then keep shipping. Two years of public,
sustained development is what sets a data-science portfolio apart.

---

## 4. The "Upper Hand" Feature (BUILT with DRAFT formula)

**Measures (equally weighted):**
- **Scoring axis** — strike rate vs the batter's own baseline (same scope)
- **Dismissal axis** — matchup balls-per-dismissal vs the batter's baseline bpd
- All relative to the batter's OWN baseline (credible, analyst-correct approach)

**Visual:** a TILT METER — needle leans toward GREEN (batter) or GOLD (bowler).
Below it, a short "why" line, e.g. *"Bowler edge — strike rate down 18%, dismissed
every 35 balls vs his usual 42."*

**Honesty rules (non-negotiable for credibility):**
- Under ~30 balls → needle shown FAINT + "small sample" label. Never a confident
  verdict on thin data.
- "Never dismissed" → handled cleanly (no divide-by-zero; counts as batter edge on
  the dismissal axis).
- Most meaningful within a single format; same-scope baseline handles this.

**Why it's the signature:** the needle is exciting (instant "who's winning" for
newcomers); the "why" makes it credible (real reasoning, not fake precision).

**Data source:** `/compare` returns matchup-vs-baseline numbers per format.
`matchup_avg: null` means "never dismissed" — handle as the batter-edge case.

### 4a-i. Tilt formula — CALIBRATED & LOCKED (24 Jun 2026)

Core principle: **the needle's tilt must match how one-sided the contest actually
is.** Big domination → big tilt; slight edge → slight tilt. A glance at the angle
should *feel* true before any number is read. Output: a single needle value from
−100 (full gold / bowler) to +100 (full green / batter), 0 = even.

**Final calibrated formula:**

- **Scoring axis** = `(matchup_sr / baseline_sr − 1) × 100`. SR-only (not avg).
- **Dismissal axis** = `(matchup_bpd / baseline_bpd − 1) × 100`. Never-dismissed → +100.
- **Format-aware weighting** of the two axes:
  - Tests → 50/50 (survival matters as much as scoring in long-form)
  - T20 / ODI / All formats → 60/40 SR-weighted (limited-overs and aggregate views value scoring more, since most deliveries are limited-overs)
- **Raw needle** = `scoring × scoringWeight + dismissal × dismissalWeight`
- **Shaping** = `100 × tanh(raw / 50)` — sharper curve so genuinely lopsided contests visually look lopsided, not squashed
- **Visual rotation:** `−needle × 0.9` degrees
- **Verdict bands (tightened):**
  - `|needle| < 6` → "Even contest"
  - `< 18` → "slight"
  - `< 45` → "clear"
  - `≥ 45` → "strong"

**Calibration session — 6 known matchups, all agreed with reality:**

| Matchup | Verdict | Note |
|---|---|---|
| Rohit Sharma vs Pat Cummins (all) | Bowler edge · slight | Modest, well-known edge |
| Virat Kohli vs Mitchell Starc (all) | Batter edge · slight | Survival outweighs SR drop |
| David Warner vs Stuart Broad (all) | Bowler edge · clear | Famous bunny — clear by SR |
| AB de Villiers vs Lasith Malinga (all) | Batter edge · strong | Meter committed where gut hedged |
| Steve Smith vs R Ashwin (all) | Batter edge · clear | Meter committed where gut hedged |
| Babar Azam vs Jasprit Bumrah (all) | Bowler edge · slight | Small sample (59 balls) but trusts what's there |

Small-sample threshold kept at **30 balls** — below that, meter dims to 40% and shows "small sample" label. User trusts the user above 30.

### 4a-ii. Tilt meter — look & motion (BUILT + POLISHED)

- Semicircular gauge: GREEN (batter) left half, GOLD (bowler) right half, white
  needle from centre pivot. Straight up = even; lean = edge; lean amount = one-sidedness.
- **THE RULE (Himmat's words):** the needle leans TOWARD WHOEVER HAS THE ADVANTAGE.
  Batter on top → leans to batter's (green/left) side. Bowler on top → leans to
  bowler's (gold/right) side. The needle direction and the verdict ("why" line)
  MUST ALWAYS AGREE — sanity-check every render: if the text says "bowler edge,"
  the needle must point at the bowler.
- **Needle ANIMATES:** sweeps from centre over 1100ms with a cubic-bezier bounce
  (`cubic-bezier(0.34, 1.55, 0.5, 1)`) — slight overshoot, then settles at its angle.
  Verdict + why-line + headline numbers fade in after.
- Below needle: verdict line ("Bowler edge · modest") + the "why" line.
- Below that: headline numbers (avg · SR · dismissals · etc).
- Small-sample state: under 30 balls → the whole meter renders at 40% opacity
  with a "small sample" subtitle.
- - **Glow (SHIPPED):** soft SVG-filter halo on each arc. The **winning side breathes** (animated `feGaussianBlur` stdDeviation 2.5→8→2.5 over 2.6s with spline easing); the losing side stays at static gentle glow; even contests show both sides static. The pulse is *meaningful* not decorative — the meter signals who's alive in the contest.

### 4b. Analysis-Screen Layout (BUILT)

The dark / floodlit screen, top to bottom:
1. **Top bar:** ← Back (left) · PitchNama wordmark (right, warm gold "Nama")
2. **Matchup title** (e.g. "Rohit Sharma vs Pat Cummins") — green + gold names
3. **Tilt meter (HERO — always visible)** — needle green↔gold + verdict + why
4. **Headline numbers (always visible)** — 6 stat cards: Balls · Runs · Avg · SR · Dismissals · Matches
5. **Tabs (for depth):** Charts · Phases · Report
   - **Phases:** ✅ BUILT — one table per format present in the data (T20, ODI, Test)
     with columns Balls/Runs/Avg/SR/Wkts/Dot%
   - **Charts:** ✅ BUILT — four sections: Career baseline vs this matchup, Phase
     strike rate (per format), Pressure cards (dot %, boundary %), Strike rate by
     competition (with career baseline reference line). Uses Recharts. All green/gold.
   - **Report:** ✅ BUILT — bilingual EN+Hindi broadcast pundit narratives via
     `/report`. Named edge in human terms; translates numbers into meaning; surfaces
     one meaningful phase finding (min 10 balls, 25% divergence); calls out format
     splits when avg differs ≥2× across competitions; small-sample caveat below 30 balls.
6. **Action button:** Generate Card (not yet built)

### 4c. Shareable Card (DESIGNED, not yet built)

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

---

## 5. The Build Path — "Path B" (custom web front-end)

**Decision:** replace the Streamlit front-end with a custom cinematic web app
(HTML/CSS/JS + React). **The Python engine stays 100% untouched** — it gets
wrapped in a FastAPI layer the new site calls. Himmat is learning front-end as
part of this (by choice — it's part of the goal).

| Stage | What | Notes |
|---|---|---|
| 0 | Design decisions | ✅ DONE |
| 1 | FastAPI wrapper around engine | ✅ DONE — `api.py` at root; endpoints `/matchup`, `/baseline`, `/compare`, `/players`, `/stats`, `/report` returning JSON; CORS enabled for the Vite dev origin |
| 2 | Front-end fundamentals + build the site | ◀ IN PROGRESS. Landing complete · Analysis screen complete · Tilt meter (draft formula) · Phases tab · Report tab (bilingual EN+Hindi broadcast voice via `/report`) · Charts tab (4 sections: baseline-vs-matchup, phase SR per format, pressure cards, per-competition SR). NEXT: Generate Card button, tilt-meter calibration, tilt-meter glow polish. |
| 3 | (folded into Stage 2) | — |
| 4 | Deploy + clean hosting + Instagram prep | ✅ SHIPPED 29 Jun 2026. Backend at https://pitchnama-api.onrender.com (Render Web Service, Singapore region, currently Standard $25/mo). Frontend at https://pitchnama.com (Render Static Site, custom domain via Porkbun DNS). HTTPS via Let's Encrypt. CORS allows pitchnama.com + www + onrender.com + localhost. Auto-deploy from GitHub main on push. RESOLVED 30 Jun 2026: DuckDB refactor shipped. Engine now queries the parquet from disk via DuckDB (per-request cursors for thread safety) instead of loading all 4.4M rows into pandas RAM. Peak memory ~249MB (was near 2GB). Output verified byte-identical across all endpoints (96 reference captures, 6 test pairs x 4 formats). A thread-safety bug (shared DuckDB connection 500-ing under concurrent requests) was found and fixed post-deploy; verification now includes a concurrency test. Memory refactor verified, but Starter (512MB) crashed under heavy concurrent load during stress testing, so chose Standard ($25/mo, 2GB) for launch headroom. Tier can drop to Starter later if real traffic proves light.

**Estimate:** ~2–3 weeks from here at 2–3 hrs/day to reach the hosting moment.

**Two-server dev setup:**
- FastAPI: `python -m uvicorn api:app --reload` (port 8000, from ROOT)
- Vite: `npm run dev` (port 5173, from `frontend/`)
- Git always from ROOT.

---

## 6. Standing Duties (must be flagged proactively)

1. **Clean hosting trigger** — when Himmat is about to put pitchnama.com on his
   CV, send it to a recruiter, or launch Instagram / share widely → STOP and set up
   clean ~$5/month hosting (no-sleep, clean URL, real custom domain). Streamlit free
   tier sleeps ("Zzzz") and can't do clean custom domains. Flag all costs BEFORE they happen.
2. **Refresh the data mirror weekly** (or before sharing widely) — run
   `python scripts/refresh_mirror.py` from local machine. The robot now reads from
   the GitHub Release mirror, NOT Cricsheet directly. If the mirror is stale, the
   data is stale.
3. **Write decisions down** — keep this file and the repo updated each session.
4. **Fresh-chat handoff** — when a chat gets slow/large, write a full handoff message.
5. **README is stale** — update during a dedicated README pass (old tagline,
   wrong match count, T20-only phases, "scout reports in development", "Streamlit
   planned"). Don't put repo link on CV until done.
6. **Node.js workflow bump** — `actions/checkout@v4` and `actions/setup-python@v5`
   target Node.js 20, which GitHub is now "forcing to run on Node.js 24." Workflow
   still passes, but bump these before they actually break. Not urgent yet.

---

## 7. Working Habits & Reference

- Start each session with `git pull` (data mirror refreshes via release; robot pushes
  parquets nightly).
- Spoon-fed steps: lead with do-this-now, explain in summary. Targeted edits with
  exact location by default; full files only when asked or when the change is too
  tangled. Saves usage time.
- Direct, honest collaboration; push back on bad ideas; MCQ-style choices when deciding.
- Verify cricket facts against data, not memory. Verify numbers before committing.
- Lowercase/snake_case Python, type hints, imperative commits, DRY. Delete scratch files before commit.
- **Test pair:** Rohit Sharma (RG Sharma) vs Pat Cummins (PJ Cummins).
  Known-good: 532 balls all-formats / 46 IPL / 225 Test / 15 dismissals all-formats.
- Licensing: code MIT; data credits Cricsheet (CC BY-SA 4.0) + cricketdata (GPL-3).
- Tooling: VS Code, Git, Python 3.14, Node.js + npm, gh CLI (authenticated as
  himmatsgrewal). R/RStudio for the monthly `player_meta.csv` refresh.

---

## 8. What's Already Done

**The engine (COMPLETE, do not rebuild):**
**Data access (DuckDB, 30 Jun 2026):** the engine reads the parquet from disk via DuckDB on demand (`cache.query_deliveries`), returning only the rows a query needs. pandas still does all the maths on the small result, so numbers are identical to the old full-load path. One shared DuckDB connection, a fresh `.cursor()` per query for thread safety. This is what lets the service run on Render without loading ~4.4M rows into RAM.
4.4M+ deliveries · 9,400+ matches · 7 competitions · 3 formats (Cricsheet), growing
weekly via the manual mirror refresh + nightly robot rebuild.
Modular Python package (cache, matchup, scout_report, players, charts, data_loader).
Format-aware phases (T20 / ODI / Test ball-age). Bilingual EN+Hindi reports.
Full player names + countries (cricketdata `player_meta`, joined on `cricsheet_id`) +
~374 curated overrides + multi-field search. Dismissal logic fixed (bowler-credited
only; run-outs excluded). Plotly matchup-vs-baseline chart (Streamlit). Streamlit
Cloud deployment still live at pitchnama.streamlit.app (URL-forwarded from
pitchnama.com). To be replaced by the Stage 2 site at the $5 hosting moment.

**Data pipeline (CURRENT ARCHITECTURE — permanent fix):**
Cricsheet's bot filter periodically blocks cloud IP ranges (GitHub Actions
included). To make the robot independent of that:
- A `data-mirror` GitHub Release on this repo holds the 7 Cricsheet zips.
- `pitchnama/data_loader.py` `download_dataset(source='mirror')` (the default) reads
  from the mirror; `source='cricsheet'` reads upstream.
- `scripts/refresh_mirror.py` is Himmat's weekly job: downloads fresh from Cricsheet
  (local IP works) → uploads to the data-mirror Release via `gh release upload --clobber`.
- The robot (nightly) downloads from the mirror, rebuilds parquets, commits.
- GitHub never blocks itself, so the robot can never fail to fetch zips again.
- Trade-off accepted: the mirror is only as fresh as Himmat's last weekly refresh.
  Cricsheet data isn't real-time anyway (batched days after matches).

**Stage 1 — the API bridge (COMPLETE):**
`api.py` at repo root wraps the untouched engine in FastAPI. Endpoints (all JSON,
verified, committed):
- `/matchup?batter=&bowler=` → head-to-head
- `/baseline?batter=` → batter's own baseline
- `/compare?batter=&bowler=` → matchup vs baseline (feeds the tilt meter and charts)
- `/players` → full searchable player list (label, scorecard, country, search blob)
- `/stats` → live dataset totals (deliveries, matches, competitions)
- `/report` → bilingual EN+Hindi scout narrative (broadcast pundit voice)

Web layer uses `match_format` param → passed to engine's `format` (avoids the
Python `format` builtin clash). CORS enabled for `localhost:5173`.
Run locally: `python -m uvicorn api:app --reload`.

**Stage 2 — front-end (IN PROGRESS, near complete):**

Environment:
- Node.js + npm installed (Windows); PowerShell exec-policy set with
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- React app scaffolded via Vite (JavaScript) in `frontend/`.
- Tailwind v4 wired (`@tailwindcss/vite` + `@theme` brand colours in `index.css`).
- Recharts installed for the Charts tab.
- gh CLI installed for the weekly mirror refresh + future deployment.

Landing page (`App.jsx`):
- Green header bar (Pitch + bright-gold "Nama") on richer off-white background
  with green/gold radial glows.
- Centered content: headline, tagline.
- Searchable batter (green) and bowler (gold) dropdowns — reusable `PlayerSelect`,
  controlled, fetches `/players` once, filters in-browser by the `search` blob.
- Format selector (All formats / T20 / ODI / Test).
- Analyse button.
- Quick-try chips: Rohit Sharma vs Pat Cummins · Virat Kohli vs Kagiso Rabada ·
  David Warner vs Stuart Broad.
- Live stat line from `/stats`.

Floodlit transition:
- Full-screen black overlay fades in 500ms → view swaps → fades out 500ms.
- Triggered both ways: Analyse and Back.

Analysis screen (`App.jsx`):
- Dark background `#0d1117`, white text.
- Top bar: ← Back · PitchNama wordmark (warm gold "Nama").
- Matchup title (green name vs gold name) with animated entrance.
- "Format · matches" subtitle.
- **Tilt meter:** SVG semicircle (green left, gold right), animated white needle
  (1100ms cubic-bezier overshoot), verdict line ("Bowler edge · slight"), why line,
  small-sample dimming. Uses DRAFT formula (see §4a-i).
- 6 stat cards staggered fade-in: Balls, Runs, Avg, SR, Dismissals, Matches.
- Tab bar: Charts · Phases · Report. All three tabs FULLY BUILT.
- **Phases tab:** per-format tables (T20/ODI/Test) of phase splits (Balls, Runs,
  Avg, SR, Wkts, Dot%).
- **Charts tab:** four sections in narrative order — (1) Career baseline vs this
  matchup (grouped bar, green vs gold, SR and Avg); (2) Phase strike rate per format
  (one mini chart per format, green=usual / gold=matchup); (3) Pressure cards (dot %
  and boundary %, with green/gold arrows showing direction); (4) Strike rate by
  competition (gold bars with dashed green career-SR reference line). All with
  branded dark tooltip and entrance animation.
- **Report tab:** stacked English (left aligned, green label) + Hindi (left aligned,
  green label) broadcast pundit narratives from `/report`.

NOT yet built:
- Generate Card button + shareable card (square 1:1 + portrait 4:5)
- Tilt-meter formula calibration (still using draft)
- Tilt-meter glow polish on the dark screen
- README pass
- Node.js workflow bump (standing duty)
- Logo + font pass (end-of-project)
- Real ~$5/mo hosting + pitchnama.com pointing to the new site