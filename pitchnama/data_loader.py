"""
data_loader.py — Functions for loading and indexing IPL match data.

PitchNama uses ball-by-ball data from Cricsheet (https://cricsheet.org/),
distributed under CC BY-SA 4.0. This module handles reading the JSON files
into Python objects ready for analysis.
"""

import json
import os
from typing import Iterator, Tuple


# Default folder where IPL match files live (relative to project root)
DEFAULT_IPL_FOLDER = "data/ipl_json"


def list_match_files(folder: str = DEFAULT_IPL_FOLDER) -> list[str]:
    """
    Return a list of all JSON match files in the given folder.

    Args:
        folder: Path to the folder containing match JSON files.
                Defaults to 'data/ipl_json'.

    Returns:
        A list of filenames (e.g. ['1082591.json', '1082592.json', ...]),
        excluding non-JSON files like README.txt.
    """
    return [f for f in os.listdir(folder) if f.endswith('.json')]


def load_match(file_path: str) -> dict:
    """
    Load a single match JSON file and return its parsed contents.

    Args:
        file_path: Full path to the match JSON file.

    Returns:
        The match data as a dictionary with keys 'meta', 'info', 'innings'.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def iter_matches(folder: str = DEFAULT_IPL_FOLDER) -> Iterator[Tuple[str, dict]]:
    """
    Generator that yields (filename, match_data) for every match in the folder.

    Use this when scanning all matches without loading them all into memory at once.

    Args:
        folder: Path to the folder containing match JSON files.

    Yields:
        Tuples of (filename, parsed match data).
    """
    for filename in list_match_files(folder):
        file_path = os.path.join(folder, filename)
        yield filename, load_match(file_path)


def iter_deliveries(match_data: dict) -> Iterator[dict]:
    """
    Generator that yields every delivery (ball) from a match, with context.

    Each yielded dictionary includes the original delivery data plus:
      - 'over': the over number (0-indexed in T20s, 0-19)
      - 'innings_index': which innings (0 or 1)

    Args:
        match_data: A parsed match JSON object.

    Yields:
        Dictionaries representing individual deliveries with added context.
    """
    for innings_index, innings in enumerate(match_data['innings']):
        for over in innings['overs']:
            for delivery in over['deliveries']:
                yield {
                    **delivery,
                    'over': over['over'],
                    'innings_index': innings_index,
                }