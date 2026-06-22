"""
api.py — FastAPI wrapper around the PitchNama engine.

Exposes the existing analysis functions over HTTP as JSON, so a
front-end (or anything else) can request matchup data by URL.
The engine itself is untouched — this file only imports and calls it.
"""

from functools import lru_cache
from typing import Optional

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pitchnama.matchup import (
    analyze_matchup,
    analyze_batter_overall,
    compare_matchup_to_baseline,
)
from pitchnama.players import load_registry
from pitchnama.cache import CACHE_PATH
from pitchnama.scout_report import generate_report

app = FastAPI(title="PitchNama API")

# Allow the local Vite dev server (the React front-end) to call this API.
# Browsers block cross-origin requests by default; this tells the API to
# permit calls coming from the front-end's address during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def _get_stats() -> dict:
    """
    Count the live dataset totals once, then reuse.

    Reads only the two columns it needs (cheap on memory), counted the same
    way build_cache reports them. The figures reflect whatever the daily
    auto-update robot last built; cached for the life of the server process,
    so a redeploy after fresh data picks up the new numbers.
    """
    df = pd.read_parquet(
        CACHE_PATH, columns=['match_id', 'competition'], engine='pyarrow'
    )
    return {
        'deliveries': int(len(df)),
        'matches': int(df['match_id'].nunique()),
        'competitions': int(df['competition'].nunique()),
    }


@lru_cache(maxsize=1)
def _get_player_options() -> list[dict]:
    """
    Build the searchable player option list once, then reuse.

    Mirrors the Streamlit app's get_player_options: each option shows a
    display name + country, is findable by display/full/scorecard/country,
    and returns the scorecard name (what the engine expects).
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
            'country': country,
            'search': search_blob,
        })

    options.sort(key=lambda x: x['label'].lower())
    return options


@app.get("/")
def home() -> dict:
    """A simple health-check so we can confirm the server is alive."""
    return {"status": "PitchNama API is running"}


@app.get("/stats")
def stats() -> dict:
    """Live dataset totals for the landing page (deliveries, matches, competitions)."""
    return _get_stats()


@app.get("/players")
def players() -> list[dict]:
    """
    Return the full searchable player list for the front-end.

    Each item: {label, scorecard, country, search}. The front-end shows
    label + country, searches the 'search' blob, and sends 'scorecard'
    back to /matchup or /compare.
    """
    return _get_player_options()


@app.get("/matchup")
def matchup(
    batter: str,
    bowler: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """Head-to-head matchup data for a batter vs a bowler."""
    return analyze_matchup(
        batter_name=batter,
        bowler_name=bowler,
        format=match_format,
        competition=competition,
    )


@app.get("/baseline")
def baseline(
    batter: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """A batter's own baseline (across all bowlers in scope)."""
    result = analyze_batter_overall(
        batter_name=batter,
        format=match_format,
        competition=competition,
    )
    if result is None:
        return {
            "batter": batter,
            "match_format": match_format,
            "competition": competition,
            "message": "No deliveries found for this batter in this scope.",
        }
    return result


@app.get("/compare")
def compare(
    batter: str,
    bowler: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """Compare a matchup to the batter's own baseline (feeds the tilt meter)."""
    return compare_matchup_to_baseline(
        batter_name=batter,
        bowler_name=bowler,
        format=match_format,
        competition=competition,
    )


@app.get("/report")
def report(
    batter: str,
    bowler: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """
    Bilingual scout report for a matchup. Returns the English and Hindi
    narratives generated from the same compare_matchup_to_baseline data
    the tilt meter uses.
    """
    data = compare_matchup_to_baseline(
        batter_name=batter,
        bowler_name=bowler,
        format=match_format,
        competition=competition,
    )
    return {
        "english": generate_report(data, language='en'),
        "hindi": generate_report(data, language='hi'),
    }