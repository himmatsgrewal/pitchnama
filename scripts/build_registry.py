"""
scripts/build_registry.py — Build the PitchNama player registry.

Usage (from project root):
    python scripts/build_registry.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pitchnama.players import build_registry


if __name__ == "__main__":
    df = build_registry(verbose=True)