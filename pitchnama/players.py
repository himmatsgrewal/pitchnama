"""
players.py — Player name registry for PitchNama.

Builds and loads a registry of every player who appears in the dataset,
mapping their Cricsheet scorecard names (e.g. 'RG Sharma') to unique
person IDs (Cricsheet's registry).

Display names come from a curated JSON file (data/player_display_names.json)
that we maintain manually for the most prominent players. Anyone not in the
curated list gets a politely-formatted fallback (e.g. 'RG Sharma' → 'R. G. Sharma').

Pipeline:
    Build (run once after dataset changes):
        Match JSONs  →  extract (name, person_id) pairs  →  Parquet

    Load:
        Parquet  →  pandas DataFrame  →  used for display name lookups
"""

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .data_loader import CRICSHEET_DATASETS, DATA_ROOT, iter_matches


REGISTRY_PATH = "data/players.parquet"
DISPLAY_NAMES_PATH = "pitchnama/player_display_names.json"


def build_registry(output_path: str = REGISTRY_PATH, verbose: bool = True) -> pd.DataFrame:
    """
    Scan every dataset and build a unified player registry.

    For every match, Cricsheet's info section includes a 'registry.people'
    dict mapping scorecard names to unique person IDs. We aggregate this
    across all matches to produce one row per (name, person_id) pair, with
    counts of appearances.
    """
    seen = {}  # (scorecard_name, person_id) → match count

    if verbose:
        print("Building player registry...")

    for code in CRICSHEET_DATASETS:
        _, subfolder, label = CRICSHEET_DATASETS[code]
        folder = os.path.join(DATA_ROOT, subfolder)
        if not os.path.exists(folder):
            if verbose:
                print(f"  [{label}] folder missing, skipping")
            continue

        count_in_dataset = 0
        for _, match_data in iter_matches(folder):
            registry = match_data.get('info', {}).get('registry', {}).get('people', {})
            for name, person_id in registry.items():
                key = (name, person_id)
                seen[key] = seen.get(key, 0) + 1
                count_in_dataset += 1
        if verbose:
            print(f"  [{label}] processed")

    rows = [
        {'scorecard_name': name, 'person_id': pid, 'appearances': count}
        for (name, pid), count in seen.items()
    ]
    df = pd.DataFrame(rows)

    # Aggregate by person_id to get total appearances per person
    # (a person can have multiple scorecard name spellings across matches)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine='pyarrow', compression='snappy')

    if verbose:
        size_kb = os.path.getsize(output_path) / 1024
        print(f"\nTotal unique (name, person_id) pairs: {len(df):,}")
        print(f"Unique players:                       {df['person_id'].nunique():,}")
        print(f"Saved to:                             {output_path} ({size_kb:.1f} KB)")

    return df


def load_registry(registry_path: str = REGISTRY_PATH) -> pd.DataFrame:
    """Load the player registry from disk."""
    if not os.path.exists(registry_path):
        raise FileNotFoundError(
            f"Registry not found at {registry_path}. "
            f"Run `python scripts/build_registry.py` first."
        )
    return pd.read_parquet(registry_path, engine='pyarrow')


def load_display_names(path: str = DISPLAY_NAMES_PATH) -> dict:
    """Load the curated display-name overrides. Returns empty dict if file missing."""
    if not os.path.exists(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _polish_scorecard_name(name: str) -> str:
    """
    Fallback formatter: turn 'RG Sharma' into 'R. G. Sharma'.
    Adds dots and spaces to initials, leaves surnames alone.
    """
    parts = name.split(' ', 1)
    if len(parts) == 1:
        return name
    initials, rest = parts
    # If first chunk is all uppercase letters (typical initials block), expand it
    if initials.isupper() and len(initials) >= 2 and initials.isalpha():
        spaced = '. '.join(initials) + '.'
        return f"{spaced} {rest}"
    return name


def display_name(scorecard_name: str, overrides: Optional[dict] = None) -> str:
    """
    Convert a scorecard name to a display name.

    Lookup order:
      1. If curated overrides include this scorecard_name → use it
      2. Otherwise fall back to polished initials format

    Args:
        scorecard_name: e.g. 'RG Sharma'
        overrides: optional preloaded display-names dict (for performance)

    Returns:
        e.g. 'Rohit Sharma' if curated, 'R. G. Sharma' if fallback.
    """
    if overrides is None:
        overrides = load_display_names()
    if scorecard_name in overrides:
        return overrides[scorecard_name]
    return _polish_scorecard_name(scorecard_name)