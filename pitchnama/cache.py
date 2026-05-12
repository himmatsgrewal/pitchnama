"""
cache.py — Fast ball-by-ball cache for PitchNama.

The raw Cricsheet JSON files take ~30 seconds to scan in full for every
analysis. That's fine for exploration, unbearable for a live web app.

This module solves it: parse all matches once into a single Parquet table,
then load that table instantly for every subsequent analysis. Same data,
1000× faster lookups.

Pipeline:
    Build (run once, or when new matches are added):
        Raw JSON files  →  parse  →  pandas DataFrame  →  save as Parquet

    Load (every analysis call):
        Parquet file  →  pandas DataFrame  (instant)

Parquet is the industry-standard binary columnar format for analytical
datasets. Used everywhere from CricViz to financial markets.
"""

import os
from pathlib import Path

import pandas as pd

from .data_loader import iter_matches, iter_deliveries


# Where the cache file lives. Same data/ folder as the raw JSONs.
CACHE_PATH = "data/ipl_deliveries.parquet"


def build_cache(output_path: str = CACHE_PATH, verbose: bool = True) -> pd.DataFrame:
    """
    Parse every IPL match file and save all deliveries to a single Parquet file.

    Each row of the output table represents one ball, with all the context
    (match, date, venue, batter, bowler, runs, wicket, phase) flattened.

    Args:
        output_path: Where to save the Parquet file.
        verbose: If True, print progress.

    Returns:
        The DataFrame that was saved.
    """
    rows = []
    match_count = 0

    if verbose:
        print("Building PitchNama cache from raw JSON files...")

    for filename, match_data in iter_matches():
        match_count += 1
        info = match_data['info']
        match_id = filename.replace('.json', '')
        match_date = info['dates'][0]
        match_season = str(info['season'])
        match_venue = info['venue']
        match_city = info.get('city', None)
        teams = info['teams']

        for delivery in iter_deliveries(match_data):
            rows.append({
                'match_id': match_id,
                'date': match_date,
                'season': match_season,
                'venue': match_venue,
                'city': match_city,
                'team_a': teams[0],
                'team_b': teams[1],
                'innings': delivery['innings_index'] + 1,
                'over': delivery['over'],
                'batter': delivery['batter'],
                'non_striker': delivery.get('non_striker'),
                'bowler': delivery['bowler'],
                'runs_batter': delivery['runs']['batter'],
                'runs_extras': delivery['runs']['extras'],
                'runs_total': delivery['runs']['total'],
                'wicket': 'wickets' in delivery,
            })

    df = pd.DataFrame(rows)

    # Ensure the data directory exists
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Save as Parquet
    df.to_parquet(output_path, index=False, engine='pyarrow', compression='snappy')

    if verbose:
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"  Parsed {match_count} matches → {len(df):,} deliveries")
        print(f"  Saved to {output_path} ({size_mb:.1f} MB)")

    return df


def load_cache(cache_path: str = CACHE_PATH) -> pd.DataFrame:
    """
    Load the cached ball-by-ball table from disk.

    Args:
        cache_path: Path to the Parquet cache file.

    Returns:
        A pandas DataFrame with one row per delivery.

    Raises:
        FileNotFoundError: If the cache doesn't exist. Run build_cache() first.
    """
    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"Cache not found at {cache_path}. "
            f"Run `python scripts/build_cache.py` first."
        )
    return pd.read_parquet(cache_path, engine='pyarrow')