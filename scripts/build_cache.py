"""
scripts/build_cache.py — Build/rebuild the PitchNama ball-by-ball cache.

Run this once after first downloading the data, and any time you add new
matches to data/ipl_json/. Output goes to data/ipl_deliveries.parquet.

Usage (from project root):
    python scripts/build_cache.py
"""

import sys
from pathlib import Path

# Add project root to Python's path so we can import the pitchnama package
# when running this script directly from the scripts/ folder.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pitchnama.cache import build_cache


if __name__ == "__main__":
    df = build_cache(verbose=True)
    print(f"\nDone. The cache has {len(df):,} rows across {df['match_id'].nunique()} matches.")
    print(f"Columns: {list(df.columns)}")