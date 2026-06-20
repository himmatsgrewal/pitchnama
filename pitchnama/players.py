"""
players.py — Player name registry for PitchNama.

Builds and loads a registry of every player in the dataset, enriched with
full names and countries from Cricsheet/Cricinfo metadata (player_meta.csv,
exported once from the cricketdata R package).

Display name priority:
    1. Curated override (pitchnama/player_display_names.json) — always wins
    2. Derived clean name from full_name ("Rohit Gurunath Sharma" -> "Rohit Sharma")
    3. Polished scorecard fallback ("RG Sharma" -> "R. G. Sharma")

The registry stores, per player:
    scorecard_name, person_id, appearances, full_name, display_name, country

NOTE: This module only builds the *registry* (players.parquet). It never
touches deliveries.parquet — match data and stats are unaffected.
"""

import json
import os
from pathlib import Path
from typing import Optional

import pandas as pd

from .data_loader import CRICSHEET_DATASETS, DATA_ROOT, iter_matches


REGISTRY_PATH = "data/players.parquet"
DISPLAY_NAMES_PATH = "pitchnama/player_display_names.json"
PLAYER_META_PATH = "data/player_meta.csv"


# ---------- Display-name helpers ----------

def load_display_names(path: str = DISPLAY_NAMES_PATH) -> dict:
    """Load curated display-name overrides. Skips the _comment key. Empty dict if missing."""
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _polish_scorecard_name(name: str) -> str:
    """Fallback: 'RG Sharma' -> 'R. G. Sharma'. Leaves single-token names alone."""
    parts = name.split(' ', 1)
    if len(parts) == 1:
        return name
    initials, rest = parts
    if initials.isupper() and len(initials) >= 2 and initials.isalpha():
        spaced = '. '.join(initials) + '.'
        return f"{spaced} {rest}"
    return name


def derive_display_name(full_name: str) -> str:
    """
    Turn a full legal name into a common 'First Last' display name.
      - 1-2 words: return as-is
      - 3+ words: first word + last word
    """
    if not isinstance(full_name, str):
        return ""
    cleaned = full_name.strip().lstrip("-").strip()
    parts = cleaned.split()
    if len(parts) <= 2:
        return cleaned
    return f"{parts[0]} {parts[-1]}"


def resolve_display_name(scorecard_name: str,
                         full_name: Optional[str],
                         overrides: dict) -> str:
    """Apply the display-name priority: curated -> derived -> polished fallback."""
    if scorecard_name in overrides:
        return overrides[scorecard_name]
    if isinstance(full_name, str) and full_name.strip() and full_name.strip().lower() != "nan":
        return derive_display_name(full_name)
    return _polish_scorecard_name(scorecard_name)


# ---------- Registry build ----------

def build_registry(output_path: str = REGISTRY_PATH, verbose: bool = True) -> pd.DataFrame:
    """
    Scan every dataset, build the player registry, and enrich with full names
    and countries from player_meta.csv. Writes players.parquet.
    """
    seen = {}  # (scorecard_name, person_id) -> appearance count

    if verbose:
        print("Building player registry...")

    for code in CRICSHEET_DATASETS:
        config = CRICSHEET_DATASETS[code]
        subfolder = config['subfolder']
        label = config['label']
        folder = os.path.join(DATA_ROOT, subfolder)
        if not os.path.exists(folder):
            if verbose:
                print(f"  [{label}] folder missing, skipping")
            continue
        for _, match_data in iter_matches(folder):
            registry = match_data.get('info', {}).get('registry', {}).get('people', {})
            for name, person_id in registry.items():
                key = (name, person_id)
                seen[key] = seen.get(key, 0) + 1
        if verbose:
            print(f"  [{label}] processed")

    rows = [
        {'scorecard_name': name, 'person_id': pid, 'appearances': count}
        for (name, pid), count in seen.items()
    ]
    df = pd.DataFrame(rows)

    # --- Enrich with full_name + country from player_meta.csv ---
    full_name_map = {}
    country_map = {}
    if os.path.exists(PLAYER_META_PATH):
        meta = pd.read_csv(PLAYER_META_PATH)
        meta['full_name'] = meta['full_name'].astype(str).str.strip()
        full_name_map = dict(zip(meta['cricsheet_id'], meta['full_name']))
        country_map = dict(zip(meta['cricsheet_id'], meta['country']))
        if verbose:
            print(f"  Loaded metadata for {len(meta):,} players from {PLAYER_META_PATH}")
    else:
        if verbose:
            print(f"  WARNING: {PLAYER_META_PATH} not found — names will use fallback only.")

    overrides = load_display_names()

    df['full_name'] = df['person_id'].map(full_name_map)
    df['country'] = df['person_id'].map(country_map)
    df['display_name'] = df.apply(
        lambda r: resolve_display_name(r['scorecard_name'], r['full_name'], overrides),
        axis=1,
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False, engine='pyarrow', compression='snappy')

    if verbose:
        n_full = df['full_name'].notna().sum()
        n_curated = df['scorecard_name'].isin(overrides).sum()
        print(f"\nTotal (name, id) pairs: {len(df):,}")
        print(f"Unique players:         {df['person_id'].nunique():,}")
        print(f"  With full name:       {n_full:,}")
        print(f"  Curated overrides:    {n_curated:,}")
        print(f"Saved to: {output_path}")

    return df


def load_registry(registry_path: str = REGISTRY_PATH) -> pd.DataFrame:
    """Load the player registry from disk."""
    if not os.path.exists(registry_path):
        raise FileNotFoundError(
            f"Registry not found at {registry_path}. "
            f"Run `python scripts/build_registry.py` first."
        )
    return pd.read_parquet(registry_path, engine='pyarrow')


def display_name(scorecard_name: str, overrides: Optional[dict] = None) -> str:
    """
    Resolve a display name for a scorecard name (used by older callers like
    scout_report). Looks up the prebuilt registry's display_name if available,
    else falls back to override-or-polish.
    """
    if overrides is None:
        overrides = load_display_names()
    if scorecard_name in overrides:
        return overrides[scorecard_name]
    # Try the registry's prebuilt display name
    try:
        reg = load_registry()
        match = reg[reg['scorecard_name'] == scorecard_name]
        if len(match) > 0 and 'display_name' in reg.columns:
            return match.iloc[0]['display_name']
    except Exception:
        pass
    return _polish_scorecard_name(scorecard_name)