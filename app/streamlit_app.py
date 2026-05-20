"""
streamlit_app.py — PitchNama web interface.

A simple Streamlit app that lets users pick any batter–bowler pair from the
full Cricsheet player registry, scope the analysis to a format or competition,
and view headline numbers plus bilingual scout reports.

Run from the project root:
    python -m streamlit run app/streamlit_app.py
"""

import sys
from pathlib import Path

# Add project root to Python path so we can import the pitchnama package
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
import streamlit as st

from pitchnama.cache import load_cache
from pitchnama.matchup import compare_matchup_to_baseline
from pitchnama.players import load_registry, load_display_names, display_name
from pitchnama.scout_report import generate_report


# ---------- Page setup ----------

st.set_page_config(
    page_title="PitchNama — Cricket Matchup Analytics",
    page_icon="🏏",
    layout="centered",
)

# Custom CSS to reduce padding and feel a bit less Streamlit-default
st.markdown(
    """
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 880px; }
    h1 { letter-spacing: -0.5px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------- Header ----------

st.title("PitchNama 🏏")
st.markdown("*Every pitch tells a story.*")
st.markdown(
    "Open-source cricket matchup analytics. Pick any batter and bowler, "
    "scope the analysis, and get a bilingual scout report."
)
st.divider()


# ---------- Load player list (cached so it's instant after first load) ----------

@st.cache_data
def get_player_options() -> list[dict]:
    """
    Return player option dicts for the dropdowns, using the enriched registry.
    Each option: label (display name), scorecard, full, country, and a combined
    'search' string so a player is findable by short name, full name, or scorecard.
    """
    registry = load_registry()

    grouped = (registry
               .sort_values('appearances', ascending=False)
               .groupby('scorecard_name', as_index=False)
               .agg({
                   'appearances': 'sum',
                   'display_name': 'first',
                   'full_name': 'first',
                   'country': 'first',
               }))

    options = []
    for _, row in grouped.iterrows():
        scorecard = row['scorecard_name']
        display = row['display_name'] if pd.notna(row['display_name']) else scorecard
        full = row['full_name'] if pd.notna(row['full_name']) else ''
        country = row['country'] if pd.notna(row['country']) else ''
        search_blob = f"{display} {full} {scorecard} {country}".lower()
        options.append({
            'label': display,
            'scorecard': scorecard,
            'full': full,
            'country': country,
            'search': search_blob,
        })

    options.sort(key=lambda x: x['label'].lower())
    return options


@st.cache_data
def warmup_cache():
    """Force the deliveries Parquet to load into memory once, so first query is fast."""
    load_cache()


with st.spinner("Loading PitchNama..."):
    player_options = get_player_options()
    warmup_cache()


# ---------- Selection UI ----------

st.subheader("Pick the matchup")

# Streamlit's selectbox is searchable by default — typing filters the list live.
# We pass a list of (display, scorecard) tuples and use format_func to show display name.
col1, col2 = st.columns(2)

with col1:
    batter_choice = st.selectbox(
        "Batter",
        options=player_options,
        format_func=lambda x: x['label'] + (f"  ·  {x['country']}" if x['country'] else ""),
        index=None,
        placeholder="Type a name — full or short…",
        key="batter_select",
    )

with col2:
    bowler_choice = st.selectbox(
        "Bowler",
        options=player_options,
        format_func=lambda x: x['label'] + (f"  ·  {x['country']}" if x['country'] else ""),
        index=None,
        placeholder="Type a name — full or short…",
        key="bowler_select",
    )

# Scope filters
col3, col4 = st.columns(2)

with col3:
    format_choice = st.selectbox(
        "Format",
        options=['All formats', 'T20', 'ODI', 'Test'],
        index=0,
    )

with col4:
    competition_choice = st.selectbox(
        "Competition (optional)",
        options=['Any', 'ipl', 't20i', 'odi', 'test', 'bbl', 'psl', 'cpl'],
        index=0,
    )

analyze = st.button("Analyse matchup", type="primary", use_container_width=True)


# ---------- Run analysis ----------

if analyze:
    if not batter_choice or not bowler_choice:
        st.warning("Please pick both a batter and a bowler.")
        st.stop()

    if batter_choice['scorecard'] == bowler_choice['scorecard']:
        st.warning("Batter and bowler must be different players.")
        st.stop()

    batter_scorecard = batter_choice['scorecard']
    bowler_scorecard = bowler_choice['scorecard']

    # Normalise scope arguments
    fmt = None if format_choice == 'All formats' else format_choice
    comp = None if competition_choice == 'Any' else competition_choice

    with st.spinner("Crunching the numbers..."):
        data = compare_matchup_to_baseline(
            batter_scorecard, bowler_scorecard,
            format=fmt, competition=comp,
        )

    if 'message' in data:
        st.warning(data['message'])
        st.stop()

    # ---------- Headline stats ----------

    st.divider()
    st.subheader(f"{batter_choice['label']} vs {bowler_choice['label']}")

    matchup = data['overall_matchup']
    baseline = data['overall_baseline']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Balls", f"{matchup['balls']:,}")
    m2.metric("Runs", f"{matchup['runs']:,}")
    m3.metric("Dismissals", f"{matchup['wickets']}")
    avg_str = f"{matchup['avg']:.1f}" if matchup['avg'] is not None else "—"
    m4.metric("Average", avg_str,
              delta=(f"vs career {baseline['avg']:.1f}"
                     if baseline['avg'] is not None else None),
              delta_color="off")

    m5, m6 = st.columns(2)
    m5.metric("Strike rate", f"{matchup['sr']:.1f}",
              delta=f"vs career {baseline['sr']:.1f}",
              delta_color="off")
    m6.metric("Matches", f"{data['matches_played']}")

    # ---------- Per-competition breakdown ----------

    comp_breakdown = data.get('competition_breakdown', {})
    nonzero = {c: s for c, s in comp_breakdown.items() if s.get('balls', 0) > 0}
    if len(nonzero) >= 2:
        st.divider()
        st.subheader("Across competitions")
        comp_df = pd.DataFrame([
            {
                'Competition': c.upper(),
                'Balls': s['balls'],
                'Runs': s['runs'],
                'Wickets': s['wickets'],
                'Average': f"{s['avg']:.1f}" if s.get('avg') is not None else "—",
                'Strike rate': f"{s['sr']:.1f}",
            }
            for c, s in sorted(nonzero.items(),
                               key=lambda kv: kv[1]['balls'], reverse=True)
        ])
        st.dataframe(comp_df, hide_index=True, use_container_width=True)

    # ---------- Phase breakdown (T20 only) ----------

    phases = data.get('phases', {})
    nonzero_phases = {p: s for p, s in phases.items()
                      if s.get('matchup_balls', 0) > 0}
    if nonzero_phases:
        st.divider()
        st.subheader("Phase breakdown (T20 phases)")
        phase_df = pd.DataFrame([
            {
                'Phase': p,
                'Balls': s['matchup_balls'],
                'Matchup avg': f"{s['matchup_avg']:.1f}" if s.get('matchup_avg') is not None else "—",
                'Baseline avg': f"{s['baseline_avg']:.1f}" if s.get('baseline_avg') is not None else "—",
                'Matchup SR': f"{s['matchup_sr']:.1f}" if s.get('matchup_sr') is not None else "—",
                'Baseline SR': f"{s['baseline_sr']:.1f}" if s.get('baseline_sr') is not None else "—",
            }
            for p, s in nonzero_phases.items()
        ])
        st.dataframe(phase_df, hide_index=True, use_container_width=True)
        if fmt != 'T20' and comp not in ('ipl', 't20i', 'bbl', 'psl', 'cpl'):
            st.caption("ℹ️ Phase definitions are T20-based; shown here for diagnostic purposes only.")

    # ---------- Bilingual scout reports ----------

    st.divider()
    st.subheader("Scout report")

    en_col, hi_col = st.columns(2)
    with en_col:
        st.markdown("**English**")
        st.markdown(generate_report(data, language='en'))
    with hi_col:
        st.markdown("**Hindi**")
        st.markdown(generate_report(data, language='hi'))


# ---------- Footer ----------

st.divider()
st.caption(
    "Built by [Himmat Singh Grewal](https://github.com/himmatsgrewal) · "
    "Open-source on [GitHub](https://github.com/himmatsgrewal/pitchnama) · "
    "Data: [Cricsheet](https://cricsheet.org/) (CC BY-SA 4.0)"
)