from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Dict, List

import httpx

from .models import Record, StandingsSnapshot, Team, TeamStandings


# Fixed endpoint for the final day of the 2024–2025 regular season
STANDINGS_URL = "https://api-web.nhle.com/v1/standings/2025-04-16"

# Project-relative data directory (…/nhl-analytics/data/raw)
_BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = _BASE_DIR / "data" / "raw"


def _get_default(value: Any) -> Any:
    """Unwrap NHL API localization objects that use a nested `default` key.

    Many fields in the standings payload can look like:
        {"default": "Some Value", "fr": "...", ...}
    This helper returns the `default` value when present, otherwise the input.
    """
    if isinstance(value, dict) and "default" in value:
        return value["default"]
    return value


def _build_record(raw: Dict[str, Any] | None) -> Record | None:
    """Build a Record model from a small standings sub-object, if present."""
    if not raw:
        return None

    # NHL API uses fields like `wins`, `losses`, `ot`
    return Record(
        wins=raw.get("wins", 0),
        losses=raw.get("losses", 0),
        ot=raw.get("ot", 0),
    )


def _build_team(raw: Dict[str, Any]) -> Team:
    """Build the Team model from the API object."""
    # The standings/now payload may expose localized objects such as:
    #   {"teamName": {"default": "Canadiens", "fr": "Canadiens"}}
    # We use `_get_default` to safely unwrap these.
    team_id = _get_default(raw.get("teamId"))

    name_source = raw.get("teamName") or raw.get("teamCommonName")
    name = _get_default(name_source) or ""

    abbreviation = _get_default(raw.get("teamAbbrev")) or ""

    division = _get_default(raw.get("divisionName")) or _get_default(
        raw.get("divisionAbbrev")
    )
    conference = _get_default(raw.get("conferenceName")) or _get_default(
        raw.get("conferenceAbbrev")
    )

    return Team(
        id=int(team_id) if team_id is not None else -1,
        name=name,
        abbreviation=abbreviation,
        division=division,
        conference=conference,
    )


def _build_team_standings(season: str, raw: Dict[str, Any]) -> TeamStandings:
    """Build a single `TeamStandings` entry from a raw standings row."""
    team = _build_team(raw)

    # Core numbers
    games_played = int(raw.get("gamesPlayed", 0))
    points = int(raw.get("points", 0))

    # Ranks (use exact 2026 keys; default to 0 if missing)
    league_rank = int(raw.get("leagueSequence", 0))
    conference_rank = int(raw.get("conferenceSequence", 0))
    division_rank = int(raw.get("divisionSequence", 0))

    # Goals (use 2026 keys: goalFor/goalAgainst/goalDiff)
    goals_for = int(raw.get("goalFor", 0))
    goals_against = int(raw.get("goalAgainst", 0))
    goal_differential = int(raw.get("goalDiff", 0))

    # Optional regulation wins / ROW when present
    regulation_wins_raw = _get_default(raw.get("regulationWins"))
    regulation_wins = (
        int(regulation_wins_raw) if regulation_wins_raw is not None else None
    )

    row_raw = _get_default(raw.get("row"))
    row = int(row_raw) if row_raw is not None else None

    # Split records, when present
    home_record = _build_record(raw.get("homeRecord"))
    away_record = _build_record(raw.get("roadRecord") or raw.get("awayRecord"))
    division_record = _build_record(raw.get("divisionRecord"))
    conference_record = _build_record(raw.get("conferenceRecord"))

    return TeamStandings(
        season=season,
        team=team,
        games_played=games_played,
        points=points,
        regulation_wins=regulation_wins,
        row=row,
        league_rank=league_rank,
        conference_rank=conference_rank,
        division_rank=division_rank,
        goals_for=goals_for,
        goals_against=goals_against,
        goal_differential=goal_differential,
        home_record=home_record,
        away_record=away_record,
        division_record=division_record,
        conference_record=conference_record,
    )


async def fetch_standings_snapshot() -> StandingsSnapshot:
    """Fetch the current NHL standings and parse into `StandingsSnapshot`."""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(STANDINGS_URL)
        resp.raise_for_status()
        data = resp.json()

    # The standings/now format contains a `standings` list; each entry includes
    # a `seasonId`. Prefer a top-level season key when present, otherwise
    # derive it from the first standings row.
    season_raw = data.get("seasonId") or data.get("season")
    if season_raw is None:
        standings_list = data.get("standings") or []
        if standings_list:
            season_raw = standings_list[0].get("seasonId")
    season: str = str(season_raw) if season_raw is not None else ""

    raw_standings: List[Dict[str, Any]] = data.get("standings") or data.get(
        "teamRecords", []
    )

    teams: List[TeamStandings] = [
        _build_team_standings(season=season, raw=entry) for entry in raw_standings
    ]

    # Note: `StandingsSnapshot` defines `teams` with alias="standings", so we
    # pass the list using that alias.
    return StandingsSnapshot(season=season, standings=teams)


def save_snapshot(snapshot: StandingsSnapshot) -> str:
    """Persist a standings snapshot for the 2024–2025 season.

    The output filename is forced to contain '20242025' so it's obvious which
    season the data corresponds to, regardless of what the API reports.
    """
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    path = RAW_DATA_DIR / "standings_20242025_snapshot.json"

    # Support both Pydantic v1 and v2 without assuming which is installed.
    if hasattr(snapshot, "model_dump"):
        payload = snapshot.model_dump(by_alias=True)  # Pydantic v2
    else:
        payload = snapshot.dict(by_alias=True)  # Pydantic v1

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(path)


async def main() -> None:
    """Simple CLI entrypoint for manual testing."""
    snapshot = await fetch_standings_snapshot()
    print(f"Season: {snapshot.season}")
    print(f"Teams in snapshot: {len(snapshot.teams)}")

    # Print the first three teams as a smoke test
    for ts in snapshot.teams[:3]:
        print(
            f"{ts.team.abbreviation}: {ts.points} pts, "
            f"{ts.games_played} GP, GF={ts.goals_for}, GA={ts.goals_against}"
        )

    saved_path = save_snapshot(snapshot)
    print(f"Snapshot saved to: {saved_path}")


if __name__ == "__main__":
    # Run the async main, which will fetch and print the first three teams.
    asyncio.run(main())

