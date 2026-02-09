from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Record(BaseModel):
    """Win/loss record for a team in a given context (overall, home, away, division, conference)."""

    wins: int = Field(..., ge=0)
    losses: int = Field(..., ge=0)
    ot: int = Field(0, ge=0, description="Overtime or shootout losses")


class Team(BaseModel):
    """Core team identity information from the standings/now endpoint."""

    id: int = Field(..., description="Unique team identifier (NHL internal ID)")
    name: str
    abbreviation: str
    division: Optional[str] = Field(
        None, description="Short division name, e.g. 'Atlantic', if present."
    )
    conference: Optional[str] = Field(
        None, description="Conference name, e.g. 'Eastern', if present."
    )


class TeamStandings(BaseModel):
    """Team standings snapshot from the standings/now endpoint."""

    season: str = Field(
        ...,
        description="Season identifier, e.g. '20242025'.",
    )
    team: Team

    games_played: int = Field(..., ge=0)

    points: int = Field(..., ge=0)
    regulation_wins: Optional[int] = Field(
        None,
        ge=0,
        description="Wins in regulation only, if exposed by the API.",
    )
    row: Optional[int] = Field(
        None,
        ge=0,
        description="Regulation plus overtime wins, if exposed by the API.",
    )

    league_rank: Optional[int] = Field(
        None, ge=1, description="Team rank across the entire league."
    )
    conference_rank: Optional[int] = Field(
        None, ge=1, description="Team rank within its conference."
    )
    division_rank: Optional[int] = Field(
        None, ge=1, description="Team rank within its division."
    )

    goals_for: int = Field(..., ge=0)
    goals_against: int = Field(..., ge=0)

    home_record: Optional[Record] = None
    away_record: Optional[Record] = None
    division_record: Optional[Record] = None
    conference_record: Optional[Record] = None

    goal_differential: int = Field(
        ...,
        description="Computed or API-provided goal differential (GF - GA).",
    )


class StandingsSnapshot(BaseModel):
    """Wrapper for the full response from the standings/now endpoint.

    The NHL API returns a collection of team standings rather than a single team.
    """

    season: str = Field(
        ...,
        description="Season identifier shared by all teams, e.g. '20242025'.",
    )
    teams: List[TeamStandings] = Field(
        ...,
        alias="standings",
        description="Standings entries for all teams returned by the endpoint.",
    )

