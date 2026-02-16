"""MLB data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class MlbLeague:
    """MLB league information."""
    league_id: int
    league_name: str
    league_abbr: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbDivision:
    """MLB division information."""
    division_id: int
    division_name: str
    division_abbr: str | None
    league_id: int | None
    raw: dict[str, Any]


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


@dataclass(frozen=True, slots=True)
class MlbPlayer:
    """MLB player dimension information."""
    player_id: int
    full_name: str
    first_name: str | None
    last_name: str | None
    primary_number: str | None
    birth_date: date | None
    current_age: int | None
    birth_city: str | None
    birth_state_province: str | None
    birth_country: str | None
    height: str | None
    weight: int | None
    primary_position_code: str | None
    primary_position_name: str | None
    primary_position_abbr: str | None
    bat_side_code: str | None
    bat_side_description: str | None
    pitch_hand_code: str | None
    pitch_hand_description: str | None
    mlb_debut_date: date | None
    active: bool | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbStandingsRecord:
    """MLB standings record for a single team on a given date."""
    team_id: int
    season: int
    standings_date: date | None
    league_id: int | None
    division_id: int | None
    division_rank: int | None
    wins: int | None
    losses: int | None
    win_pct: float | None
    games_back: float | None
    wildcard_games_back: float | None
    streak: str | None
    last_ten_record: str | None
    runs_scored: int | None
    runs_allowed: int | None
    run_differential: int | None
    home_wins: int | None
    home_losses: int | None
    away_wins: int | None
    away_losses: int | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbStatcastPitch:
    """Statcast pitch-level data with tracking metrics."""
    play_id: str
    game_id: int
    at_bat_index: int | None
    pitcher_id: int
    batter_id: int
    catcher_id: int | None
    umpire_id: int | None
    pitch_number: int | None
    pitch_type: str | None
    pitch_type_description: str | None
    release_speed: float | None  # mph
    release_spin_rate: float | None  # rpm
    release_extension: float | None  # feet
    release_pos_x: float | None  # feet
    release_pos_y: float | None  # feet
    release_pos_z: float | None  # feet
    zone: int | None
    plate_x: float | None  # feet
    plate_z: float | None  # feet
    strikes: int | None
    balls: int | None
    outs: int | None
    pitch_result: str | None
    pitch_result_description: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbStatcastBattedBall:
    """Statcast batted ball data with exit velocity and launch angle."""
    play_id: str
    game_id: int
    at_bat_index: int | None
    batter_id: int
    pitcher_id: int
    launch_speed: float | None  # mph (exit velocity)
    launch_angle: float | None  # degrees
    launch_distance: float | None  # feet (projected)
    hit_location: int | None
    hit_trajectory: str | None
    hit_result: str | None
    sprint_speed: float | None  # ft/sec
    is_barrel: bool | None
    is_hard_hit: bool | None  # 95+ mph exit velo
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbScheduleEntry:
    """MLB schedule entry with venue, probable pitchers, and game time."""
    game_id: int
    season: int
    game_date: date | None
    game_datetime: datetime | None
    game_type: str | None
    status: str | None
    day_night: str | None
    venue_id: int | None
    venue_name: str | None
    home_team_id: int | None
    away_team_id: int | None
    home_probable_pitcher_id: int | None
    home_probable_pitcher_name: str | None
    away_probable_pitcher_id: int | None
    away_probable_pitcher_name: str | None
    scheduled_innings: int | None
    series_description: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbVenue:
    """MLB venue (ballpark) reference data."""

    venue_id: int
    season: int | None
    venue_name: str | None
    active: bool | None

    # Location
    city: str | None
    state: str | None
    state_abbrev: str | None
    country: str | None
    latitude: float | None
    longitude: float | None

    # Field/park metadata
    capacity: int | None
    turf_type: str | None
    roof_type: str | None
    left_line: float | None
    right_line: float | None
    center: float | None
    left: float | None
    right: float | None
    left_center: float | None
    right_center: float | None

    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbBroadcast:
    """Broadcast information for an MLB game."""
    game_id: int
    broadcast_name: str
    broadcast_type: str | None  # TV, AM, FM
    call_sign: str | None
    is_national: bool | None
    home_away: str | None
    language: str | None
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class MlbLineupEntry:
    """Starting lineup entry for an MLB game."""
    game_id: int
    player_id: int
    team_side: str  # "home" or "away"
    full_name: str
    position_abbreviation: str | None
    batting_order: int
    raw: dict[str, Any]
