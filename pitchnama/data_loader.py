"""
data_loader.py — Functions for loading and downloading cricket match data.

PitchNama uses ball-by-ball data from Cricsheet (https://cricsheet.org/),
distributed under CC BY-SA 4.0. Cricsheet's bot filter periodically blocks
cloud IP ranges (e.g. GitHub Actions), so we mirror the zips on our own
repo's GitHub Release ('data-mirror'). The daily robot reads from the
mirror; only scripts/refresh_mirror.py (run locally) talks to Cricsheet.

This module handles:
  - Downloading and extracting dataset zips (from mirror by default;
    from Cricsheet only when explicitly requested)
  - Listing match files in a folder
  - Loading and iterating through parsed match data
"""

import json
import os
import zipfile
from pathlib import Path
from typing import Iterator, Literal, Tuple

import requests


# Where all raw match files live (under data/)
DATA_ROOT = "data"

# Our self-hosted mirror, a GitHub Release on this same repo.
GITHUB_OWNER = 'himmatsgrewal'
GITHUB_REPO = 'pitchnama'
MIRROR_RELEASE_TAG = 'data-mirror'

# Browser-like headers. Cricsheet rejects bare bot requests; GitHub Releases
# don't care, but sending these is harmless either way so we keep one set.
BROWSER_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/126.0.0.0 Safari/537.36'
    ),
    'Accept': (
        'text/html,application/xhtml+xml,application/xml;q=0.9,'
        'image/avif,image/webp,application/zip,application/octet-stream,*/*;q=0.8'
    ),
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Referer': 'https://cricsheet.org/downloads/',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
}

# Datasets we use, indexed by short code. Each entry holds:
#   cricsheet_url    — upstream source (only used by scripts/refresh_mirror.py)
#   mirror_filename  — asset filename on our data-mirror GitHub Release
#   subfolder        — extracted folder name under data/
#   label            — human-readable name for logs
CRICSHEET_DATASETS = {
    'ipl':  {'cricsheet_url': 'https://cricsheet.org/downloads/ipl_male_json.zip',
             'mirror_filename': 'ipl_male_json.zip',
             'subfolder': 'ipl_json',
             'label': 'IPL'},
    't20i': {'cricsheet_url': 'https://cricsheet.org/downloads/t20s_male_json.zip',
             'mirror_filename': 't20i_male_json.zip',
             'subfolder': 't20i_json',
             'label': "Men's T20Is"},
    'odi':  {'cricsheet_url': 'https://cricsheet.org/downloads/odis_male_json.zip',
             'mirror_filename': 'odi_male_json.zip',
             'subfolder': 'odi_json',
             'label': "Men's ODIs"},
    'test': {'cricsheet_url': 'https://cricsheet.org/downloads/tests_male_json.zip',
             'mirror_filename': 'test_male_json.zip',
             'subfolder': 'test_json',
             'label': "Men's Tests"},
    'bbl':  {'cricsheet_url': 'https://cricsheet.org/downloads/bbl_male_json.zip',
             'mirror_filename': 'bbl_male_json.zip',
             'subfolder': 'bbl_json',
             'label': 'Big Bash League'},
    'psl':  {'cricsheet_url': 'https://cricsheet.org/downloads/psl_male_json.zip',
             'mirror_filename': 'psl_male_json.zip',
             'subfolder': 'psl_json',
             'label': 'Pakistan Super League'},
    'cpl':  {'cricsheet_url': 'https://cricsheet.org/downloads/cpl_male_json.zip',
             'mirror_filename': 'cpl_male_json.zip',
             'subfolder': 'cpl_json',
             'label': 'Caribbean Premier League'},
}


def _mirror_url(filename: str) -> str:
    """Public download URL for a file on our data-mirror GitHub Release."""
    return (f'https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/'
            f'releases/download/{MIRROR_RELEASE_TAG}/{filename}')


# ---------- Download / extract ----------

def download_dataset(
    code: str,
    verbose: bool = True,
    force: bool = False,
    source: Literal['mirror', 'cricsheet'] = 'mirror',
) -> str:
    """
    Download and extract a dataset by short code (e.g. 'ipl', 't20i').

    By default downloads from our self-hosted GitHub Release mirror — what
    the daily robot uses. Pass source='cricsheet' to download direct from
    upstream (only sensible from a non-blocked IP; used by
    scripts/refresh_mirror.py to refresh the mirror).

    Uses HTTP If-Modified-Since to avoid re-downloading unchanged data.
    Re-extracts if the zip is newer than the existing JSON folder.

    Args:
        code: Dataset short code from CRICSHEET_DATASETS.
        verbose: If True, print progress.
        force: If True, re-download even if local file appears current.
        source: 'mirror' (default) or 'cricsheet'.

    Returns:
        The path to the extracted folder.
    """
    if code not in CRICSHEET_DATASETS:
        raise ValueError(f"Unknown dataset code: {code}. "
                         f"Available: {list(CRICSHEET_DATASETS.keys())}")

    config = CRICSHEET_DATASETS[code]
    label = config['label']
    subfolder = config['subfolder']

    if source == 'cricsheet':
        url = config['cricsheet_url']
    else:
        url = _mirror_url(config['mirror_filename'])

    # Local zip uses the short-code name so the file path is the same
    # regardless of which source we downloaded from.
    zip_path = os.path.join(DATA_ROOT, f"{code}_male_json.zip")
    extract_path = os.path.join(DATA_ROOT, subfolder)

    Path(DATA_ROOT).mkdir(parents=True, exist_ok=True)

    headers = dict(BROWSER_HEADERS)
    if os.path.exists(zip_path) and not force:
        # Tell the server "only send if newer than my local copy".
        local_mtime = os.path.getmtime(zip_path)
        from email.utils import formatdate
        headers['If-Modified-Since'] = formatdate(local_mtime, usegmt=True)

    if verbose:
        action = "Force-downloading" if force else "Checking"
        print(f"  [{label}] {action} {url}...")

    response = requests.get(url, headers=headers, stream=True)

    if response.status_code == 304:
        if verbose:
            print(f"  [{label}] up to date, skipping download")
    elif response.status_code == 200:
        content = response.content
        if content[:2] != b'PK':
            raise RuntimeError(
                f"Download for {label} did not return a valid zip. "
                f"First bytes: {content[:50]}"
            )
        with open(zip_path, 'wb') as f:
            f.write(content)
        if verbose:
            size_mb = len(content) / (1024 * 1024)
            print(f"  [{label}] downloaded fresh zip ({size_mb:.2f} MB)")
    else:
        raise RuntimeError(
            f"Download failed for {label}. Status: {response.status_code}"
        )

    # Decide whether to re-extract
    needs_extract = True
    if os.path.exists(extract_path):
        existing = [f for f in os.listdir(extract_path) if f.endswith('.json')]
        if existing:
            zip_mtime = os.path.getmtime(zip_path)
            folder_mtime = os.path.getmtime(extract_path)
            if zip_mtime <= folder_mtime and not force:
                needs_extract = False
                if verbose:
                    print(f"  [{label}] extracted folder is up to date "
                          f"({len(existing)} files)")

    if needs_extract:
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