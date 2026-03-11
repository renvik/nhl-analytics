"""
Gold Layer visualizer: build Plotly charts from Silver/Bronze data.

- Top 10 Goal Scorers: horizontal bar (Y: player name, X: goals), rank 1 at top.
- League Standings: horizontal bar (Y: team name, X: points), rank 1 at top.

Output: in-memory figures; optionally write HTML to data/gold/.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

try:
    from src.processor import (
        GOAL_LEADERS_PATH,
        SILVER_PLAYER_STATS_PATH,
        STANDINGS_PATH,
        TOP_50_SCORERS_PATH,
        load_goal_leaders,
        load_standings,
    )
except ImportError:
    from processor import (
        GOAL_LEADERS_PATH,
        SILVER_PLAYER_STATS_PATH,
        STANDINGS_PATH,
        TOP_50_SCORERS_PATH,
        load_goal_leaders,
        load_standings,
    )

_BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_DATA_DIR = _BASE_DIR / "data" / "gold"


def _top10_goal_scorers_df(
    *,
    top50_path: Path | None = None,
    silver_path: Path | None = None,
    goal_leaders_path: Path | None = None,
) -> pd.DataFrame:
    """Load Top 50 scorers CSV (preferred), or silver/goal leaders; take top 10 by goals."""
    top50_path = top50_path or TOP_50_SCORERS_PATH
    silver_path = silver_path or SILVER_PLAYER_STATS_PATH
    goal_leaders_path = goal_leaders_path or GOAL_LEADERS_PATH

    if top50_path.exists():
        df = pd.read_csv(top50_path)
        # CSV has player, value; already sorted by goals desc
        top10 = df.head(10)[["player", "value"]].copy()
        return top10.reset_index(drop=True)
    if silver_path.exists():
        df = pd.read_csv(silver_path)
    else:
        df = load_goal_leaders(goal_leaders_path)
    by_goals = df.sort_values("value", ascending=False)
    top10 = by_goals.head(10).copy()
    top10["player"] = (top10["firstName"].astype(str) + " " + top10["lastName"].astype(str)).str.strip()
    return top10[["player", "value"]].reset_index(drop=True)


def fig_top10_goal_scorers(
    *,
    top50_path: Path | None = None,
    silver_path: Path | None = None,
    goal_leaders_path: Path | None = None,
) -> go.Figure:
    """
    Top 10 Goal Scorers: horizontal bar — Y: player name, X: goals.
    Rank 1 (most goals) at top. Uses data/silver/top_50_scorers.csv when present.
    """
    top10 = _top10_goal_scorers_df(
        top50_path=top50_path,
        silver_path=silver_path,
        goal_leaders_path=goal_leaders_path,
    )
    # Plotly horizontal bar: first row in data is at bottom. Reverse so rank 1 is at top.
    top10 = top10.iloc[::-1].reset_index(drop=True)

    fig = px.bar(
        top10,
        x="value",
        y="player",
        orientation="h",
        labels={"value": "Goals", "player": "Player"},
        title="Top 10 Goal Scorers",
        text="value",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": top10["player"].tolist()},
        xaxis_title="Goals",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=20),
    )
    return fig


def fig_league_standings(
    *,
    standings_path: Path | None = None,
) -> go.Figure:
    """
    League Standings: horizontal bar — Y: team name, X: points.
    Rank 1 at top. Returns in-memory Plotly figure.
    """
    standings = load_standings(standings_path)
    if len(standings) != 32:
        warnings.warn(
            f"Expected 32 NHL teams in standings, got {len(standings)}. "
            "Re-run the extractor to refresh data/raw/standings_20242025_snapshot.json.",
            UserWarning,
            stacklevel=2,
        )
    # Sort by league_rank; rank 1 at top means we show in ascending rank order, then reverse for bar order
    by_rank = standings.sort_values("league_rank").copy()
    by_rank = by_rank.rename(columns={"team_name": "team"})
    # For horizontal bar, reverse so rank 1 is at top
    by_rank = by_rank.iloc[::-1].reset_index(drop=True)

    fig = px.bar(
        by_rank,
        x="points",
        y="team",
        orientation="h",
        labels={"points": "Points", "team": "Team"},
        title="NHL Standings 2024-2025",
        text="points",
    )
    fig.update_traces(textposition="outside")
    n_teams = len(by_rank)
    fig.update_layout(
        yaxis={"categoryorder": "array", "categoryarray": by_rank["team"].tolist()},
        xaxis_title="Points",
        yaxis_title="",
        showlegend=False,
        margin=dict(l=20),
        height=max(500, n_teams * 28),  # enough height so all teams are visible
    )
    return fig


def write_gold_html(
    *,
    top10_path: Path | None = None,
    standings_path: Path | None = None,
) -> None:
    """Write Top 10 Goal Scorers and League Standings figures to data/gold/ as HTML."""
    GOLD_DATA_DIR.mkdir(parents=True, exist_ok=True)

    top10_path = top10_path or (GOLD_DATA_DIR / "top10_goal_scorers.html")
    fig_top10 = fig_top10_goal_scorers()
    fig_top10.write_html(str(top10_path))
    print(f"Wrote {top10_path}")

    standings_path = standings_path or (GOLD_DATA_DIR / "league_standings.html")
    fig_standings = fig_league_standings()
    fig_standings.write_html(str(standings_path))
    print(f"Wrote {standings_path}")


if __name__ == "__main__":
    write_gold_html()
