# PitchNama 🏏

> *The chronicle of every contest.*

**PitchNama** is an open-source cricket matchup analytics tool that goes beyond averages and strike rates. It produces phase-aware, format-aware insights, a bilingual broadcast-style scout report (English + Hindi), and a flagship "Upper Hand" tilt meter for any batter–bowler pair, drawing on ball-by-ball data across cricket's major formats and competitions.

The name is a fusion of *pitch* (the surface where every match is decided) and *nama* (the Hindustani word for "chronicle" or "record" — as in *Akbarnama*, the great chronicles of the Mughal era). PitchNama is the chronicle of every contest between bat and ball.

---

## Why PitchNama

Public cricket analytics tools tell you *what happened* — runs scored, wickets taken, averages over a career. They rarely tell you *what's actually happening* in a specific matchup, in a specific phase, in a specific format, against a specific opponent.

A coach preparing for a Test series against Australia doesn't want to know that Rohit Sharma averages 30 in IPL. They want to know:

- *How does Rohit play Pat Cummins specifically?*
- *Does that change between Tests, ODIs, and T20s?*
- *Does Cummins's edge change in different phases?*
- *How does it compare to Rohit's career baselines in that format?*

PitchNama is built to answer those questions.

---

## What it does

- **Matchup analysis** — head-to-head stats for any batter–bowler pair: runs, balls, dismissals, strike rate, average, boundary rate, dot ball percentage
- **Flagship "Upper Hand" tilt meter** — a green/gold semicircular gauge whose needle leans toward whoever holds the advantage. Compares matchup strike rate and balls-per-dismissal to the batter's own career baseline. Includes a plain-English verdict ("Bowler edge · slight") and a "why" line so the read is never numbers without meaning.
- **Format-aware filtering** — scope any analysis to T20, ODI, or Test cricket; or to a specific competition (IPL, T20Is, Tests, BBL, PSL, CPL, etc.)
- **Phase-aware splits** — separate analysis for the powerplay, middle overs, and death (T20/ODI), or the early/middle/old-ball phases of a Test innings
- **Career baselines** — every matchup contextualised against the batter's overall stats so insights are honest, not just numerical
- **Sample-size honesty** — small samples are flagged (the meter dims, the report adds a caveat), not hidden
- **Bilingual scout report** — auto-generated broadcast-pundit-style narratives in English and Hindi, including the edge, the supporting numbers translated into meaning, the sharpest phase finding, and the format split where relevant
- **Visual analytics** — career-baseline-vs-matchup bars, phase strike-rate per format, dot/boundary pressure cards, and strike rate by competition with a career-baseline reference line
- **Shareable cards** — one-click 1080×1080 PNG download with the matchup title, tilt meter, verdict, key stats, and PitchNama branding. Designed for Instagram and WhatsApp.

---

## Data

PitchNama is built on **4.4 million+ ball-by-ball deliveries** across **9,400+ professional cricket matches**, sourced from [Cricsheet](https://cricsheet.org/) under CC BY-SA 4.0. The dataset grows continuously — data is refreshed weekly from Cricsheet and rebuilt by an automated workflow every night.

| Competition | Matches | Deliveries |
|---|---:|---:|
| Men's Tests | 881 | 1,699,286 |
| Men's ODIs | 2,543 | 1,348,815 |
| Men's T20Is | 3,382 | 762,586 |
| Indian Premier League | 1,243 | 295,732 |
| Big Bash League | 662 | 153,250 |
| Caribbean Premier League | 407 | 95,024 |
| Pakistan Super League | 357 | 83,799 |

Player names and countries are joined in from a curated metadata table (16,000+ players) so the front-end can display human-readable names ("Rohit Sharma · India") rather than scorecard initials. All data is downloaded, parsed, and cached as a single Parquet file (~14 MB) for instant in-memory queries.

---

## Architecture

PitchNama is a three-layer stack:

**1. The engine (Python).** A modular package that owns the data pipeline and the analytics.

- `pitchnama/data_loader.py` — Cricsheet zip download + JSON parsing. Reads from a self-hosted GitHub Release mirror by default; `source='cricsheet'` mode for the weekly refresh script.
- `pitchnama/cache.py` — Build and load the unified Parquet cache.
- `pitchnama/matchup.py` — Head-to-head, baseline, and matchup-vs-baseline analytics.
- `pitchnama/players.py` — Player name registry with display-name resolution + multi-field search.
- `pitchnama/scout_report.py` — Bilingual broadcast-pundit scout report generation.
- `pitchnama/charts.py` — Plotly chart helpers.

**2. The API (FastAPI).** `api.py` at the repo root exposes the engine over HTTP as JSON:

- `GET /matchup` — head-to-head
- `GET /baseline` — batter's career baseline
- `GET /compare` — matchup vs baseline (feeds the tilt meter and charts)
- `GET /players` — searchable player list
- `GET /stats` — live dataset totals
- `GET /report` — bilingual EN+Hindi scout narrative

**3. The web front-end (React + Vite + Tailwind).** A custom cinematic web app under `frontend/`. A light landing page with a searchable matchup picker fades through black into a dark "floodlit stadium" analysis screen featuring the tilt meter, headline numbers, and three tabs (Charts, Phases, Report). A Generate Card button downloads a 1080×1080 Instagram-ready PNG.

**Automated pipeline.** A GitHub Actions workflow rebuilds the Parquet cache and player registry nightly. Source data is mirrored on a GitHub Release so the workflow is independent of Cricsheet's bot filter.

---

## Status

🟢 **In active development, approaching v1 launch.**

Done: full Python engine · multi-format ball-by-ball analytics · bilingual scout report · FastAPI bridge · custom React front-end · floodlit transition · animated tilt meter · four-section Charts tab · Phases tab · Report tab · Generate Card button · automated nightly data rebuild · self-hosted Cricsheet mirror.

Up next: tilt-meter formula calibration · final visual polish · deployment to **pitchnama.com** with real hosting.

---

## Tech

- **Python 3.14** — engine
- **pandas + pyarrow** — data wrangling and Parquet storage
- **FastAPI + Uvicorn** — JSON API
- **React + Vite + Tailwind CSS** — front-end
- **Recharts** — visualisations
- **html-to-image** — card export
- **GitHub Actions + GitHub Releases** — automated data pipeline + mirror
- **Cricsheet** (CC BY-SA 4.0) — primary data source
- **cricketdata R package** (GPL-3) — player metadata source

---

## Roadmap

Post-launch, PitchNama will expand into a full cricket analytics platform with three top-level sections:

- **Men's cricket** — what's launching now (matchups, stats, scout reports)
- **Women's cricket** — same depth of analytics, applied to women's data (WT20Is, WODIs, WBBL, WPL)
- **Venues** — per-ground analysis: batting-friendly vs bowling-friendly, phase behaviour, historical patterns

---

## Author

Built by **Himmat Singh Grewal**, Master of Data Science @ RMIT University, Melbourne.

- 🌐 [GitHub](https://github.com/himmatsgrewal)
- 💼 [LinkedIn](https://linkedin.com/in/himmatsinghgrewal)

---

## License

[MIT](LICENSE) — free to use, modify, and distribute. Just keep the credit.

Cricsheet data is distributed under CC BY-SA 4.0. Player metadata from the cricketdata R package is GPL-3.

---

> *"PitchNama — the chronicle of every contest."*