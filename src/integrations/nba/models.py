"""NBA data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class NbaConference:
    """NBA conference information."""
    conference_id: int
    conference_name: str
    conference_abbr: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaDivision:
    """NBA division information."""
    division_id: int
    division_name: str
    division_abbr: str | None
    conference_id: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaTeam:
    """NBA team information."""
    team_id: int
    team_name: str
    team_abbr: str | None
    team_city: str | None
    conference_id: int | None
    division_id: int | None
    year_founded: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaGame:
    """NBA game information."""
    game_id: str
    season: int
    season_type: str | None  # Regular Season, Playoffs, etc.
    game_date: date | None
    status: str | None
    home_team_id: int | None
    away_team_id: int | None
    home_score: int | None
    away_score: int | None
    arena: str | None
    attendance: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaPlayer:
    """NBA player dimension information."""
    player_id: int
    full_name: str
    first_name: str | None
    last_name: str | None
    jersey_number: str | None
    position: str | None
    height: str | None
    weight: int | None
    birth_date: date | None
    country: str | None
    draft_year: int | None
    draft_round: int | None
    draft_number: int | None
    is_active: bool | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaPlayerGameStats:
    """Player statistics for a single game."""
    game_id: str
    player_id: int
    team_id: int
    player_name: str
    starter: bool | None
    minutes: str | None
    field_goals_made: int | None
    field_goals_attempted: int | None
    field_goal_pct: float | None
    three_pointers_made: int | None
    three_pointers_attempted: int | None
    three_point_pct: float | None
    free_throws_made: int | None
    free_throws_attempted: int | None
    free_throw_pct: float | None
    offensive_rebounds: int | None
    defensive_rebounds: int | None
    total_rebounds: int | None
    assists: int | None
    steals: int | None
    blocks: int | None
    turnovers: int | None
    personal_fouls: int | None
    points: int | None
    plus_minus: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class NbaStandingsRecord:
    """NBA standings record for a single team on a given date."""
    team_id: int
    season: int
    season_type: str | None
    standings_date: date | None
    conference_id: int | None
    division_id: int | None
    conference_rank: int | None
    division_rank: int | None
    wins: int | None
    losses: int | None
    win_pct: float | None
    games_back: float | None
    conference_wins: int | None
    conference_losses: int | None
    home_wins: int | None
    home_losses: int | None
    away_wins: int | None
    away_losses: int | None
    last_ten_wins: int | None
    last_ten_losses: int | None
    streak: str | None
    points_per_game: float | None
    opp_points_per_game: float | None
    diff_points_per_game: float | None
    raw: dict[str, Any]
