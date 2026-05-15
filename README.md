# PitchNama 🏏

> *Every pitch tells a story.*

**PitchNama** is an open-source cricket matchup analytics tool that goes beyond averages and strike rates. It produces phase-aware, format-aware insights and bilingual scout reports (English + Hindi) for any batter–bowler pair, drawing on ball-by-ball data across cricket's major formats and competitions.

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
- **Format-aware filtering** — scope any analysis to T20, ODI, or Test cricket; or to a specific competition (IPL, T20Is, Tests, BBL, PSL, CPL, etc.)
- **Phase-aware splits** — separate analysis for the powerplay (overs 1–6), middle overs (7–15), and death (16–20)
- **Career baselines** — every matchup contextualised against the batter's overall stats so insights are honest, not just numerical
- **Sample-size honesty** — small samples are flagged, not hidden
- **Bilingual scout reports** — auto-generated narrative summaries in English and Hindi *(in development)*

---

## Data

PitchNama is built on **4.4 million ball-by-ball deliveries** across **9,327 professional cricket matches**, sourced from [Cricsheet](https://cricsheet.org/) under CC BY-SA 4.0.

| Competition | Matches | Deliveries |
|---|---:|---:|
| Men's Tests | 877 | 1,692,797 |
| Men's ODIs | 2,530 | 1,341,897 |
| Men's T20Is | 3,278 | 739,700 |
| Indian Premier League | 1,216 | 289,189 |
| Big Bash League | 662 | 153,250 |
| Caribbean Premier League | 407 | 95,024 |
| Pakistan Super League | 357 | 83,799 |

All data is downloaded, parsed, and cached as a single Parquet file (~14 MB) for instant in-memory queries.

---

## Architecture

**Package structure:**

- `pitchnama/data_loader.py` — Cricsheet download + JSON parsing
- `pitchnama/cache.py` — Parquet cache build/load
- `pitchnama/matchup.py` — Analysis functions (filterable by format/competition)
- `scripts/download_data.py` — Pull latest data from Cricsheet
- `scripts/build_cache.py` — Rebuild the unified Parquet cache

The cache is loaded once per session and served from memory thereafter — every analysis call after the first runs in milliseconds.

---

## Status

🚧 **Active development.** Multi-format ball-by-ball analysis works end-to-end. Up next: bilingual scout report generation, Streamlit web app, and deployment to **pitchnama.com**.

---

## Tech

- **Python 3.14**
- **pandas + pyarrow** — data wrangling and Parquet storage
- **Streamlit** — web interface *(planned)*
- **Cricsheet** — data source (CC BY-SA 4.0)

---

## Author

Built by **Himmat Singh Grewal**, Master of Data Science @ RMIT University, Melbourne.

- 🐙 [GitHub](https://github.com/himmatsgrewal)
- 💼 [LinkedIn](https://linkedin.com/in/himmatsinghgrewal)

---

## License

[MIT](LICENSE) — free to use, modify, and distribute. Just keep the credit.

---

> *"PitchNama — the chronicle of every contest."*