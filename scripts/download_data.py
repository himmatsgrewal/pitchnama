"""
scripts/download_data.py — Download all Cricsheet datasets PitchNama uses.

Downloads and extracts every dataset listed in pitchnama.data_loader.CRICSHEET_DATASETS.
Skips downloads/extractions that are already done — safe to re-run.

Usage (from project root):
    python scripts/download_data.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pitchnama.data_loader import CRICSHEET_DATASETS, download_dataset


if __name__ == "__main__":
    print("=" * 60)
    print("PitchNama — Downloading Cricsheet datasets")
    print("=" * 60)

    for code in CRICSHEET_DATASETS:
        download_dataset(code, verbose=True)

    print()
    print("=" * 60)
    print("All datasets ready.")
    print("=" * 60)