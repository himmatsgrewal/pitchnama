"""
cache.py — Fast ball-by-ball cache for PitchNama.

Builds a unified Parquet table containing every ball from every Cricsheet
dataset PitchNama supports (IPL, T20Is, ODIs, Tests, BBL, PSL, CPL, ...).

The cache file lives at data/deliveries.parquet and is read instantly
(~50 ms) by all analysis code. The raw JSON files are parsed exactly once
per build.

The `wicket` column counts ONLY bowler-credited dismissals (bowled, caught,
lbw, stumped, caught & bowled, hit wicket). Run-outs and other non-bowler
dismissals are NOT counted, since they are not credited to the bowler.
"""

import os
from pathlib import Path

import pandas as pd

from .data_loader import (
    CRICSHEET_DATASETS,
    DATA_ROOT,
    iter_matches,
    iter_deliveries,
)


# Where the unified cache lives.
CACHE_PATH = "data/deliveries.parquet"


# T20 / ODI / Test classification, derived from dataset code.
FORMAT_BY_CODE = {
    'ipl':  'T20',
    't20i': 'T20',
    'bbl':  'T20',
    'psl':  'T20',
    'cpl':  'T20',
    'odi':  'ODI',
    'test': 'Test',
}


# Dismissal kinds credited to the bowler. Everything else (run out, retired
# hurt, obstructing the field, etc.) is NOT the bowler's wicket.
BOWLER_CREDITED_DISMISSALS = {
    'bowled', 'caught', 'lbw', 'stumped', 'caught and bowled', 'hit wicket',
}


def _is_bowler_wicket(delivery: dict) -> bool:
    """True only if a wicket fell AND it is credited to the bowler."""
    if 'wickets' not in delivery:
        return False
    for w in delivery['wickets']:
        if w.get('kind', '').lower() in BOWLER_CREDITED_DISMISSALS:
            return True
    return False


def _parse_dataset(code: str, verbose: bool = True) -> list[dict]:
    """Parse a single Cricsheet dataset folder into a list of ball dicts."""
    config = CRICSHEET_DATASETS[code]
    subfolder = config['subfolder']
    label = config['label']
    folder = os.path.join(DATA_ROOT, subfolder)

    if not os.path.exists(folder):
        if verbose:
            print(f"  [{label}] folder missing, skipping. "
                  f"Run scripts/download_data.py first.")
        return []

    competition_format = FORMAT_BY_CODE[code]
    rows = []
    match_count = 0

    for filename, match_data in iter_matches(folder):
        match_count += 1
        info = match_data['info']
        match_id = filename.replace('.json', '')
        match_date = info['dates'][0]
        match_season = str(info.get('season', ''))
        match_venue = info.get('venue', None)
        match_city = info.get('city', None)
        teams = info.get('teams', [None, None])

        for delivery in iter_deliveries(match_data):
            rows.append({
                'competition': code,
                'format': competition_format,
                'match_id': match_id,
                'date': match_date,
                'season': match_season,
                'venue': match_venue,
                'city': match_city,
                'team_a': teams[0] if len(teams) > 0 else None,
                'team_b': teams[1] if len(teams) > 1 else None,
                'innings': delivery['innings_index'] + 1,
                'over': delivery['over'],
                'batter': delivery['batter'],
                'non_striker': delivery.get('non_striker'),
                'bowler': delivery['bowler'],
                'runs_batter': delivery['runs']['batter'],
                'runs_extras': delivery['runs']['extras'],
                'runs_total': delivery['runs']['total'],
                'wicket': _is_bowler_wicket(delivery),
            })

    if verbose:
        print(f"  [{label}] parsed {match_count} matches → {len(rows):,} deliveries")

    return rows


def build_cache(output_path: str = CACHE_PATH, verbose: bool = True) -> pd.DataFrame:
    """
    Parse every Cricsheet dataset and save all deliveries to a unified
    Parquet file.
    """
    if verbose:
        print("Building unified PitchNama cache...")

    all_rows = []
    for code in CRICSHEET_DATASETS:
        all_rows.extend(_parse_dataset(code, verbose=verbose))

    df = pd.DataFrame(all_rows)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine='pyarrow', compression='snappy')

    if verbose:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print()
        print(f"Total deliveries: {len(df):,}")
        print(f"Total matches:    {df['match_id'].nunique():,}")
        print(f"Saved to:         {output_path} ({size_mb:.2f} MB)")
        print()
        print("Per-competition breakdown:")
        breakdown = df.groupby('competition').agg(
            matches=('match_id', 'nunique'),
            deliveries=('match_id', 'size'),
        ).sort_values('deliveries', ascending=False)
        print(breakdown.to_string())

    return df


def load_cache(cache_path: str = CACHE_PATH) -> pd.DataFrame:
    """
    Load the cached deliveries DataFrame from disk.
    Raises FileNotFoundError if the cache doesn't exist. Run build_cache first.
    """
    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"Cache not found at {cache_path}. "
            f"Run `python scripts/build_cache.py` first."
        )
    return pd.read_parquet(cache_path, engine='pyarrow')