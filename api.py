"""
api.py — FastAPI wrapper around the PitchNama engine.

Exposes the existing analysis functions over HTTP as JSON, so a
front-end (or anything else) can request matchup data by URL.
The engine itself is untouched — this file only imports and calls it.
"""

from typing import Optional

from fastapi import FastAPI

from pitchnama.matchup import analyze_matchup

app = FastAPI(title="PitchNama API")


@app.get("/")
def home() -> dict:
    """A simple health-check so we can confirm the server is alive."""
    return {"status": "PitchNama API is running"}


@app.get("/matchup")
def matchup(
    batter: str,
    bowler: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """
    Return head-to-head matchup data for a batter vs a bowler.

    Example:
        /matchup?batter=RG Sharma&bowler=PJ Cummins
    """
    return analyze_matchup(
        batter_name=batter,
        bowler_name=bowler,
        format=match_format,
        competition=competition,
    )