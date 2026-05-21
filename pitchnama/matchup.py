"""
matchup.py — Cricket matchup analytics.

Core analysis functions for PitchNama. Given a batter and bowler, computes
head-to-head stats with format-aware phase splits, contextualised against
the batter's career baseline.

Phase definitions are FORMAT-AWARE:

    T20  (overs 0-indexed):
        Powerplay  overs 0-5    (1-6 human)
        Middle     overs 6-14   (7-15 human)
        Death      overs 15-19  (16-20 human)

    ODI:
        Powerplay  overs 0-9    (1-10 human)
        Middle     overs 10-39  (11-40 human)
        Death      overs 40-49  (41-50 human)

    Test (ball-age framing, per innings):
        First 30 overs   overs 0-29
        Overs 30-80      overs 30-79
        Overs 80+        overs 80+

Phase splits only make sense within a single format. For 'all formats'
scope, splits are computed PER FORMAT separately (never mixed).
"""

from functools import lru_cache
from typing import Optional

import pandas as pd

from .cache import load_cache


# ---------- Cache ----------

@lru_cache(maxsize=1)
def _get_data() -> pd.DataFrame:
    """Load the deliveries DataFrame once per session, then reuse."""
    return load_cache()


# ---------- Phase definitions (format-aware) ----------

# Ordered phase names per format
PHASE_NAMES = {
    'T20':  ['Powerplay', 'Middle', 'Death'],
    'ODI':  ['Powerplay', 'Middle', 'Death'],
    'Test': ['First 30 overs', 'Overs 30-80', 'Overs 80+'],
}


def get_phase(over: int, fmt: str) -> Optional[str]:
    """Return the phase name for a given (0-indexed) over and format."""
    if fmt == 'T20':
        if over <= 5:
            return 'Powerplay'
        elif over <= 14:
            return 'Middle'
        else:
            return 'Death'
    elif fmt == 'ODI':
        if over <= 9:
            return 'Powerplay'
        elif over <= 39:
            return 'Middle'
        else:
            return 'Death'
    elif fmt == 'Test':
        if over <= 29:
            return 'First 30 overs'
        elif over <= 79:
            return 'Overs 30-80'
        else:
            return 'Overs 80+'
    return None


def _phase_mask(df: pd.DataFrame, fmt: str, phase: str) -> pd.Series:
    """Boolean mask selecting deliveries in a given phase for a given format."""
    o = df['over']
    if fmt in ('T20', 'ODI'):
        if fmt == 'T20':
            bounds = {'Powerplay': (0, 5), 'Middle': (6, 14), 'Death': (15, 99)}
        else:
            bounds = {'Powerplay': (0, 9), 'Middle': (10, 39), 'Death': (40, 99)}
        lo, hi = bounds[phase]
        return (o >= lo) & (o <= hi)
    else:  # Test
        bounds = {'First 30 overs': (0, 29), 'Overs 30-80': (30, 79), 'Overs 80+': (80, 9999)}
        lo, hi = bounds[phase]
        return (o >= lo) & (o <= hi)


def _safe_divide(num: float, den: float) -> Optional[float]:
    return num / den if den > 0 else None


def _apply_filters(df: pd.DataFrame,
                   format: Optional[str] = None,
                   competition: Optional[str] = None) -> pd.DataFrame:
    if format is not None:
        df = df[df['format'] == format]
    if competition is not None:
        df = df[df['competition'] == competition]
    return df


# ---------- Stats ----------

def _compute_stats(df: pd.DataFrame) -> dict:
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


def _phase_split_for_format(df: pd.DataFrame, fmt: str) -> dict:
    """Compute phase stats for one format's deliveries, using that format's phases."""
    result = {}
    for phase in PHASE_NAMES[fmt]:
        sub = df[_phase_mask(df, fmt, phase)]
        result[phase] = _compute_stats(sub)
    return result


def _phase_splits_by_format(df: pd.DataFrame) -> dict:
    """
    Compute phase splits for each format present in df, separately.
    Returns {format: {phase: stats}}. Only includes formats with deliveries.
    """
    out = {}
    for fmt in ['T20', 'ODI', 'Test']:
        fmt_df = df[df['format'] == fmt]
        if len(fmt_df) > 0:
            out[fmt] = _phase_split_for_format(fmt_df, fmt)
    return out


def _competition_split(df: pd.DataFrame) -> dict:
    result = {}
    for comp in df['competition'].unique():
        result[comp] = _compute_stats(df[df['competition'] == comp])
    return result


# ---------- Public API ----------

def analyze_matchup(batter_name: str, bowler_name: str,
                    format: Optional[str] = None,
                    competition: Optional[str] = None) -> dict:
    """Full matchup analysis with format-aware phase splits."""
    df = _get_data()
    df = _apply_filters(df, format=format, competition=competition)
    matchup_df = df[(df['batter'] == batter_name) & (df['bowler'] == bowler_name)]

    if len(matchup_df) == 0:
        return {
            'batter': batter_name, 'bowler': bowler_name,
            'format': format, 'competition': competition,
            'total_balls': 0,
            'message': 'No deliveries found between these players in this scope.',
        }

    headline = _compute_stats(matchup_df)
    phase_splits = _phase_splits_by_format(matchup_df)
    competition_breakdown = _competition_split(matchup_df)
    matches_played = matchup_df['match_id'].nunique()

    return {
        'batter': batter_name, 'bowler': bowler_name,
        'format': format, 'competition': competition,
        'total_balls': headline['balls'],
        'total_runs': headline['runs'],
        'dismissals': headline['wickets'],
        'avg': headline['avg'],
        'sr': headline['sr'],
        'fours': headline['fours'],
        'sixes': headline['sixes'],
        'boundary_pct': headline['boundary_pct'],
        'dot_pct': headline['dot_pct'],
        'phase_splits_by_format': phase_splits,
        'competition_breakdown': competition_breakdown,
        'matches_played': int(matches_played),
    }


def analyze_batter_overall(batter_name: str,
                           format: Optional[str] = None,
                           competition: Optional[str] = None) -> Optional[dict]:
    """Batter's baseline across all bowlers in scope, with per-format phase splits."""
    df = _get_data()
    df = _apply_filters(df, format=format, competition=competition)
    batter_df = df[df['batter'] == batter_name]
    if len(batter_df) == 0:
        return None
    return {
        'batter': batter_name,
        'format': format, 'competition': competition,
        'overall': _compute_stats(batter_df),
        'phase_splits_by_format': _phase_splits_by_format(batter_df),
    }


def compare_matchup_to_baseline(batter_name: str, bowler_name: str,
                                format: Optional[str] = None,
                                competition: Optional[str] = None) -> dict:
    """Compare a matchup to the batter's baseline, with format-aware phase data."""
    matchup = analyze_matchup(batter_name, bowler_name,
                              format=format, competition=competition)
    baseline = analyze_batter_overall(batter_name,
                                      format=format, competition=competition)

    if matchup['total_balls'] == 0 or baseline is None:
        return {
            'batter': batter_name, 'bowler': bowler_name,
            'format': format, 'competition': competition,
            'message': 'Insufficient data for comparison.',
        }

    # Build phase comparison per format
    phases_by_format = {}
    m_splits = matchup['phase_splits_by_format']
    b_splits = baseline['phase_splits_by_format']
    for fmt, m_phases in m_splits.items():
        b_phases = b_splits.get(fmt, {})
        compared = {}
        for phase, m_stats in m_phases.items():
            b_stats = b_phases.get(phase, {'balls': 0})
            if m_stats['balls'] == 0:
                compared[phase] = {'matchup_balls': 0}
                continue
            compared[phase] = {
                'matchup_balls': m_stats['balls'],
                'baseline_balls': b_stats.get('balls', 0),
                'matchup_avg': m_stats.get('avg'),
                'baseline_avg': b_stats.get('avg'),
                'matchup_sr': m_stats.get('sr'),
                'baseline_sr': b_stats.get('sr'),
                'matchup_dot_pct': m_stats.get('dot_pct'),
                'baseline_dot_pct': b_stats.get('dot_pct'),
            }
        phases_by_format[fmt] = compared

    return {
        'batter': batter_name, 'bowler': bowler_name,
        'format': format, 'competition': competition,
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
        'phases_by_format': phases_by_format,
        'competition_breakdown': matchup['competition_breakdown'],
    }