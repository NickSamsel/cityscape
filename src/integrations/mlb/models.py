"""MLB data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True, slots=True)
class MlbTeam:
    """MLB team information."""
    team_id: int
    team_name: str
    team_abbr: str | None
    league_id: int | None
    division_id: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbGame:
    """MLB game information."""
    game_id: int
    season: int
    game_date: date | None
    game_type: str | None
    status: str | None
    home_team_id: int | None
    away_team_id: int | None
    home_score: int | None
    away_score: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbPlayerBattingStats:
    """Player batting statistics for a single game."""
    game_id: int
    player_id: int
    team_id: int
    player_name: str
    batting_order: str | None
    position: str | None
    at_bats: int | None
    runs: int | None
    hits: int | None
    doubles: int | None
    triples: int | None
    home_runs: int | None
    rbi: int | None
    stolen_bases: int | None
    walks: int | None
    strikeouts: int | None
    left_on_base: int | None
    avg: str | None
    obp: str | None
    slg: str | None
    ops: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbPlayerPitchingStats:
    """Player pitching statistics for a single game."""
    game_id: int
    player_id: int
    team_id: int
    player_name: str
    innings_pitched: str | None
    hits: int | None
    runs: int | None
    earned_runs: int | None
    walks: int | None
    strikeouts: int | None
    home_runs: int | None
    pitches: int | None
    strikes: int | None
    era: str | None
    raw: dict[str, Any]
