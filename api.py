"""
api.py — FastAPI wrapper around the PitchNama engine.

Exposes the existing analysis functions over HTTP as JSON, so a
front-end (or anything else) can request matchup data by URL.
The engine itself is untouched — this file only imports and calls it.
"""

from typing import Optional

from fastapi import FastAPI

from pitchnama.matchup import (
    analyze_matchup,
    analyze_batter_overall,
    compare_matchup_to_baseline,
)

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


@app.get("/baseline")
def baseline(
    batter: str,
    match_format: Optional[str] = None,
    competition: Optional[str] = None,
) -> dict:
    """
    Return a batter's own baseline (across all bowlers in scope).

    This is the reference the tilt meter measures a matchup against.

    Example:
        /baseline?batter=RG Sharma
    """
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
    """
    Compare a matchup to the batter's own baseline.

    This is the data the 'who has the upper hand' tilt meter will use.

    Example:
        /compare?batter=RG Sharma&bowler=PJ Cummins
    """
    return compare_matchup_to_baseline(
        batter_name=batter,
        bowler_name=bowler,
        format=match_format,
        competition=competition,
    )