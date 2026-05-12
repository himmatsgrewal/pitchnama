"""
data_loader.py — Functions for loading and downloading cricket match data.

PitchNama uses ball-by-ball data from Cricsheet (https://cricsheet.org/),
distributed under CC BY-SA 4.0. This module handles:
  - Downloading and extracting Cricsheet ZIPs for any competition
  - Listing match files in a folder
  - Loading and iterating through parsed match data
"""

import json
import os
import zipfile
from pathlib import Path
from typing import Iterator, Tuple

import requests


# Where all raw match files live (under data/)
DATA_ROOT = "data"

# Cricsheet datasets we use, indexed by short code.
# Each entry: (Cricsheet zip URL, subfolder name under data/, human-readable label)
CRICSHEET_DATASETS = {
    'ipl':   ('https://cricsheet.org/downloads/ipl_male_json.zip',     'ipl_json',    'IPL'),
    't20i':  ('https://cricsheet.org/downloads/t20s_male_json.zip',    't20i_json',   "Men's T20Is"),
    'odi':   ('https://cricsheet.org/downloads/odis_male_json.zip',    'odi_json',    "Men's ODIs"),
    'test':  ('https://cricsheet.org/downloads/tests_male_json.zip',   'test_json',   "Men's Tests"),
    'bbl':   ('https://cricsheet.org/downloads/bbl_male_json.zip',     'bbl_json',    'Big Bash League'),
    'psl':   ('https://cricsheet.org/downloads/psl_male_json.zip',     'psl_json',    'Pakistan Super League'),
    'cpl':   ('https://cricsheet.org/downloads/cpl_male_json.zip',     'cpl_json',    'Caribbean Premier League'),
}


# ---------- Download / extract ----------

def download_dataset(code: str, verbose: bool = True) -> str:
    """
    Download and extract a Cricsheet dataset by short code (e.g. 'ipl', 't20i').

    Skips download if the zip already exists. Skips extraction if the folder
    already has match files in it.

    Args:
        code: Dataset short code from CRICSHEET_DATASETS.
        verbose: If True, print progress.

    Returns:
        The path to the extracted folder.
    """
    if code not in CRICSHEET_DATASETS:
        raise ValueError(f"Unknown dataset code: {code}. "
                         f"Available: {list(CRICSHEET_DATASETS.keys())}")

    url, subfolder, label = CRICSHEET_DATASETS[code]
    zip_path = os.path.join(DATA_ROOT, f"{code}_male_json.zip")
    extract_path = os.path.join(DATA_ROOT, subfolder)

    # Ensure the data directory exists
    Path(DATA_ROOT).mkdir(parents=True, exist_ok=True)

    # Skip download if zip already exists
    if os.path.exists(zip_path):
        if verbose:
            print(f"  [{label}] zip already downloaded")
    else:
        if verbose:
            print(f"  [{label}] downloading from {url}...")
        response = requests.get(url)
        if response.status_code != 200 or response.content[:2] != b'PK':
            raise RuntimeError(
                f"Download failed for {label}. Status: {response.status_code}, "
                f"First bytes: {response.content[:50]}"
            )
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        if verbose:
            size_mb = len(response.content) / (1024 * 1024)
            print(f"  [{label}] saved zip ({size_mb:.2f} MB)")

    # Skip extraction if folder already has JSON files
    if os.path.exists(extract_path):
        existing = [f for f in os.listdir(extract_path) if f.endswith('.json')]
        if existing:
            if verbose:
                print(f"  [{label}] already extracted ({len(existing)} files)")
            return extract_path

    # Extract
    Path(extract_path).mkdir(parents=True, exist_ok=True)
    if verbose:
        print(f"  [{label}] extracting...")
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_path)

    if verbose:
        n = len([f for f in os.listdir(extract_path) if f.endswith('.json')])
        print(f"  [{label}] extracted {n} match files")

    return extract_path


# ---------- Iteration ----------

def list_match_files(folder: str) -> list[str]:
    """Return a list of all JSON match files in the given folder."""
    return [f for f in os.listdir(folder) if f.endswith('.json')]


def load_match(file_path: str) -> dict:
    """Load a single match JSON file and return its parsed contents."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_matches(folder: str) -> Iterator[Tuple[str, dict]]:
    """
    Yield (filename, match_data) for every match in the folder.
    Use when scanning all matches without loading them into memory at once.
    """
    for filename in list_match_files(folder):
        file_path = os.path.join(folder, filename)
        yield filename, load_match(file_path)


def iter_deliveries(match_data: dict) -> Iterator[dict]:
    """
    Yield every delivery from a match, with over and innings_index attached.
    """
    for innings_index, innings in enumerate(match_data['innings']):
        for over in innings['overs']:
            for delivery in over['deliveries']:
                yield {
                    **delivery,
                    'over': over['over'],
                    'innings_index': innings_index,
                }