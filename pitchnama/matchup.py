"""
matchup.py — Cricket matchup analytics.

Core analysis functions for PitchNama. Given a batter and bowler, computes
head-to-head stats with phase-aware splits and contextualizes them against
the batter's career baseline.

Phase definitions (T20, 0-indexed overs):
    Powerplay: overs 0-5    (overs 1-6 in human terms)
    Middle:    overs 6-14   (overs 7-15 in human terms)
    Death:     overs 15-19  (overs 16-20 in human terms)
"""

from typing import Optional
from .data_loader import iter_matches, iter_deliveries


# ---------- Helpers ----------

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


# ---------- Ball collection ----------

def find_matchup_balls(batter_name: str, bowler_name: str) -> list[dict]:
    """
    Scan every IPL match file and return every ball where the given
    bowler delivered to the given batter.

    Args:
        batter_name: Cricket-scorecard format (e.g. 'RG Sharma').
        bowler_name: Cricket-scorecard format (e.g. 'PJ Cummins').

    Returns:
        A list of ball dictionaries, each with match context attached.
    """
    balls = []

    for filename, match_data in iter_matches():
        info = match_data['info']
        match_date = info['dates'][0]
        match_season = info['season']
        match_venue = info['venue']

        for delivery in iter_deliveries(match_data):
            if (delivery['bowler'] == bowler_name
                    and delivery['batter'] == batter_name):
                balls.append({
                    'match_id': filename.replace('.json', ''),
                    'date': match_date,
                    'season': match_season,
                    'venue': match_venue,
                    'innings': delivery['innings_index'] + 1,
                    'over': delivery['over'],
                    'runs_batter': delivery['runs']['batter'],
                    'runs_extras': delivery['runs']['extras'],
                    'runs_total': delivery['runs']['total'],
                    'wicket': 'wickets' in delivery,
                })

    return balls


def find_batter_balls(batter_name: str) -> list[dict]:
    """
    Scan every IPL match file and return every ball this batter faced
    (regardless of bowler). Used for computing career baselines.
    """
    balls = []

    for _, match_data in iter_matches():
        for delivery in iter_deliveries(match_data):
            if delivery['batter'] == batter_name:
                balls.append({
                    'over': delivery['over'],
                    'runs_batter': delivery['runs']['batter'],
                    'runs_extras': delivery['runs']['extras'],
                    'wicket': 'wickets' in delivery,
                })

    return balls


# ---------- Stat computation ----------

def _compute_stats(balls: list[dict]) -> dict:
    """
    Given a list of ball dicts, compute headline cricket stats.

    Returns a dictionary of: balls, runs, wickets, avg, sr, dot_pct,
    fours, sixes, boundary_pct.
    """
    n = len(balls)
    if n == 0:
        return {'balls': 0}

    runs = sum(b['runs_batter'] for b in balls)
    wickets = sum(1 for b in balls if b['wicket'])
    dots = sum(1 for b in balls if b['runs_batter'] == 0 and b['runs_extras'] == 0)
    fours = sum(1 for b in balls if b['runs_batter'] == 4)
    sixes = sum(1 for b in balls if b['runs_batter'] == 6)

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


def _phase_split(balls: list[dict]) -> dict:
    """Split a list of balls into Powerplay/Middle/Death buckets and compute stats per bucket."""
    phases = {'Powerplay': [], 'Middle': [], 'Death': []}
    for b in balls:
        phases[get_phase(b['over'])].append(b)

    return {phase: _compute_stats(balls) for phase, balls in phases.items()}


# ---------- Public API ----------

def analyze_matchup(batter_name: str, bowler_name: str) -> dict:
    """
    Full matchup analysis between a batter and a bowler.

    Returns a dictionary containing:
      - The two player names
      - Headline stats (balls, runs, wickets, avg, sr, etc.)
      - Phase breakdown (powerplay/middle/death)
      - Number of distinct matches the matchup occurred in

    If no balls exist between the pair, returns a minimal dict with
    'total_balls': 0 and an explanatory message.
    """
    balls = find_matchup_balls(batter_name, bowler_name)

    if not balls:
        return {
            'batter': batter_name,
            'bowler': bowler_name,
            'total_balls': 0,
            'message': 'No deliveries found between these players in our dataset.',
        }

    headline = _compute_stats(balls)
    phase_breakdown = _phase_split(balls)
    matches_played = len({b['match_id'] for b in balls})

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
        'matches_played': matches_played,
    }


def analyze_batter_overall(batter_name: str) -> Optional[dict]:
    """
    Compute a batter's career IPL baseline across all bowlers.

    Used to contextualize matchup numbers against career norms.

    Returns None if the batter has no balls in our dataset.
    """
    balls = find_batter_balls(batter_name)

    if not balls:
        return None

    return {
        'batter': batter_name,
        'overall': _compute_stats(balls),
        'phase_stats': _phase_split(balls),
    }


def compare_matchup_to_baseline(batter_name: str, bowler_name: str) -> dict:
    """
    Compare a specific matchup to the batter's career baseline.

    Returns a structured dictionary suitable for rendering as a side-by-side
    comparison table or feeding into a scout report templater.
    """
    matchup = analyze_matchup(batter_name, bowler_name)
    baseline = analyze_batter_overall(batter_name)

    if matchup['total_balls'] == 0 or baseline is None:
        return {
            'batter': batter_name,
            'bowler': bowler_name,
            'message': 'Insufficient data for comparison.',
        }

    # Phase-by-phase comparison
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