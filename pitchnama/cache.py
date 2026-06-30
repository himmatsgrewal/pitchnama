"""
cache.py — Fast ball-by-ball cache for PitchNama.

Builds a unified Parquet table containing every ball from every Cricsheet
dataset PitchNama supports (IPL, T20Is, ODIs, Tests, BBL, PSL, CPL, ...).

The cache file lives at data/deliveries.parquet. Analysis code queries it
on demand via DuckDB, which reads only the rows it needs straight from disk
(low, flat memory) instead of loading all ~4.4M rows into RAM.

The `wicket` column counts ONLY bowler-credited dismissals (bowled, caught,
lbw, stumped, caught & bowled, hit wicket). Run-outs and other non-bowler
dismissals are NOT counted, since they are not credited to the bowler.
"""

import os
import threading
from functools import lru_cache
from pathlib import Path
from typing import Optional

import duckdb
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
    Load the entire cached deliveries DataFrame from disk into memory.

    Kept for tooling/scripts that genuinely want the whole table. The live
    analysis path no longer calls this; it uses query_deliveries() instead,
    which reads only the rows it needs.

    Raises FileNotFoundError if the cache doesn't exist. Run build_cache first.
    """
    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"Cache not found at {cache_path}. "
            f"Run `python scripts/build_cache.py` first."
        )
    return pd.read_parquet(cache_path, engine='pyarrow')


# ---------- DuckDB-backed querying (low, flat memory) ----------

# One process-wide DuckDB connection, created once. DuckDB reads the parquet
# directly from disk per query; it does NOT hold the whole table in RAM, so the
# connection itself is tiny.
#
# IMPORTANT (thread safety): FastAPI handles each request on its own worker
# thread, so several queries can run at once. A single DuckDB connection object
# must NOT be used by multiple threads simultaneously — doing so corrupts its
# internal state and raises errors. The safe, DuckDB-recommended pattern is to
# keep ONE shared connection and call .cursor() on it per query; each cursor is
# an independent, thread-safe execution context over the same database.
_con: Optional["duckdb.DuckDBPyConnection"] = None
_con_lock = threading.Lock()


def _get_connection() -> "duckdb.DuckDBPyConnection":
    """Return the shared in-process DuckDB connection, creating it once."""
    global _con
    if _con is None:
        with _con_lock:
            if _con is None:
                _con = duckdb.connect(database=':memory:')
    return _con


def _cursor() -> "duckdb.DuckDBPyConnection":
    """
    Return a fresh cursor over the shared connection. Each request thread gets
    its own cursor, which is the thread-safe unit of execution in DuckDB.
    """
    return _get_connection().cursor()


def query_deliveries(
    cache_path: str = CACHE_PATH,
    batter: Optional[str] = None,
    bowler: Optional[str] = None,
    format: Optional[str] = None,
    competition: Optional[str] = None,
) -> pd.DataFrame:
    """
    Read just the deliveries matching the given filters, straight from the
    parquet on disk, and return them as a pandas DataFrame.

    This is the memory-saving heart of the refactor: instead of loading all
    ~4.4M rows, DuckDB scans the parquet and returns only the (usually small)
    set of rows for one batter / matchup / scope. Every downstream calculation
    in matchup.py then runs on this small frame exactly as before — pandas
    still does all the maths, so the numbers are unchanged.

    The returned DataFrame has the same columns and dtypes the old
    pd.read_parquet path produced, so calling code does not change.
    """
    if not os.path.exists(cache_path):
        raise FileNotFoundError(
            f"Cache not found at {cache_path}. "
            f"Run `python scripts/build_cache.py` first."
        )

    con = _cursor()

    clauses = []
    params: list = []
    if batter is not None:
        clauses.append("batter = ?")
        params.append(batter)
    if bowler is not None:
        clauses.append("bowler = ?")
        params.append(bowler)
    if format is not None:
        clauses.append('"format" = ?')
        params.append(format)
    if competition is not None:
        clauses.append("competition = ?")
        params.append(competition)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM read_parquet(?){where}"

    result = con.execute(sql, [cache_path, *params]).fetch_df()

    # Defensive: some DuckDB/pandas version combinations return None instead of
    # an empty DataFrame when a query matches zero rows. Downstream code expects
    # a DataFrame in every case (it calls len(...) and selects columns), so
    # normalise None to a correctly-shaped empty DataFrame with the right columns.
    if result is None:
        cols = _get_columns(cache_path)
        return pd.DataFrame(columns=cols)

    return result


@lru_cache(maxsize=1)
def _get_columns(cache_path: str = CACHE_PATH) -> tuple:
    """
    Return the parquet's column names (cached). Used to build a correctly-shaped
    empty DataFrame when a query matches no rows, so downstream column access
    behaves exactly as it did with the old full-load path.
    """
    con = _cursor()
    info = con.execute(
        "SELECT * FROM read_parquet(?) LIMIT 0", [cache_path]
    ).fetch_df()
    return tuple(info.columns)