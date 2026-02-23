"""
Silver Layer processor: load raw (Bronze) JSON, normalize and flatten into DataFrames.

See SILVER_PROCESSOR_PLAN.md for the full implementation plan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

# Same repo root as extractor (parent of src/)
_BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = _BASE_DIR / "data" / "raw"
SILVER_DATA_DIR = _BASE_DIR / "data" / "silver"

STANDINGS_PATH = RAW_DATA_DIR / "standings_20242025_snapshot.json"
GOAL_LEADERS_PATH = RAW_DATA_DIR / "goal_leaders_20242025.json"
SILVER_PLAYER_STATS_PATH = SILVER_DATA_DIR / "silver_player_stats.csv"


def _get_default(value: Any) -> Any:
    """Unwrap NHL API localization objects that use a nested `default` key.

    Many fields (e.g. firstName, lastName, teamName in goal leaders) look like:
        {"default": "Some Value", "fr": "...", ...}
    Returns the `default` value when present, otherwise the input.
    """
    if isinstance(value, dict) and "default" in value:
        return value["default"]
    return value


def load_standings(path: Path | None = None) -> pd.DataFrame:
    """Load standings snapshot JSON into a flat DataFrame.

    Uses json_normalize on the standings array; flattens the nested `team`
    object so columns are team_id, team_name, team_abbreviation, etc., for
    joining with goal leaders on team_abbreviation.
    """
    path = path or STANDINGS_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    # One row per team; json_normalize flattens nested "team" to team.id, team.abbreviation, etc.
    df = pd.json_normalize(data, record_path="standings")

    # Rename team.* columns to team_* for consistent join key (team_abbreviation)
    df = df.rename(columns=lambda c: c.replace("team.", "team_", 1) if c.startswith("team.") else c)

    return df


def load_goal_leaders(path: Path | None = None) -> pd.DataFrame:
    """Load goal leaders JSON into a flat DataFrame.

    Builds a DataFrame from the goalsSh list; flattens firstName, lastName,
    and teamName from {"default": "…"} dicts into plain strings.
    """
    path = path or GOAL_LEADERS_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    df = pd.DataFrame(data["goalsSh"])

    for col in ("firstName", "lastName", "teamName"):
        if col in df.columns:
            df[col] = df[col].apply(_get_default)

    return df


if __name__ == "__main__":
    SILVER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    standings = load_standings()
    goal_leaders = load_goal_leaders()

    silver = goal_leaders.merge(
        standings,
        left_on="teamAbbrev",
        right_on="team_abbreviation",
        how="left",
    )
    silver.to_csv(SILVER_PLAYER_STATS_PATH, index=False)
