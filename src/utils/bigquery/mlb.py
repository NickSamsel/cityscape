from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
from google.cloud import bigquery
from prefect import get_run_logger

from .engine import INFER_SCHEMA, UpsertTableConfig, ensure_table, upsert_dataframe


def _ts(expr: str) -> str:
    return f"TIMESTAMP({expr})"


def _i64(expr: str) -> str:
    return f"CAST({expr} AS INT64)"


def _f64(expr: str) -> str:
    return f"CAST({expr} AS FLOAT64)"


MLB_SCHEDULE = UpsertTableConfig(
    dataset="raw",
    table="mlb_schedule",
    key_columns=("game_id",),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("game_datetime", "TIMESTAMP", mode="NULLABLE"),
        bigquery.SchemaField("game_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("day_night", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("venue_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("venue_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_probable_pitcher_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_probable_pitcher_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_probable_pitcher_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_probable_pitcher_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("scheduled_innings", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("series_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={
        "game_datetime": _ts("S.`game_datetime`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
    insert_expressions={
        "game_datetime": _ts("S.`game_datetime`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
)


MLB_VENUES = UpsertTableConfig(
    dataset="raw",
    table="mlb_venues",
    key_columns=("venue_id", "season"),
    on_clause=(
        "T.`venue_id` = S.`venue_id` AND (T.`season` = S.`season` OR (T.`season` IS NULL AND S.`season` IS NULL))"
    ),
    schema=(
        bigquery.SchemaField("venue_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("venue_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("active", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("state_abbrev", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("country", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("latitude", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("longitude", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("capacity", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("turf_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("roof_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("left_line", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("right_line", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("center", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("left", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("right", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("left_center", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("right_center", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={
        "capacity": _i64("S.`capacity`"),
        "left_line": _f64("S.`left_line`"),
        "right_line": _f64("S.`right_line`"),
        "center": _f64("S.`center`"),
        "left": _f64("S.`left`"),
        "right": _f64("S.`right`"),
        "left_center": _f64("S.`left_center`"),
        "right_center": _f64("S.`right_center`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
    insert_expressions={
        "capacity": _i64("S.`capacity`"),
        "left_line": _f64("S.`left_line`"),
        "right_line": _f64("S.`right_line`"),
        "center": _f64("S.`center`"),
        "left": _f64("S.`left`"),
        "right": _f64("S.`right`"),
        "left_center": _f64("S.`left_center`"),
        "right_center": _f64("S.`right_center`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
)


MLB_GAME_BROADCASTS = UpsertTableConfig(
    dataset="raw",
    table="mlb_game_broadcasts",
    key_columns=("game_id", "broadcast_name"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("broadcast_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("broadcast_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("call_sign", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("is_national", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("home_away", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("language", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_GAME_LINEUPS = UpsertTableConfig(
    dataset="raw",
    table="mlb_game_lineups",
    key_columns=("game_id", "player_id", "team_side"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_side", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("full_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("position_abbreviation", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("batting_order", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_TEAMS = UpsertTableConfig(
    dataset="raw",
    table="mlb_teams",
    key_columns=("team_id", "season"),
    schema=(
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("division_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_GAMES = UpsertTableConfig(
    dataset="raw",
    table="mlb_games",
    key_columns=("game_id", "season"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("game_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("venue_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_PLAYER_BATTING_STATS = UpsertTableConfig(
    dataset="raw",
    table="mlb_player_batting_stats",
    key_columns=("game_id", "player_id"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("batting_order", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("position", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("at_bats", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("runs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("hits", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("doubles", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("triples", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("home_runs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("rbi", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("stolen_bases", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("walks", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("strikeouts", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("left_on_base", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("avg", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("obp", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("slg", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("ops", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_PLAYER_PITCHING_STATS = UpsertTableConfig(
    dataset="raw",
    table="mlb_player_pitching_stats",
    key_columns=("game_id", "player_id"),
    schema=(
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("innings_pitched", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("hits", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("runs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("earned_runs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("walks", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("strikeouts", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("home_runs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("pitches", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("strikes", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("era", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_LEAGUES = UpsertTableConfig(
    dataset="raw",
    table="mlb_leagues",
    key_columns=("league_id",),
    schema=(
        bigquery.SchemaField("league_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("league_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("league_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_DIVISIONS = UpsertTableConfig(
    dataset="raw",
    table="mlb_divisions",
    key_columns=("division_id",),
    schema=(
        bigquery.SchemaField("division_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("division_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("division_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_PLAYERS = UpsertTableConfig(
    dataset="raw",
    table="mlb_players",
    key_columns=("player_id",),
    schema=(
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("full_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("first_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("last_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("primary_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("birth_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("current_age", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("birth_city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("birth_state_province", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("birth_country", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("height", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("weight", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("primary_position_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("primary_position_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("primary_position_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("bat_side_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("bat_side_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitch_hand_code", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitch_hand_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("mlb_debut_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("active", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    update_expressions={"loaded_at": _ts("S.`loaded_at`")},
    insert_expressions={"loaded_at": _ts("S.`loaded_at`")},
)


MLB_STATCAST_PITCHES = UpsertTableConfig(
    dataset="raw",
    table="mlb_statcast_pitches",
    key_columns=("play_id",),
    schema=(
        bigquery.SchemaField("play_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("at_bat_index", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("pitcher_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("batter_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("catcher_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("umpire_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitch_number", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("pitch_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitch_type_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("release_speed", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("release_spin_rate", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("release_extension", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("release_pos_x", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("release_pos_y", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("release_pos_z", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("zone", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("plate_x", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("plate_z", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("strikes", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("balls", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("outs", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("pitch_result", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("pitch_result_description", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    staging_schema=None,
    update_expressions={
        "at_bat_index": _i64("S.`at_bat_index`"),
        "pitch_number": _i64("S.`pitch_number`"),
        "release_speed": _f64("S.`release_speed`"),
        "release_spin_rate": _f64("S.`release_spin_rate`"),
        "release_extension": _f64("S.`release_extension`"),
        "release_pos_x": _f64("S.`release_pos_x`"),
        "release_pos_y": _f64("S.`release_pos_y`"),
        "release_pos_z": _f64("S.`release_pos_z`"),
        "zone": _i64("S.`zone`"),
        "plate_x": _f64("S.`plate_x`"),
        "plate_z": _f64("S.`plate_z`"),
        "strikes": _i64("S.`strikes`"),
        "balls": _i64("S.`balls`"),
        "outs": _i64("S.`outs`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
    insert_expressions={
        "at_bat_index": _i64("S.`at_bat_index`"),
        "pitch_number": _i64("S.`pitch_number`"),
        "release_speed": _f64("S.`release_speed`"),
        "release_spin_rate": _f64("S.`release_spin_rate`"),
        "release_extension": _f64("S.`release_extension`"),
        "release_pos_x": _f64("S.`release_pos_x`"),
        "release_pos_y": _f64("S.`release_pos_y`"),
        "release_pos_z": _f64("S.`release_pos_z`"),
        "zone": _i64("S.`zone`"),
        "plate_x": _f64("S.`plate_x`"),
        "plate_z": _f64("S.`plate_z`"),
        "strikes": _i64("S.`strikes`"),
        "balls": _i64("S.`balls`"),
        "outs": _i64("S.`outs`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
)


MLB_STATCAST_BATTED_BALLS = UpsertTableConfig(
    dataset="raw",
    table="mlb_statcast_batted_balls",
    key_columns=("play_id",),
    schema=(
        bigquery.SchemaField("play_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("at_bat_index", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("batter_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("pitcher_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("launch_speed", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("launch_angle", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("launch_distance", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("hit_location", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("hit_trajectory", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("hit_result", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("sprint_speed", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("is_barrel", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("is_hard_hit", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    staging_schema=None,
    update_expressions={
        "at_bat_index": _i64("S.`at_bat_index`"),
        "launch_speed": _f64("S.`launch_speed`"),
        "launch_angle": _f64("S.`launch_angle`"),
        "launch_distance": _f64("S.`launch_distance`"),
        "hit_location": _i64("S.`hit_location`"),
        "sprint_speed": _f64("S.`sprint_speed`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
    insert_expressions={
        "at_bat_index": _i64("S.`at_bat_index`"),
        "launch_speed": _f64("S.`launch_speed`"),
        "launch_angle": _f64("S.`launch_angle`"),
        "launch_distance": _f64("S.`launch_distance`"),
        "hit_location": _i64("S.`hit_location`"),
        "sprint_speed": _f64("S.`sprint_speed`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
)


MLB_STANDINGS = UpsertTableConfig(
    dataset="raw",
    table="mlb_standings",
    key_columns=("team_id", "season", "standings_date"),
    schema=(
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("standings_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("division_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("division_rank", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("wins", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("losses", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("win_pct", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("games_back", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("wildcard_games_back", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("streak", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("last_ten_record", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("runs_scored", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("runs_allowed", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("run_differential", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("home_wins", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("home_losses", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_wins", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_losses", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ),
    staging_schema=None,
    update_expressions={
        "league_id": _i64("S.`league_id`"),
        "division_id": _i64("S.`division_id`"),
        "division_rank": _i64("S.`division_rank`"),
        "wins": _i64("S.`wins`"),
        "losses": _i64("S.`losses`"),
        "win_pct": _f64("S.`win_pct`"),
        "games_back": _f64("S.`games_back`"),
        "wildcard_games_back": _f64("S.`wildcard_games_back`"),
        "runs_scored": _i64("S.`runs_scored`"),
        "runs_allowed": _i64("S.`runs_allowed`"),
        "run_differential": _i64("S.`run_differential`"),
        "home_wins": _i64("S.`home_wins`"),
        "home_losses": _i64("S.`home_losses`"),
        "away_wins": _i64("S.`away_wins`"),
        "away_losses": _i64("S.`away_losses`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
    insert_expressions={
        "league_id": _i64("S.`league_id`"),
        "division_id": _i64("S.`division_id`"),
        "division_rank": _i64("S.`division_rank`"),
        "wins": _i64("S.`wins`"),
        "losses": _i64("S.`losses`"),
        "win_pct": _f64("S.`win_pct`"),
        "games_back": _f64("S.`games_back`"),
        "wildcard_games_back": _f64("S.`wildcard_games_back`"),
        "runs_scored": _i64("S.`runs_scored`"),
        "runs_allowed": _i64("S.`runs_allowed`"),
        "run_differential": _i64("S.`run_differential`"),
        "home_wins": _i64("S.`home_wins`"),
        "home_losses": _i64("S.`home_losses`"),
        "away_wins": _i64("S.`away_wins`"),
        "away_losses": _i64("S.`away_losses`"),
        "loaded_at": _ts("S.`loaded_at`"),
    },
)


def ensure_mlb_schedule_tables(client: bigquery.Client, project_id: str) -> None:
    for cfg in (MLB_SCHEDULE, MLB_VENUES, MLB_GAME_BROADCASTS, MLB_GAME_LINEUPS):
        ensure_table(client=client, project_id=project_id, cfg=cfg)


def ensure_mlb_tables(client: bigquery.Client, project_id: str) -> None:
    for cfg in (
        MLB_TEAMS,
        MLB_GAMES,
        MLB_PLAYER_BATTING_STATS,
        MLB_PLAYER_PITCHING_STATS,
        MLB_LEAGUES,
        MLB_DIVISIONS,
        MLB_PLAYERS,
        MLB_STATCAST_PITCHES,
        MLB_STATCAST_BATTED_BALLS,
        MLB_STANDINGS,
        MLB_SCHEDULE,
        MLB_VENUES,
        MLB_GAME_BROADCASTS,
        MLB_GAME_LINEUPS,
    ):
        ensure_table(client=client, project_id=project_id, cfg=cfg)


def upsert_mlb_schedule(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "season": r["season"],
                "game_date": r.get("game_date"),
                "game_datetime": r.get("game_datetime"),
                "game_type": r.get("game_type"),
                "status": r.get("status"),
                "day_night": r.get("day_night"),
                "venue_id": str(r["venue_id"]) if r.get("venue_id") is not None else None,
                "venue_name": r.get("venue_name"),
                "home_team_id": str(r["home_team_id"]) if r.get("home_team_id") is not None else None,
                "away_team_id": str(r["away_team_id"]) if r.get("away_team_id") is not None else None,
                "home_probable_pitcher_id": (
                    str(r["home_probable_pitcher_id"]) if r.get("home_probable_pitcher_id") is not None else None
                ),
                "home_probable_pitcher_name": r.get("home_probable_pitcher_name"),
                "away_probable_pitcher_id": (
                    str(r["away_probable_pitcher_id"]) if r.get("away_probable_pitcher_id") is not None else None
                ),
                "away_probable_pitcher_name": r.get("away_probable_pitcher_name"),
                "scheduled_innings": r.get("scheduled_innings"),
                "series_description": r.get("series_description"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": dt.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate schedule records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_SCHEDULE, df=df)
    return len(df)


def upsert_mlb_teams(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "team_id": str(r["team_id"]),
                "season": r["season"],
                "team_name": r["team_name"],
                "team_abbr": r.get("team_abbr"),
                "league_id": r.get("league_id"),
                "division_id": r.get("division_id"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["team_id", "season"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate team records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_TEAMS, df=df)
    return len(df)


def upsert_mlb_games(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "season": r["season"],
                "game_date": r.get("game_date"),
                "game_type": r.get("game_type"),
                "status": r.get("status"),
                "home_team_id": str(r["home_team_id"]) if r.get("home_team_id") else None,
                "away_team_id": str(r["away_team_id"]) if r.get("away_team_id") else None,
                "home_score": r.get("home_score"),
                "away_score": r.get("away_score"),
                "venue_id": str(r["venue_id"]) if r.get("venue_id") is not None else None,
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "season"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate game records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_GAMES, df=df)
    return len(df)


def upsert_mlb_player_batting_stats(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "player_id": str(r["player_id"]),
                "team_id": str(r["team_id"]),
                "player_name": r["player_name"],
                "batting_order": r.get("batting_order"),
                "position": r.get("position"),
                "at_bats": r.get("at_bats"),
                "runs": r.get("runs"),
                "hits": r.get("hits"),
                "doubles": r.get("doubles"),
                "triples": r.get("triples"),
                "home_runs": r.get("home_runs"),
                "rbi": r.get("rbi"),
                "stolen_bases": r.get("stolen_bases"),
                "walks": r.get("walks"),
                "strikeouts": r.get("strikeouts"),
                "left_on_base": r.get("left_on_base"),
                "avg": r.get("avg"),
                "obp": r.get("obp"),
                "slg": r.get("slg"),
                "ops": r.get("ops"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "player_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(
            f"Removed {initial_count - len(df)} duplicate batting stat records"
        )

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_PLAYER_BATTING_STATS, df=df)
    return len(df)


def upsert_mlb_player_pitching_stats(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "player_id": str(r["player_id"]),
                "team_id": str(r["team_id"]),
                "player_name": r["player_name"],
                "innings_pitched": r.get("innings_pitched"),
                "hits": r.get("hits"),
                "runs": r.get("runs"),
                "earned_runs": r.get("earned_runs"),
                "walks": r.get("walks"),
                "strikeouts": r.get("strikeouts"),
                "home_runs": r.get("home_runs"),
                "pitches": r.get("pitches"),
                "strikes": r.get("strikes"),
                "era": r.get("era"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "player_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(
            f"Removed {initial_count - len(df)} duplicate pitching stat records"
        )

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_PLAYER_PITCHING_STATS, df=df)
    return len(df)


def upsert_mlb_leagues(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "league_id": r["league_id"],
                "league_name": r["league_name"],
                "league_abbr": r.get("league_abbr"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["league_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate league records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_LEAGUES, df=df)
    return len(df)


def upsert_mlb_divisions(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "division_id": r["division_id"],
                "division_name": r["division_name"],
                "division_abbr": r.get("division_abbr"),
                "league_id": r.get("league_id"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["division_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(
            f"Removed {initial_count - len(df)} duplicate division records"
        )

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_DIVISIONS, df=df)
    return len(df)


def upsert_mlb_players(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "player_id": str(r["player_id"]),
                "full_name": r["full_name"],
                "first_name": r.get("first_name"),
                "last_name": r.get("last_name"),
                "primary_number": r.get("primary_number"),
                "birth_date": r.get("birth_date"),
                "current_age": r.get("current_age"),
                "birth_city": r.get("birth_city"),
                "birth_state_province": r.get("birth_state_province"),
                "birth_country": r.get("birth_country"),
                "height": r.get("height"),
                "weight": r.get("weight"),
                "primary_position_code": r.get("primary_position_code"),
                "primary_position_name": r.get("primary_position_name"),
                "primary_position_abbr": r.get("primary_position_abbr"),
                "bat_side_code": r.get("bat_side_code"),
                "bat_side_description": r.get("bat_side_description"),
                "pitch_hand_code": r.get("pitch_hand_code"),
                "pitch_hand_description": r.get("pitch_hand_description"),
                "mlb_debut_date": r.get("mlb_debut_date"),
                "active": r.get("active"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["player_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate player records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_PLAYERS, df=df)
    return len(df)


def upsert_mlb_statcast_pitches(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "play_id": r["play_id"],
                "game_id": str(r["game_id"]),
                "at_bat_index": r.get("at_bat_index"),
                "pitcher_id": str(r["pitcher_id"]),
                "batter_id": str(r["batter_id"]),
                "catcher_id": str(r["catcher_id"]) if r.get("catcher_id") else None,
                "umpire_id": str(r["umpire_id"]) if r.get("umpire_id") else None,
                "pitch_number": r.get("pitch_number"),
                "pitch_type": r.get("pitch_type"),
                "pitch_type_description": r.get("pitch_type_description"),
                "release_speed": r.get("release_speed"),
                "release_spin_rate": r.get("release_spin_rate"),
                "release_extension": r.get("release_extension"),
                "release_pos_x": r.get("release_pos_x"),
                "release_pos_y": r.get("release_pos_y"),
                "release_pos_z": r.get("release_pos_z"),
                "zone": r.get("zone"),
                "plate_x": r.get("plate_x"),
                "plate_z": r.get("plate_z"),
                "strikes": r.get("strikes"),
                "balls": r.get("balls"),
                "outs": r.get("outs"),
                "pitch_result": r.get("pitch_result"),
                "pitch_result_description": r.get("pitch_result_description"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["play_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate pitch records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_STATCAST_PITCHES, df=df)
    return len(df)


def upsert_mlb_statcast_batted_balls(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "play_id": r["play_id"],
                "game_id": str(r["game_id"]),
                "at_bat_index": r.get("at_bat_index"),
                "batter_id": str(r["batter_id"]),
                "pitcher_id": str(r["pitcher_id"]),
                "launch_speed": r.get("launch_speed"),
                "launch_angle": r.get("launch_angle"),
                "launch_distance": r.get("launch_distance"),
                "hit_location": r.get("hit_location"),
                "hit_trajectory": r.get("hit_trajectory"),
                "hit_result": r.get("hit_result"),
                "sprint_speed": r.get("sprint_speed"),
                "is_barrel": r.get("is_barrel"),
                "is_hard_hit": r.get("is_hard_hit"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["play_id"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(
            f"Removed {initial_count - len(df)} duplicate batted ball records"
        )

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_STATCAST_BATTED_BALLS, df=df)
    return len(df)


def upsert_mlb_standings(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "team_id": str(r["team_id"]),
                "season": r["season"],
                "standings_date": r["standings_date"],
                "league_id": r.get("league_id"),
                "division_id": r.get("division_id"),
                "division_rank": r.get("division_rank"),
                "wins": r.get("wins"),
                "losses": r.get("losses"),
                "win_pct": r.get("win_pct"),
                "games_back": r.get("games_back"),
                "wildcard_games_back": r.get("wildcard_games_back"),
                "streak": r.get("streak"),
                "last_ten_record": r.get("last_ten_record"),
                "runs_scored": r.get("runs_scored"),
                "runs_allowed": r.get("runs_allowed"),
                "run_differential": r.get("run_differential"),
                "home_wins": r.get("home_wins"),
                "home_losses": r.get("home_losses"),
                "away_wins": r.get("away_wins"),
                "away_losses": r.get("away_losses"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": datetime.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["team_id", "season", "standings_date"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(
            f"Removed {initial_count - len(df)} duplicate standings records"
        )

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_STANDINGS, df=df)
    return len(df)


def upsert_mlb_venues(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "venue_id": str(r["venue_id"]),
                "season": r.get("season"),
                "venue_name": r.get("venue_name"),
                "active": r.get("active"),
                "city": r.get("city"),
                "state": r.get("state"),
                "state_abbrev": r.get("state_abbrev"),
                "country": r.get("country"),
                "latitude": r.get("latitude"),
                "longitude": r.get("longitude"),
                "capacity": r.get("capacity"),
                "turf_type": r.get("turf_type"),
                "roof_type": r.get("roof_type"),
                "left_line": r.get("left_line"),
                "right_line": r.get("right_line"),
                "center": r.get("center"),
                "left": r.get("left"),
                "right": r.get("right"),
                "left_center": r.get("left_center"),
                "right_center": r.get("right_center"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": dt.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["venue_id", "season"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate venue records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_VENUES, df=df)
    return len(df)


def upsert_mlb_game_broadcasts(
    client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]
) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "broadcast_name": r["broadcast_name"],
                "broadcast_type": r.get("broadcast_type"),
                "call_sign": r.get("call_sign"),
                "is_national": r.get("is_national"),
                "home_away": r.get("home_away"),
                "language": r.get("language"),
                "raw": json.dumps(r["raw"]),
                "loaded_at": dt.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "broadcast_name"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate broadcast records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_GAME_BROADCASTS, df=df)
    return len(df)


def upsert_mlb_game_lineups(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data: list[dict[str, Any]] = []
    for r in rows:
        data.append(
            {
                "game_id": str(r["game_id"]),
                "player_id": str(r["player_id"]),
                "team_side": r["team_side"],
                "full_name": r["full_name"],
                "position_abbreviation": r.get("position_abbreviation"),
                "batting_order": r["batting_order"],
                "raw": json.dumps(r["raw"]),
                "loaded_at": dt.utcnow(),
            }
        )

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "player_id", "team_side"], keep="last")
    if initial_count > len(df):
        get_run_logger().warning(f"Removed {initial_count - len(df)} duplicate lineup records")

    upsert_dataframe(client=client, project_id=project_id, cfg=MLB_GAME_LINEUPS, df=df)
    return len(df)
