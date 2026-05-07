# PitchNama 🏏

> *Every pitch tells a story.*

**PitchNama** is an open-source cricket matchup analytics tool that goes beyond averages and strike rates. It produces phase-aware insights and bilingual scout reports (English + Hindi) for any batter–bowler pair, drawing on ball-by-ball data across cricket's major formats and competitions.

The name is a fusion of *pitch* (the surface where every match is decided) and *nama* (the Hindustani word for "chronicle" or "record" — as in *Akbarnama*, the great chronicles of the Mughal era). PitchNama is the chronicle of every contest between bat and ball.

---

## Why PitchNama

Public cricket analytics tools tell you *what happened* — runs scored, wickets taken, averages over a career. They rarely tell you *what's actually happening* in a specific matchup, in a specific phase, against a specific opponent.

A coach preparing for a match doesn't want to know that Rohit Sharma averages 30 in IPL. They want to know:

- *How does Rohit play Pat Cummins specifically?*
- *Does that change in the powerplay vs the death overs?*
- *How does it compare to his career baselines?*
- *What's the pattern across formats — IPL, T20Is, ODIs, Tests?*

PitchNama is built to answer those questions.

---

## What it does

- **Matchup analysis** — head-to-head stats for any batter–bowler pair: runs, balls, dismissals, strike rate, average, boundary rate, dot ball percentage
- **Phase-aware splits** — separate analysis for the powerplay (overs 1–6), middle overs (7–15), and death (16–20)
- **Career baselines** — every matchup contextualized against the batter's overall stats so insights are honest, not just numerical
- **Sample-size honesty** — small samples are flagged, not hidden
- **Bilingual scout reports** — auto-generated narrative summaries in English and Hindi *(in development)*
- **Multi-format coverage** — IPL is the first dataset; international cricket and other leagues are being added

---

## Status

🚧 **Active development.** Currently covers IPL men's matches (1,200+ matches, ~300,000 deliveries). International formats (T20I, ODI, Test) coming next.

---

## Data

All analysis is built on ball-by-ball match data from [Cricsheet](https://cricsheet.org/), licensed under CC BY-SA 4.0. Cricsheet is a free, community-maintained source of cricket data trusted by researchers, analysts, and journalists worldwide.

---

## Tech

- **Python** (3.14+) — core analysis
- **pandas** — data wrangling
- **Streamlit** — web interface *(in development)*

---

## Author

Built by **Himmat Singh Grewal**, Master of Data Science @ RMIT University.

- 🐙 [GitHub](https://github.com/himmatsgrewal)
- 💼 [LinkedIn](https://linkedin.com/in/himmatsinghgrewal)

---

## License

[MIT](LICENSE) — free to use, modify, and distribute. Just keep the credit.

---

> *"PitchNama — the chronicle of every contest."*