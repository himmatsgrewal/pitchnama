"""
scripts/refresh_mirror.py — Refresh the data-mirror GitHub Release with the
latest Cricsheet zips.

Run this weekly (or whenever you want the robot to use fresher data) from
your local machine. It:
  1. Downloads fresh zips from Cricsheet (your IP can reach them; the
     robot's cloud IP cannot).
  2. Uploads them to the 'data-mirror' GitHub Release via the gh CLI.
The robot picks these up automatically on its next nightly run.

Requirements:
  - gh CLI installed and authenticated (`gh auth login` once)

Usage (from project root):
    python scripts/refresh_mirror.py
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pitchnama.data_loader import (
    CRICSHEET_DATASETS,
    DATA_ROOT,
    MIRROR_RELEASE_TAG,
    download_dataset,
)


def upload_to_release(zip_path: Path, label: str) -> None:
    """Upload one zip to the data-mirror release, replacing any existing asset."""
    result = subprocess.run(
        ['gh', 'release', 'upload', MIRROR_RELEASE_TAG, str(zip_path), '--clobber'],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  [{label}] upload FAILED:")
        print(result.stderr)
        sys.exit(1)
    print(f"  [{label}] uploaded {zip_path.name}")


if __name__ == "__main__":
    print("=" * 60)
    print("PitchNama — Refreshing data-mirror from Cricsheet")
    print("=" * 60)

    # Step 1: download fresh from Cricsheet (works on your local IP).
    print("\nStep 1/2: download from Cricsheet")
    print("-" * 60)
    for code in CRICSHEET_DATASETS:
        download_dataset(code, verbose=True, source='cricsheet')

    # Step 2: upload to the GitHub Release so the robot can read them.
    print("\nStep 2/2: upload to GitHub Release")
    print("-" * 60)
    for code, config in CRICSHEET_DATASETS.items():
        zip_path = Path(DATA_ROOT) / f"{code}_male_json.zip"
        if not zip_path.exists():
            print(f"  [{config['label']}] WARN: {zip_path.name} missing, skipping")
            continue
        upload_to_release(zip_path, config['label'])

    print()
    print("=" * 60)
    print("Mirror refreshed. The robot will pick it up on its next nightly run.")
    print("(Or trigger it manually via GitHub → Actions.)")
    print("=" * 60)