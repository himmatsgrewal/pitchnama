"""
matchup.py — Cricket matchup analytics.

Core analysis functions for PitchNama. Given a batter and bowler, computes
head-to-head stats with phase-aware splits and contextualizes them against
the batter's career baseline.

This version reads from the cached Parquet DataFrame (data/ipl_deliveries.parquet)
for near-instant lookups. Build the cache first via:
    python scripts/build_cache.py

Phase definitions (T20, 0-indexed overs):
    Powerplay: overs 0-5    (overs 1-6 in human terms)
    Middle:    overs 6-14   (overs 7-15 in human terms)
    Death:     overs 15-19  (overs 16-20 in human terms)
"""

from functools import lru_cache
from typing import Optional

import pandas as pd

from .cache import load_cache


# ---------- Cache helpers ----------

@lru_cache(maxsize=1)
def _get_data() -> pd.DataFrame:
    """
    Load the full IPL deliveries DataFrame, cached in memory.

    The @lru_cache decorator means the Parquet file is read from disk
    exactly once per Python session. Every subsequent call returns the
    already-loaded DataFrame instantly.
    """
    return load_cache()


def get_phase(over: int) -> str:
    """Bucket a T20 over number (0-indexed) into a match phase."""
    if over <= 5:
        return 'Powerplay'
    elif over <= 14:
        return 'Middle'
    else:
        return 'Death'


def _safe_divide(numerator: float, denominator: float) -> Optional[float]:
    """Divide safely, returning None if denominator is zero."""
    return numerator / denominator if denominator > 0 else None


# ---------- Stat computation (works on any DataFrame slice) ----------

def _compute_stats(df: pd.DataFrame) -> dict:
    """
    Given a slice of the deliveries DataFrame, compute headline cricket stats.
    Returns balls, runs, wickets, avg, sr, dot_pct, fours, sixes, boundary_pct.
    """
    n = len(df)
    if n == 0:
        return {'balls': 0}

    runs = int(df['runs_batter'].sum())
    wickets = int(df['wicket'].sum())
    dots = int(((df['runs_batter'] == 0) & (df['runs_extras'] == 0)).sum())
    fours = int((df['runs_batter'] == 4).sum())
    sixes = int((df['runs_batter'] == 6).sum())

    return {
        'balls': n,
        'runs': runs,
        'wickets': wickets,
        'avg': _safe_divide(runs, wickets),
        'sr': (runs / n) * 100,
        'dot_pct': (dots / n) * 100,
        'fours': fours,
        'sixes': sixes,
        'boundary_pct': ((fours + sixes) / n) * 100,
    }


def _phase_split(df: pd.DataFrame) -> dict:
    """Split a DataFrame of balls by phase and compute stats per phase."""
    result = {}
    for phase_name in ['Powerplay', 'Middle', 'Death']:
        if phase_name == 'Powerplay':
            mask = df['over'] <= 5
        elif phase_name == 'Middle':
            mask = (df['over'] >= 6) & (df['over'] <= 14)
        else:
            mask = df['over'] >= 15
        result[phase_name] = _compute_stats(df[mask])
    return result


# ---------- Public API ----------

def analyze_matchup(batter_name: str, bowler_name: str) -> dict:
    """
    Full matchup analysis between a batter and a bowler.

    Returns headline stats, phase breakdown, and number of distinct matches
    the matchup occurred in. If no balls exist between the pair, returns a
    minimal dict with total_balls=0.
    """
    df = _get_data()
    matchup_df = df[(df['batter'] == batter_name) & (df['bowler'] == bowler_name)]

    if len(matchup_df) == 0:
        return {
            'batter': batter_name,
            'bowler': bowler_name,
            'total_balls': 0,
            'message': 'No deliveries found between these players in our dataset.',
        }

    headline = _compute_stats(matchup_df)
    phase_breakdown = _phase_split(matchup_df)
    matches_played = matchup_df['match_id'].nunique()

    return {
        'batter': batter_name,
        'bowler': bowler_name,
        'total_balls': headline['balls'],
        'total_runs': headline['runs'],
        'dismissals': headline['wickets'],
        'avg': headline['avg'],
        'sr': headline['sr'],
        'fours': headline['fours'],
        'sixes': headline['sixes'],
        'boundary_pct': headline['boundary_pct'],
        'dot_pct': headline['dot_pct'],
        'phase_breakdown': phase_breakdown,
        'matches_played': int(matches_played),
    }


def analyze_batter_overall(batter_name: str) -> Optional[dict]:
    """
    Compute a batter's career IPL baseline across all bowlers. Phase-split.
    Used to contextualize matchup numbers against career norms.
    Returns None if the batter has no balls in our dataset.
    """
    df = _get_data()
    batter_df = df[df['batter'] == batter_name]

    if len(batter_df) == 0:
        return None

    return {
        'batter': batter_name,
        'overall': _compute_stats(batter_df),
        'phase_stats': _phase_split(batter_df),
    }


def compare_matchup_to_baseline(batter_name: str, bowler_name: str) -> dict:
    """
    Compare a specific matchup to the batter's career baseline.
    Returns a structured dict suitable for rendering or feeding into a templater.
    """
    matchup = analyze_matchup(batter_name, bowler_name)
    baseline = analyze_batter_overall(batter_name)

    if matchup['total_balls'] == 0 or baseline is None:
        return {
            'batter': batter_name,
            'bowler': bowler_name,
            'message': 'Insufficient data for comparison.',
        }

    phases_compared = {}
    for phase in ['Powerplay', 'Middle', 'Death']:
        m_stats = matchup['phase_breakdown'].get(phase, {'balls': 0})
        b_stats = baseline['phase_stats'].get(phase, {'balls': 0})

        if m_stats['balls'] == 0:
            phases_compared[phase] = {'matchup_balls': 0}
            continue

        phases_compared[phase] = {
            'matchup_balls': m_stats['balls'],
            'baseline_balls': b_stats.get('balls', 0),
            'matchup_avg': m_stats.get('avg'),
            'baseline_avg': b_stats.get('avg'),
            'matchup_sr': m_stats.get('sr'),
            'baseline_sr': b_stats.get('sr'),
            'matchup_dot_pct': m_stats.get('dot_pct'),
            'baseline_dot_pct': b_stats.get('dot_pct'),
        }

    return {
        'batter': batter_name,
        'bowler': bowler_name,
        'sample_size': matchup['total_balls'],
        'matches_played': matchup['matches_played'],
        'overall_baseline': baseline['overall'],
        'overall_matchup': {
            'balls': matchup['total_balls'],
            'runs': matchup['total_runs'],
            'wickets': matchup['dismissals'],
            'avg': matchup['avg'],
            'sr': matchup['sr'],
        },
        'phases': phases_compared,
    }