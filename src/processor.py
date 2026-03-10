"""
Silver Layer processor: load raw (Bronze) JSON, normalize and flatten into DataFrames.

See SILVER_PROCESSOR_PLAN.md for the full implementation plan.
"""

from __future__ import annotations

import json
import warnings
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


def validate_goal_leaders_20242025(data: dict[str, Any]) -> None:
    """Validate that goal leaders data has Leon Draisaitl as top scorer with 52 goals (2024-25 regular season).

    Raises ValueError if the "goals" key is missing, empty, or if the top entry is not Draisaitl with 52.
    """
    goals = data.get("goals")
    if not goals or not isinstance(goals, list):
        raise ValueError(
            "Goal leaders JSON must contain a non-empty 'goals' list (regular-season goal leaders)."
        )
    sorted_goals = sorted(goals, key=lambda p: p.get("value", 0), reverse=True)
    top = sorted_goals[0]
    first = str(_get_default(top.get("firstName", ""))).strip()
    last = str(_get_default(top.get("lastName", ""))).strip()
    value = top.get("value")
    if first != "Leon" or last != "Draisaitl" or value != 52:
        raise ValueError(
            f"Expected top goal scorer for 2024-25 to be Leon Draisaitl with 52 goals; "
            f"got {first} {last} with {value} goals."
        )


def load_standings(path: Path | None = None) -> pd.DataFrame:
    """Load standings snapshot JSON into a flat DataFrame.

    Uses json_normalize on the standings array; flattens the nested `team`
    object so columns are team_id, team_name, team_abbreviation, etc., for
    joining with goal leaders on team_abbreviation.

    Points are recalculated from wins and OT losses for accuracy; the raw
    JSON 'points' value is not used. Formula: points = (wins * 2) + (ot_losses * 1).
    """
    path = path or STANDINGS_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    # One row per team; json_normalize flattens nested "team" to team.id, team.abbreviation, etc.
    df = pd.json_normalize(data, record_path="standings")

    # Rename team.* columns to team_* for consistent join key (team_abbreviation)
    df = df.rename(columns=lambda c: c.replace("team.", "team_", 1) if c.startswith("team.") else c)

    # Raw API uses teamAbbrev / teamName; json_normalize flattens to teamAbbrev.default, teamName.default
    if "team_abbreviation" not in df.columns:
        if "teamAbbrev" in df.columns:
            df["team_abbreviation"] = df["teamAbbrev"].apply(_get_default)
        elif "teamAbbrev.default" in df.columns:
            df["team_abbreviation"] = df["teamAbbrev.default"]
    if "team_name" not in df.columns:
        if "teamName" in df.columns:
            df["team_name"] = df["teamName"].apply(_get_default)
        elif "teamName.default" in df.columns:
            df["team_name"] = df["teamName.default"]

    # Normalize raw API camelCase to snake_case for silver/visualizer
    renames = {
        "gamesPlayed": "games_played",
        "leagueSequence": "league_rank",
        "goalFor": "goals_for",
        "goalAgainst": "goals_against",
        "goalDifferential": "goal_differential",
    }
    for old, new in renames.items():
        if old in df.columns and new not in df.columns:
            df[new] = df[old]

    # otLosses -> ot_losses (standings may be raw API or saved snapshot)
    if "otLosses" in df.columns and "ot_losses" not in df.columns:
        df["ot_losses"] = df["otLosses"].fillna(0).astype(int)

    # Recalculate points from wins and ot_losses; do not rely on raw JSON 'points'
    if "wins" in df.columns and "ot_losses" in df.columns:
        df["points"] = (df["wins"].fillna(0).astype(int) * 2) + (df["ot_losses"].fillna(0).astype(int) * 1)
    elif "wins" in df.columns and "otLosses" in df.columns:
        df["points"] = (df["wins"].fillna(0).astype(int) * 2) + (df["otLosses"].fillna(0).astype(int) * 1)

    return df


def load_goal_leaders(path: Path | None = None) -> pd.DataFrame:
    """Load goal leaders JSON into a flat DataFrame.

    Uses the "goals" list (regular-season goal leaders), not "goalsSh" (short-handed).
    Validates that the top scorer is Leon Draisaitl with 52 goals for 2024-25.
    Flattens firstName, lastName, and teamName from {"default": "…"} dicts into plain strings.
    """
    path = path or GOAL_LEADERS_PATH
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if "goals" in data and data["goals"]:
        validate_goal_leaders_20242025(data)
        records = data["goals"]
    elif "goalsSh" in data and data["goalsSh"]:
        warnings.warn(
            "Goal leaders file has only 'goalsSh' (short-handed); expected 'goals' for regular-season leaders. "
            "Re-fetch from the API to get correct data.",
            UserWarning,
            stacklevel=2,
        )
        records = data["goalsSh"]
    else:
        raise ValueError("Goal leaders JSON must contain a non-empty 'goals' or 'goalsSh' list.")

    df = pd.DataFrame(records)

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
