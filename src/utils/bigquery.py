from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from google.cloud import bigquery
import pandas as pd
from prefect import get_run_logger


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project_id: str
    location: str = "US"
    credentials_path: str | None = None
    service_account_key: str | None = None


def get_client(cfg: BigQueryConfig) -> bigquery.Client:
    """Create BigQuery client with optional credentials.
    
    Supports credentials from:
    1. Base64-encoded service account JSON (cfg.service_account_key)
    2. File path (cfg.credentials_path)
    3. Application Default Credentials (fallback)
    """
    import base64
    import json
    from google.oauth2 import service_account
    
    credentials = None
    
    # Option 1: Use base64-encoded service account key from env variable
    if cfg.service_account_key:
        try:
            # Decode base64 to get JSON string
            decoded = base64.b64decode(cfg.service_account_key)
            service_account_info = json.loads(decoded)
            credentials = service_account.Credentials.from_service_account_info(service_account_info)
        except Exception as e:
            # If decode fails, try using it as plain JSON
            try:
                service_account_info = json.loads(cfg.service_account_key)
                credentials = service_account.Credentials.from_service_account_info(service_account_info)
            except Exception:
                pass  # Fall through to other options
    
    # Option 2: Use file path
    if credentials is None and cfg.credentials_path:
        if os.path.exists(cfg.credentials_path):
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cfg.credentials_path
    
    # Create client with credentials or fall back to application default
    if credentials:
        return bigquery.Client(project=cfg.project_id, location=cfg.location, credentials=credentials)
    else:
        return bigquery.Client(project=cfg.project_id, location=cfg.location)


def ensure_raw_dataset(client: bigquery.Client, project_id: str) -> None:
    """Ensure the raw dataset exists."""
    dataset_id = f"{project_id}.raw"
    dataset = bigquery.Dataset(dataset_id)
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)
    
    # Also create league-specific datasets for dbt models
    for league in ['mlb', 'nba', 'nfl', 'nhl']:
        for layer in ['staging', 'intermediate', 'core']:
            dataset_id = f"{project_id}.{league}_{layer}"
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            client.create_dataset(dataset, exists_ok=True)


def ensure_mlb_tables(client: bigquery.Client, project_id: str) -> None:
    """Ensure MLB tables exist in BigQuery with proper schema."""
    
    # Define schema for mlb_teams
    teams_schema = [
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("division_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    
    teams_table_id = f"{project_id}.raw.mlb_teams"
    teams_table = bigquery.Table(teams_table_id, schema=teams_schema)
    client.create_table(teams_table, exists_ok=True)
    
    # Define schema for mlb_games
    games_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("game_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    
    games_table_id = f"{project_id}.raw.mlb_games"
    games_table = bigquery.Table(games_table_id, schema=games_schema)
    client.create_table(games_table, exists_ok=True)
    
    # Define schema for mlb_player_batting_stats
    batting_stats_schema = [
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
    ]
    
    batting_stats_table_id = f"{project_id}.raw.mlb_player_batting_stats"
    batting_stats_table = bigquery.Table(batting_stats_table_id, schema=batting_stats_schema)
    client.create_table(batting_stats_table, exists_ok=True)
    
    # Define schema for mlb_player_pitching_stats
    pitching_stats_schema = [
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
    ]
    
    pitching_stats_table_id = f"{project_id}.raw.mlb_player_pitching_stats"
    pitching_stats_table = bigquery.Table(pitching_stats_table_id, schema=pitching_stats_schema)
    client.create_table(pitching_stats_table, exists_ok=True)
    
    # Define schema for mlb_leagues
    leagues_schema = [
        bigquery.SchemaField("league_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("league_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("league_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    
    leagues_table_id = f"{project_id}.raw.mlb_leagues"
    leagues_table = bigquery.Table(leagues_table_id, schema=leagues_schema)
    client.create_table(leagues_table, exists_ok=True)
    
    # Define schema for mlb_divisions
    divisions_schema = [
        bigquery.SchemaField("division_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("division_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("division_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]
    
    divisions_table_id = f"{project_id}.raw.mlb_divisions"
    divisions_table = bigquery.Table(divisions_table_id, schema=divisions_schema)
    client.create_table(divisions_table, exists_ok=True)
    
    # Define schema for mlb_players
    players_schema = [
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
    ]
    
    players_table_id = f"{project_id}.raw.mlb_players"
    players_table = bigquery.Table(players_table_id, schema=players_schema)
    client.create_table(players_table, exists_ok=True)
    
    # Define schema for mlb_statcast_pitches
    statcast_pitches_schema = [
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
    ]
    
    statcast_pitches_table_id = f"{project_id}.raw.mlb_statcast_pitches"
    statcast_pitches_table = bigquery.Table(statcast_pitches_table_id, schema=statcast_pitches_schema)
    client.create_table(statcast_pitches_table, exists_ok=True)
    
    # Define schema for mlb_statcast_batted_balls
    statcast_batted_balls_schema = [
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
    ]
    
    statcast_batted_balls_table_id = f"{project_id}.raw.mlb_statcast_batted_balls"
    statcast_batted_balls_table = bigquery.Table(statcast_batted_balls_table_id, schema=statcast_batted_balls_schema)
    client.create_table(statcast_batted_balls_table, exists_ok=True)

    # Define schema for mlb_standings
    standings_schema = [
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
    ]

    standings_table_id = f"{project_id}.raw.mlb_standings"
    standings_table = bigquery.Table(standings_table_id, schema=standings_schema)
    client.create_table(standings_table, exists_ok=True)

    # Define schema for mlb_schedule
    schedule_schema = [
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
    ]

    schedule_table_id = f"{project_id}.raw.mlb_schedule"
    schedule_table = bigquery.Table(schedule_table_id, schema=schedule_schema)
    client.create_table(schedule_table, exists_ok=True)

    # Define schema for mlb_game_broadcasts
    broadcasts_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("broadcast_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("broadcast_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("call_sign", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("is_national", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("home_away", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("language", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    broadcasts_table_id = f"{project_id}.raw.mlb_game_broadcasts"
    broadcasts_table = bigquery.Table(broadcasts_table_id, schema=broadcasts_schema)
    client.create_table(broadcasts_table, exists_ok=True)

    # Define schema for mlb_game_lineups
    lineups_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_side", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("full_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("position_abbreviation", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("batting_order", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    lineups_table_id = f"{project_id}.raw.mlb_game_lineups"
    lineups_table = bigquery.Table(lineups_table_id, schema=lineups_schema)
    client.create_table(lineups_table, exists_ok=True)


def upsert_mlb_teams(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB teams data to BigQuery."""
    if not rows:
        return 0
    
    # Convert to DataFrame
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
            "team_id": str(r["team_id"]),
            "season": r["season"],
            "team_name": r["team_name"],
            "team_abbr": r.get("team_abbr"),
            "league_id": r.get("league_id"),
            "division_id": r.get("division_id"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by (team_id, season) - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['team_id', 'season'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate team records")
    
    # Use MERGE strategy: write to temp table, then merge
    table_id = f"{project_id}.raw.mlb_teams"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("team_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("division_id", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
        ]
    )
    
    # For simplicity, use WRITE_APPEND with deduplication in dbt
    # Or implement proper MERGE logic
    temp_table = f"{project_id}.raw._temp_mlb_teams"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.team_id = S.team_id AND T.season = S.season
    WHEN MATCHED THEN
      UPDATE SET
        team_name = S.team_name,
        team_abbr = S.team_abbr,
        league_id = S.league_id,
        division_id = S.division_id,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (team_id, season, team_name, team_abbr, league_id, division_id, raw, loaded_at)
      VALUES (S.team_id, S.season, S.team_name, S.team_abbr, S.league_id, S.division_id, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_games(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB games data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
            "game_id": str(r["game_id"]),
            "season": r["season"],
            "game_date": r.get("game_date"),
            "game_type": r.get("game_type"),
            "status": r.get("status"),
            "home_team_id": str(r["home_team_id"]) if r.get("home_team_id") else None,
            "away_team_id": str(r["away_team_id"]) if r.get("away_team_id") else None,
            "home_score": r.get("home_score"),
            "away_score": r.get("away_score"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by (game_id, season) - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id', 'season'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate game records")
    
    table_id = f"{project_id}.raw.mlb_games"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
            bigquery.SchemaField("game_type", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("home_score", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("away_score", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_games"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id AND T.season = S.season
    WHEN MATCHED THEN
      UPDATE SET
        game_date = S.game_date,
        game_type = S.game_type,
        status = S.status,
        home_team_id = S.home_team_id,
        away_team_id = S.away_team_id,
        home_score = S.home_score,
        away_score = S.away_score,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, season, game_date, game_type, status, home_team_id, away_team_id, home_score, away_score, raw, loaded_at)
      VALUES (S.game_id, S.season, S.game_date, S.game_type, S.status, S.home_team_id, S.away_team_id, S.home_score, S.away_score, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_player_batting_stats(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB player batting stats data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
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
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by (game_id, player_id) - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id', 'player_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate batting stat records")
    
    table_id = f"{project_id}.raw.mlb_player_batting_stats"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
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
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_player_batting_stats"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id AND T.player_id = S.player_id
    WHEN MATCHED THEN
      UPDATE SET
        team_id = S.team_id,
        player_name = S.player_name,
        batting_order = S.batting_order,
        position = S.position,
        at_bats = S.at_bats,
        runs = S.runs,
        hits = S.hits,
        doubles = S.doubles,
        triples = S.triples,
        home_runs = S.home_runs,
        rbi = S.rbi,
        stolen_bases = S.stolen_bases,
        walks = S.walks,
        strikeouts = S.strikeouts,
        left_on_base = S.left_on_base,
        avg = S.avg,
        obp = S.obp,
        slg = S.slg,
        ops = S.ops,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, player_id, team_id, player_name, batting_order, position, at_bats, runs, hits, doubles, 
              triples, home_runs, rbi, stolen_bases, walks, strikeouts, left_on_base, avg, obp, slg, ops, raw, loaded_at)
      VALUES (S.game_id, S.player_id, S.team_id, S.player_name, S.batting_order, S.position, S.at_bats, S.runs, 
              S.hits, S.doubles, S.triples, S.home_runs, S.rbi, S.stolen_bases, S.walks, S.strikeouts, 
              S.left_on_base, S.avg, S.obp, S.slg, S.ops, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_player_pitching_stats(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB player pitching stats data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
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
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by (game_id, player_id) - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id', 'player_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate pitching stat records")
    
    table_id = f"{project_id}.raw.mlb_player_pitching_stats"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
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
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_player_pitching_stats"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id AND T.player_id = S.player_id
    WHEN MATCHED THEN
      UPDATE SET
        team_id = S.team_id,
        player_name = S.player_name,
        innings_pitched = S.innings_pitched,
        hits = S.hits,
        runs = S.runs,
        earned_runs = S.earned_runs,
        walks = S.walks,
        strikeouts = S.strikeouts,
        home_runs = S.home_runs,
        pitches = S.pitches,
        strikes = S.strikes,
        era = S.era,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, player_id, team_id, player_name, innings_pitched, hits, runs, earned_runs, walks, 
              strikeouts, home_runs, pitches, strikes, era, raw, loaded_at)
      VALUES (S.game_id, S.player_id, S.team_id, S.player_name, S.innings_pitched, S.hits, S.runs, 
              S.earned_runs, S.walks, S.strikeouts, S.home_runs, S.pitches, S.strikes, S.era, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_leagues(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB leagues data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
            "league_id": r["league_id"],
            "league_name": r["league_name"],
            "league_abbr": r.get("league_abbr"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by league_id - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['league_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate league records")
    
    table_id = f"{project_id}.raw.mlb_leagues"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("league_id", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("league_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("league_abbr", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_leagues"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.league_id = S.league_id
    WHEN MATCHED THEN
      UPDATE SET
        league_name = S.league_name,
        league_abbr = S.league_abbr,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (league_id, league_name, league_abbr, raw, loaded_at)
      VALUES (S.league_id, S.league_name, S.league_abbr, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_divisions(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB divisions data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
            "division_id": r["division_id"],
            "division_name": r["division_name"],
            "division_abbr": r.get("division_abbr"),
            "league_id": r.get("league_id"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by division_id - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['division_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate division records")
    
    table_id = f"{project_id}.raw.mlb_divisions"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
            bigquery.SchemaField("division_id", "INT64", mode="REQUIRED"),
            bigquery.SchemaField("division_name", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("division_abbr", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("league_id", "INT64", mode="NULLABLE"),
            bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_divisions"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.division_id = S.division_id
    WHEN MATCHED THEN
      UPDATE SET
        division_name = S.division_name,
        division_abbr = S.division_abbr,
        league_id = S.league_id,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (division_id, division_name, division_abbr, league_id, raw, loaded_at)
      VALUES (S.division_id, S.division_name, S.division_abbr, S.league_id, S.raw, S.loaded_at)
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(data)


def upsert_mlb_players(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB players data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
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
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by player_id - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['player_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate player records")
    
    table_id = f"{project_id}.raw.mlb_players"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=[
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
        ]
    )
    
    temp_table = f"{project_id}.raw._temp_mlb_players"
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()
    
    # Merge into main table
    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.player_id = S.player_id
    WHEN MATCHED THEN
      UPDATE SET
        full_name = S.full_name,
        first_name = S.first_name,
        last_name = S.last_name,
        primary_number = S.primary_number,
        birth_date = S.birth_date,
        current_age = S.current_age,
        birth_city = S.birth_city,
        birth_state_province = S.birth_state_province,
        birth_country = S.birth_country,
        height = S.height,
        weight = S.weight,
        primary_position_code = S.primary_position_code,
        primary_position_name = S.primary_position_name,
        primary_position_abbr = S.primary_position_abbr,
        bat_side_code = S.bat_side_code,
        bat_side_description = S.bat_side_description,
        pitch_hand_code = S.pitch_hand_code,
        pitch_hand_description = S.pitch_hand_description,
        mlb_debut_date = S.mlb_debut_date,
        active = S.active,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (
        player_id, full_name, first_name, last_name, primary_number, 
        birth_date, current_age, birth_city, birth_state_province, birth_country,
        height, weight, primary_position_code, primary_position_name, primary_position_abbr,
        bat_side_code, bat_side_description, pitch_hand_code, pitch_hand_description,
        mlb_debut_date, active, raw, loaded_at
      )
      VALUES (
        S.player_id, S.full_name, S.first_name, S.last_name, S.primary_number,
        S.birth_date, S.current_age, S.birth_city, S.birth_state_province, S.birth_country,
        S.height, S.weight, S.primary_position_code, S.primary_position_name, S.primary_position_abbr,
        S.bat_side_code, S.bat_side_description, S.pitch_hand_code, S.pitch_hand_description,
        S.mlb_debut_date, S.active, S.raw, S.loaded_at
      )
    """
    
    query_job = client.query(merge_sql)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table, not_found_ok=True)
    
    return len(df)


def upsert_mlb_statcast_pitches(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB Statcast pitch data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
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
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by play_id - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['play_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate pitch records")
    
    table_id = f"{project_id}.raw.mlb_statcast_pitches"
    temp_table_id = f"{table_id}_temp"
    
    # Load to temp table
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()
    
    # Use MERGE to upsert (avoid duplicates)
    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.play_id = S.play_id
    WHEN MATCHED THEN
        UPDATE SET
            game_id = S.game_id,
            at_bat_index = CAST(S.at_bat_index AS INT64),
            pitcher_id = S.pitcher_id,
            batter_id = S.batter_id,
            catcher_id = S.catcher_id,
            umpire_id = S.umpire_id,
            pitch_number = CAST(S.pitch_number AS INT64),
            pitch_type = S.pitch_type,
            pitch_type_description = S.pitch_type_description,
            release_speed = CAST(S.release_speed AS FLOAT64),
            release_spin_rate = CAST(S.release_spin_rate AS FLOAT64),
            release_extension = CAST(S.release_extension AS FLOAT64),
            release_pos_x = CAST(S.release_pos_x AS FLOAT64),
            release_pos_y = CAST(S.release_pos_y AS FLOAT64),
            release_pos_z = CAST(S.release_pos_z AS FLOAT64),
            zone = CAST(S.zone AS INT64),
            plate_x = CAST(S.plate_x AS FLOAT64),
            plate_z = CAST(S.plate_z AS FLOAT64),
            strikes = CAST(S.strikes AS INT64),
            balls = CAST(S.balls AS INT64),
            outs = CAST(S.outs AS INT64),
            pitch_result = S.pitch_result,
            pitch_result_description = S.pitch_result_description,
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (play_id, game_id, at_bat_index, pitcher_id, batter_id, catcher_id, umpire_id, pitch_number,
                pitch_type, pitch_type_description, release_speed, release_spin_rate, release_extension,
                release_pos_x, release_pos_y, release_pos_z, zone, plate_x, plate_z, strikes, balls, outs,
                pitch_result, pitch_result_description, raw, loaded_at)
        VALUES (S.play_id, S.game_id, CAST(S.at_bat_index AS INT64), S.pitcher_id, S.batter_id, S.catcher_id,
                S.umpire_id, CAST(S.pitch_number AS INT64), S.pitch_type, S.pitch_type_description, 
                CAST(S.release_speed AS FLOAT64), CAST(S.release_spin_rate AS FLOAT64), CAST(S.release_extension AS FLOAT64),
                CAST(S.release_pos_x AS FLOAT64), CAST(S.release_pos_y AS FLOAT64), CAST(S.release_pos_z AS FLOAT64),
                CAST(S.zone AS INT64), CAST(S.plate_x AS FLOAT64), CAST(S.plate_z AS FLOAT64), 
                CAST(S.strikes AS INT64), CAST(S.balls AS INT64), CAST(S.outs AS INT64), 
                S.pitch_result, S.pitch_result_description, S.raw, TIMESTAMP(S.loaded_at))
    """
    
    query_job = client.query(merge_query)
    query_job.result()
    
    # Clean up temp table
    client.delete_table(temp_table_id, not_found_ok=True)
    
    return len(df)


def upsert_mlb_statcast_batted_balls(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB Statcast batted ball data to BigQuery."""
    if not rows:
        return 0
    
    import json
    from datetime import datetime
    
    data = []
    for r in rows:
        data.append({
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
        })
    
    df = pd.DataFrame(data)
    
    # Deduplicate by play_id - keep last occurrence
    initial_count = len(df)
    df = df.drop_duplicates(subset=['play_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate batted ball records")
    
    table_id = f"{project_id}.raw.mlb_statcast_batted_balls"
    temp_table_id = f"{table_id}_temp"
    
    # Load to temp table
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()
    
    # Use MERGE to upsert (avoid duplicates)
    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.play_id = S.play_id
    WHEN MATCHED THEN
        UPDATE SET
            game_id = S.game_id,
            at_bat_index = CAST(S.at_bat_index AS INT64),
            batter_id = S.batter_id,
            pitcher_id = S.pitcher_id,
            launch_speed = CAST(S.launch_speed AS FLOAT64),
            launch_angle = CAST(S.launch_angle AS FLOAT64),
            launch_distance = CAST(S.launch_distance AS FLOAT64),
            hit_location = CAST(S.hit_location AS INT64),
            hit_trajectory = S.hit_trajectory,
            hit_result = S.hit_result,
            sprint_speed = CAST(S.sprint_speed AS FLOAT64),
            is_barrel = S.is_barrel,
            is_hard_hit = S.is_hard_hit,
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (play_id, game_id, at_bat_index, batter_id, pitcher_id, launch_speed, launch_angle,
                launch_distance, hit_location, hit_trajectory, hit_result, sprint_speed, is_barrel,
                is_hard_hit, raw, loaded_at)
        VALUES (S.play_id, S.game_id, CAST(S.at_bat_index AS INT64), S.batter_id, S.pitcher_id, 
                CAST(S.launch_speed AS FLOAT64), CAST(S.launch_angle AS FLOAT64), CAST(S.launch_distance AS FLOAT64),
                CAST(S.hit_location AS INT64), S.hit_trajectory, S.hit_result, CAST(S.sprint_speed AS FLOAT64),
                S.is_barrel, S.is_hard_hit, S.raw, TIMESTAMP(S.loaded_at))
    """

    query_job = client.query(merge_query)
    query_job.result()

    # Clean up temp table
    client.delete_table(temp_table_id, not_found_ok=True)

    return len(df)


def upsert_mlb_standings(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB standings data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
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
        })

    df = pd.DataFrame(data)

    # Deduplicate by (team_id, season, standings_date)
    initial_count = len(df)
    df = df.drop_duplicates(subset=["team_id", "season", "standings_date"], keep="last")
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate standings records")

    table_id = f"{project_id}.raw.mlb_standings"
    temp_table_id = f"{table_id}_temp"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()

    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.team_id = S.team_id AND T.season = S.season AND T.standings_date = S.standings_date
    WHEN MATCHED THEN
        UPDATE SET
            league_id = CAST(S.league_id AS INT64),
            division_id = CAST(S.division_id AS INT64),
            division_rank = CAST(S.division_rank AS INT64),
            wins = CAST(S.wins AS INT64),
            losses = CAST(S.losses AS INT64),
            win_pct = CAST(S.win_pct AS FLOAT64),
            games_back = CAST(S.games_back AS FLOAT64),
            wildcard_games_back = CAST(S.wildcard_games_back AS FLOAT64),
            streak = S.streak,
            last_ten_record = S.last_ten_record,
            runs_scored = CAST(S.runs_scored AS INT64),
            runs_allowed = CAST(S.runs_allowed AS INT64),
            run_differential = CAST(S.run_differential AS INT64),
            home_wins = CAST(S.home_wins AS INT64),
            home_losses = CAST(S.home_losses AS INT64),
            away_wins = CAST(S.away_wins AS INT64),
            away_losses = CAST(S.away_losses AS INT64),
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (team_id, season, standings_date, league_id, division_id, division_rank,
                wins, losses, win_pct, games_back, wildcard_games_back,
                streak, last_ten_record, runs_scored, runs_allowed, run_differential,
                home_wins, home_losses, away_wins, away_losses, raw, loaded_at)
        VALUES (S.team_id, S.season, S.standings_date,
                CAST(S.league_id AS INT64), CAST(S.division_id AS INT64), CAST(S.division_rank AS INT64),
                CAST(S.wins AS INT64), CAST(S.losses AS INT64), CAST(S.win_pct AS FLOAT64),
                CAST(S.games_back AS FLOAT64), CAST(S.wildcard_games_back AS FLOAT64),
                S.streak, S.last_ten_record,
                CAST(S.runs_scored AS INT64), CAST(S.runs_allowed AS INT64), CAST(S.run_differential AS INT64),
                CAST(S.home_wins AS INT64), CAST(S.home_losses AS INT64),
                CAST(S.away_wins AS INT64), CAST(S.away_losses AS INT64),
                S.raw, TIMESTAMP(S.loaded_at))
    """

    query_job = client.query(merge_query)
    query_job.result()

    client.delete_table(temp_table_id, not_found_ok=True)

    return len(df)


def upsert_mlb_schedule(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB schedule data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data = []
    for r in rows:
        data.append({
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
            "home_probable_pitcher_id": str(r["home_probable_pitcher_id"]) if r.get("home_probable_pitcher_id") is not None else None,
            "home_probable_pitcher_name": r.get("home_probable_pitcher_name"),
            "away_probable_pitcher_id": str(r["away_probable_pitcher_id"]) if r.get("away_probable_pitcher_id") is not None else None,
            "away_probable_pitcher_name": r.get("away_probable_pitcher_name"),
            "scheduled_innings": r.get("scheduled_innings"),
            "series_description": r.get("series_description"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": dt.utcnow(),
        })

    df = pd.DataFrame(data)

    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id"], keep="last")
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate schedule records")

    table_id = f"{project_id}.raw.mlb_schedule"
    temp_table_id = f"{table_id}_temp"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()

    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.game_id = S.game_id
    WHEN MATCHED THEN
        UPDATE SET
            season = S.season,
            game_date = S.game_date,
            game_datetime = TIMESTAMP(S.game_datetime),
            game_type = S.game_type,
            status = S.status,
            day_night = S.day_night,
            venue_id = S.venue_id,
            venue_name = S.venue_name,
            home_team_id = S.home_team_id,
            away_team_id = S.away_team_id,
            home_probable_pitcher_id = S.home_probable_pitcher_id,
            home_probable_pitcher_name = S.home_probable_pitcher_name,
            away_probable_pitcher_id = S.away_probable_pitcher_id,
            away_probable_pitcher_name = S.away_probable_pitcher_name,
            scheduled_innings = S.scheduled_innings,
            series_description = S.series_description,
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (game_id, season, game_date, game_datetime, game_type, status, day_night,
                venue_id, venue_name, home_team_id, away_team_id,
                home_probable_pitcher_id, home_probable_pitcher_name,
                away_probable_pitcher_id, away_probable_pitcher_name,
                scheduled_innings, series_description, raw, loaded_at)
        VALUES (S.game_id, S.season, S.game_date, TIMESTAMP(S.game_datetime),
                S.game_type, S.status, S.day_night,
                S.venue_id, S.venue_name, S.home_team_id, S.away_team_id,
                S.home_probable_pitcher_id, S.home_probable_pitcher_name,
                S.away_probable_pitcher_id, S.away_probable_pitcher_name,
                S.scheduled_innings, S.series_description,
                S.raw, TIMESTAMP(S.loaded_at))
    """

    query_job = client.query(merge_query)
    query_job.result()

    client.delete_table(temp_table_id, not_found_ok=True)

    return len(df)


def upsert_mlb_game_broadcasts(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB game broadcast data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data = []
    for r in rows:
        data.append({
            "game_id": str(r["game_id"]),
            "broadcast_name": r["broadcast_name"],
            "broadcast_type": r.get("broadcast_type"),
            "call_sign": r.get("call_sign"),
            "is_national": r.get("is_national"),
            "home_away": r.get("home_away"),
            "language": r.get("language"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": dt.utcnow(),
        })

    df = pd.DataFrame(data)

    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "broadcast_name"], keep="last")
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate broadcast records")

    table_id = f"{project_id}.raw.mlb_game_broadcasts"
    temp_table_id = f"{table_id}_temp"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()

    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.game_id = S.game_id AND T.broadcast_name = S.broadcast_name
    WHEN MATCHED THEN
        UPDATE SET
            broadcast_type = S.broadcast_type,
            call_sign = S.call_sign,
            is_national = S.is_national,
            home_away = S.home_away,
            language = S.language,
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (game_id, broadcast_name, broadcast_type, call_sign, is_national,
                home_away, language, raw, loaded_at)
        VALUES (S.game_id, S.broadcast_name, S.broadcast_type, S.call_sign, S.is_national,
                S.home_away, S.language, S.raw, TIMESTAMP(S.loaded_at))
    """

    query_job = client.query(merge_query)
    query_job.result()

    client.delete_table(temp_table_id, not_found_ok=True)

    return len(df)


def upsert_mlb_game_lineups(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert MLB game lineup data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime as dt

    data = []
    for r in rows:
        data.append({
            "game_id": str(r["game_id"]),
            "player_id": str(r["player_id"]),
            "team_side": r["team_side"],
            "full_name": r["full_name"],
            "position_abbreviation": r.get("position_abbreviation"),
            "batting_order": r["batting_order"],
            "raw": json.dumps(r["raw"]),
            "loaded_at": dt.utcnow(),
        })

    df = pd.DataFrame(data)

    initial_count = len(df)
    df = df.drop_duplicates(subset=["game_id", "player_id", "team_side"], keep="last")
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate lineup records")

    table_id = f"{project_id}.raw.mlb_game_lineups"
    temp_table_id = f"{table_id}_temp"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    load_job = client.load_table_from_dataframe(df, temp_table_id, job_config=job_config)
    load_job.result()

    merge_query = f"""
    MERGE `{table_id}` T
    USING `{temp_table_id}` S
    ON T.game_id = S.game_id AND T.player_id = S.player_id AND T.team_side = S.team_side
    WHEN MATCHED THEN
        UPDATE SET
            full_name = S.full_name,
            position_abbreviation = S.position_abbreviation,
            batting_order = S.batting_order,
            raw = S.raw,
            loaded_at = TIMESTAMP(S.loaded_at)
    WHEN NOT MATCHED THEN
        INSERT (game_id, player_id, team_side, full_name, position_abbreviation,
                batting_order, raw, loaded_at)
        VALUES (S.game_id, S.player_id, S.team_side, S.full_name, S.position_abbreviation,
                S.batting_order, S.raw, TIMESTAMP(S.loaded_at))
    """

    query_job = client.query(merge_query)
    query_job.result()

    client.delete_table(temp_table_id, not_found_ok=True)

    return len(df)


# ============================================================================
# NBA BigQuery Functions
# ============================================================================

def ensure_nba_tables(client: bigquery.Client, project_id: str) -> None:
    """Ensure NBA tables exist in BigQuery with proper schema."""

    # Define schema for nba_teams
    teams_schema = [
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("team_city", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("conference_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("division_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("year_founded", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    teams_table_id = f"{project_id}.raw.nba_teams"
    teams_table = bigquery.Table(teams_table_id, schema=teams_schema)
    client.create_table(teams_table, exists_ok=True)

    # Define schema for nba_games
    games_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("season", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("season_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("game_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("away_team_id", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("home_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("away_score", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("arena", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("attendance", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    games_table_id = f"{project_id}.raw.nba_games"
    games_table = bigquery.Table(games_table_id, schema=games_schema)
    client.create_table(games_table, exists_ok=True)

    # Define schema for nba_player_game_stats
    player_stats_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("starter", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("minutes", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("field_goals_made", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("field_goals_attempted", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("field_goal_pct", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("three_pointers_made", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("three_pointers_attempted", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("three_point_pct", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("free_throws_made", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("free_throws_attempted", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("free_throw_pct", "FLOAT64", mode="NULLABLE"),
        bigquery.SchemaField("offensive_rebounds", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("defensive_rebounds", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("total_rebounds", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("assists", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("steals", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("blocks", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("turnovers", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("personal_fouls", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("points", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("plus_minus", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    player_stats_table_id = f"{project_id}.raw.nba_player_game_stats"
    player_stats_table = bigquery.Table(player_stats_table_id, schema=player_stats_schema)
    client.create_table(player_stats_table, exists_ok=True)

    # Define schema for nba_conferences
    conferences_schema = [
        bigquery.SchemaField("conference_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("conference_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("conference_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    conferences_table_id = f"{project_id}.raw.nba_conferences"
    conferences_table = bigquery.Table(conferences_table_id, schema=conferences_schema)
    client.create_table(conferences_table, exists_ok=True)

    # Define schema for nba_divisions
    divisions_schema = [
        bigquery.SchemaField("division_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("division_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("division_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("conference_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    divisions_table_id = f"{project_id}.raw.nba_divisions"
    divisions_table = bigquery.Table(divisions_table_id, schema=divisions_schema)
    client.create_table(divisions_table, exists_ok=True)

    # Define schema for nba_players
    players_schema = [
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("full_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("first_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("last_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("jersey_number", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("position", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("height", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("weight", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("birth_date", "DATE", mode="NULLABLE"),
        bigquery.SchemaField("country", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("draft_year", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("draft_round", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("draft_number", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("is_active", "BOOL", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    players_table_id = f"{project_id}.raw.nba_players"
    players_table = bigquery.Table(players_table_id, schema=players_schema)
    client.create_table(players_table, exists_ok=True)

    # Define schema for nba_shot_chart (individual shot details)
    shot_chart_schema = [
        bigquery.SchemaField("game_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("game_event_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("player_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("player_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("team_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("team_name", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("period", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("minutes_remaining", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("seconds_remaining", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("event_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("action_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("shot_type", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("shot_zone_basic", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("shot_zone_area", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("shot_zone_range", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("shot_distance", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("loc_x", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("loc_y", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("shot_attempted_flag", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("shot_made_flag", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("game_date", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("htm", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("vtm", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    shot_chart_table_id = f"{project_id}.raw.nba_shot_chart"
    shot_chart_table = bigquery.Table(shot_chart_table_id, schema=shot_chart_schema)
    client.create_table(shot_chart_table, exists_ok=True)


def upsert_nba_teams(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA teams data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
            "team_id": str(r["team_id"]),
            "team_name": r["team_name"],
            "team_abbr": r.get("team_abbr"),
            "team_city": r.get("team_city"),
            "conference_id": r.get("conference_id"),
            "division_id": r.get("division_id"),
            "year_founded": r.get("year_founded"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=['team_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate team records")

    table_id = f"{project_id}.raw.nba_teams"
    temp_table = f"{project_id}.raw._temp_nba_teams"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.team_id = S.team_id
    WHEN MATCHED THEN
      UPDATE SET
        team_name = S.team_name,
        team_abbr = S.team_abbr,
        team_city = S.team_city,
        conference_id = S.conference_id,
        division_id = S.division_id,
        year_founded = S.year_founded,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (team_id, team_name, team_abbr, team_city, conference_id, division_id, year_founded, raw, loaded_at)
      VALUES (S.team_id, S.team_name, S.team_abbr, S.team_city, S.conference_id, S.division_id, S.year_founded, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)


def upsert_nba_conferences(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA conferences data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
            "conference_id": int(r["conference_id"]),  # Explicitly cast to int
            "conference_name": r["conference_name"],
            "conference_abbr": r.get("conference_abbr"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    # Ensure proper dtypes for BigQuery schema (use lowercase int64, not nullable Int64)
    df['conference_id'] = df['conference_id'].astype('int64')

    initial_count = len(df)
    df = df.drop_duplicates(subset=['conference_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate conference records")

    table_id = f"{project_id}.raw.nba_conferences"
    temp_table = f"{project_id}.raw._temp_nba_conferences"

    # Define explicit schema for temp table to ensure correct types
    schema = [
        bigquery.SchemaField("conference_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("conference_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("conference_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=schema,
    )
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.conference_id = S.conference_id
    WHEN MATCHED THEN
      UPDATE SET
        conference_name = S.conference_name,
        conference_abbr = S.conference_abbr,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (conference_id, conference_name, conference_abbr, raw, loaded_at)
      VALUES (S.conference_id, S.conference_name, S.conference_abbr, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)


def upsert_nba_divisions(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA divisions data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
            "division_id": int(r["division_id"]),  # Explicitly cast to int
            "division_name": r["division_name"],
            "division_abbr": r.get("division_abbr"),
            "conference_id": int(r.get("conference_id")) if r.get("conference_id") is not None else None,
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    # Ensure proper dtypes for BigQuery schema (use lowercase int64)
    df['division_id'] = df['division_id'].astype('int64')
    # conference_id can be null, so handle it carefully
    if df['conference_id'].notna().any():
        df['conference_id'] = df['conference_id'].astype('Int64')  # Nullable integer

    initial_count = len(df)
    df = df.drop_duplicates(subset=['division_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate division records")

    table_id = f"{project_id}.raw.nba_divisions"
    temp_table = f"{project_id}.raw._temp_nba_divisions"

    # Define explicit schema for temp table to ensure correct types
    schema = [
        bigquery.SchemaField("division_id", "INT64", mode="REQUIRED"),
        bigquery.SchemaField("division_name", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("division_abbr", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("conference_id", "INT64", mode="NULLABLE"),
        bigquery.SchemaField("raw", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("loaded_at", "TIMESTAMP", mode="REQUIRED"),
    ]

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        schema=schema,
    )
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.division_id = S.division_id
    WHEN MATCHED THEN
      UPDATE SET
        division_name = S.division_name,
        division_abbr = S.division_abbr,
        conference_id = S.conference_id,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (division_id, division_name, division_abbr, conference_id, raw, loaded_at)
      VALUES (S.division_id, S.division_name, S.division_abbr, S.conference_id, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)


def upsert_nba_games(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA games data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
            "game_id": str(r["game_id"]),
            "season": r["season"],
            "season_type": r.get("season_type"),
            "game_date": r.get("game_date"),
            "status": r.get("status"),
            "home_team_id": str(r["home_team_id"]) if r.get("home_team_id") else None,
            "away_team_id": str(r["away_team_id"]) if r.get("away_team_id") else None,
            "home_score": r.get("home_score"),
            "away_score": r.get("away_score"),
            "arena": r.get("arena"),
            "attendance": r.get("attendance"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate game records")

    table_id = f"{project_id}.raw.nba_games"
    temp_table = f"{project_id}.raw._temp_nba_games"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id
    WHEN MATCHED THEN
      UPDATE SET
        season = S.season,
        season_type = S.season_type,
        game_date = S.game_date,
        status = S.status,
        home_team_id = S.home_team_id,
        away_team_id = S.away_team_id,
        home_score = S.home_score,
        away_score = S.away_score,
        arena = S.arena,
        attendance = S.attendance,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, season, season_type, game_date, status, home_team_id, away_team_id, home_score, away_score, arena, attendance, raw, loaded_at)
      VALUES (S.game_id, S.season, S.season_type, S.game_date, S.status, S.home_team_id, S.away_team_id, S.home_score, S.away_score, S.arena, S.attendance, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)


def upsert_nba_player_game_stats(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA player game stats data to BigQuery."""
    if not rows:
        return 0

    import json
    from datetime import datetime

    data = []
    for r in rows:
        data.append({
            "game_id": str(r["game_id"]),
            "player_id": str(r["player_id"]),
            "team_id": str(r["team_id"]),
            "player_name": r["player_name"],
            "starter": r.get("starter"),
            "minutes": r.get("minutes"),
            "field_goals_made": r.get("field_goals_made"),
            "field_goals_attempted": r.get("field_goals_attempted"),
            "field_goal_pct": r.get("field_goal_pct"),
            "three_pointers_made": r.get("three_pointers_made"),
            "three_pointers_attempted": r.get("three_pointers_attempted"),
            "three_point_pct": r.get("three_point_pct"),
            "free_throws_made": r.get("free_throws_made"),
            "free_throws_attempted": r.get("free_throws_attempted"),
            "free_throw_pct": r.get("free_throw_pct"),
            "offensive_rebounds": r.get("offensive_rebounds"),
            "defensive_rebounds": r.get("defensive_rebounds"),
            "total_rebounds": r.get("total_rebounds"),
            "assists": r.get("assists"),
            "steals": r.get("steals"),
            "blocks": r.get("blocks"),
            "turnovers": r.get("turnovers"),
            "personal_fouls": r.get("personal_fouls"),
            "points": r.get("points"),
            "plus_minus": r.get("plus_minus"),
            "raw": json.dumps(r["raw"]),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id', 'player_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate player stat records")

    table_id = f"{project_id}.raw.nba_player_game_stats"
    temp_table = f"{project_id}.raw._temp_nba_player_game_stats"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id AND T.player_id = S.player_id
    WHEN MATCHED THEN
      UPDATE SET
        team_id = S.team_id,
        player_name = S.player_name,
        starter = S.starter,
        minutes = S.minutes,
        field_goals_made = S.field_goals_made,
        field_goals_attempted = S.field_goals_attempted,
        field_goal_pct = S.field_goal_pct,
        three_pointers_made = S.three_pointers_made,
        three_pointers_attempted = S.three_pointers_attempted,
        three_point_pct = S.three_point_pct,
        free_throws_made = S.free_throws_made,
        free_throws_attempted = S.free_throws_attempted,
        free_throw_pct = S.free_throw_pct,
        offensive_rebounds = S.offensive_rebounds,
        defensive_rebounds = S.defensive_rebounds,
        total_rebounds = S.total_rebounds,
        assists = S.assists,
        steals = S.steals,
        blocks = S.blocks,
        turnovers = S.turnovers,
        personal_fouls = S.personal_fouls,
        points = S.points,
        plus_minus = S.plus_minus,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, player_id, team_id, player_name, starter, minutes, field_goals_made, field_goals_attempted, field_goal_pct,
              three_pointers_made, three_pointers_attempted, three_point_pct, free_throws_made, free_throws_attempted, free_throw_pct,
              offensive_rebounds, defensive_rebounds, total_rebounds, assists, steals, blocks, turnovers, personal_fouls, points, plus_minus, raw, loaded_at)
      VALUES (S.game_id, S.player_id, S.team_id, S.player_name, S.starter, S.minutes, S.field_goals_made, S.field_goals_attempted, S.field_goal_pct,
              S.three_pointers_made, S.three_pointers_attempted, S.three_point_pct, S.free_throws_made, S.free_throws_attempted, S.free_throw_pct,
              S.offensive_rebounds, S.defensive_rebounds, S.total_rebounds, S.assists, S.steals, S.blocks, S.turnovers, S.personal_fouls, S.points, S.plus_minus, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)


def upsert_nba_shot_chart(client: bigquery.Client, project_id: str, rows: Iterable[dict[str, Any]]) -> int:
    """Upsert NBA shot chart data to BigQuery.

    Individual shot attempts with location, type, and outcome.
    Similar to MLB Statcast data.
    """
    import pandas as pd
    from datetime import datetime
    from src.utils.logger import get_run_logger
    import json

    data = []
    for row in rows:
        data.append({
            "game_id": str(row["game_id"]),
            "game_event_id": row.get("game_event_id"),
            "player_id": str(row["player_id"]),
            "player_name": row.get("player_name"),
            "team_id": str(row["team_id"]),
            "team_name": row.get("team_name"),
            "period": row.get("period"),
            "minutes_remaining": row.get("minutes_remaining"),
            "seconds_remaining": row.get("seconds_remaining"),
            "event_type": row.get("event_type"),
            "action_type": row.get("action_type"),
            "shot_type": row.get("shot_type"),
            "shot_zone_basic": row.get("shot_zone_basic"),
            "shot_zone_area": row.get("shot_zone_area"),
            "shot_zone_range": row.get("shot_zone_range"),
            "shot_distance": row.get("shot_distance"),
            "loc_x": row.get("loc_x"),
            "loc_y": row.get("loc_y"),
            "shot_attempted_flag": row.get("shot_attempted_flag"),
            "shot_made_flag": row.get("shot_made_flag"),
            "game_date": row.get("game_date"),
            "htm": row.get("htm"),
            "vtm": row.get("vtm"),
            "raw": json.dumps(row.get("raw", {})),
            "loaded_at": datetime.utcnow(),
        })

    df = pd.DataFrame(data)
    initial_count = len(df)
    df = df.drop_duplicates(subset=['game_id', 'game_event_id'], keep='last')
    if initial_count > len(df):
        logger = get_run_logger()
        logger.warning(f"Removed {initial_count - len(df)} duplicate shot records")

    table_id = f"{project_id}.raw.nba_shot_chart"
    temp_table = f"{project_id}.raw._temp_nba_shot_chart"

    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(df, temp_table, job_config=job_config)
    job.result()

    merge_sql = f"""
    MERGE `{table_id}` T
    USING `{temp_table}` S
    ON T.game_id = S.game_id AND T.game_event_id = S.game_event_id
    WHEN MATCHED THEN
      UPDATE SET
        player_id = S.player_id,
        player_name = S.player_name,
        team_id = S.team_id,
        team_name = S.team_name,
        period = S.period,
        minutes_remaining = S.minutes_remaining,
        seconds_remaining = S.seconds_remaining,
        event_type = S.event_type,
        action_type = S.action_type,
        shot_type = S.shot_type,
        shot_zone_basic = S.shot_zone_basic,
        shot_zone_area = S.shot_zone_area,
        shot_zone_range = S.shot_zone_range,
        shot_distance = S.shot_distance,
        loc_x = S.loc_x,
        loc_y = S.loc_y,
        shot_attempted_flag = S.shot_attempted_flag,
        shot_made_flag = S.shot_made_flag,
        game_date = S.game_date,
        htm = S.htm,
        vtm = S.vtm,
        raw = S.raw,
        loaded_at = S.loaded_at
    WHEN NOT MATCHED THEN
      INSERT (game_id, game_event_id, player_id, player_name, team_id, team_name, period,
              minutes_remaining, seconds_remaining, event_type, action_type, shot_type,
              shot_zone_basic, shot_zone_area, shot_zone_range, shot_distance, loc_x, loc_y,
              shot_attempted_flag, shot_made_flag, game_date, htm, vtm, raw, loaded_at)
      VALUES (S.game_id, S.game_event_id, S.player_id, S.player_name, S.team_id, S.team_name, S.period,
              S.minutes_remaining, S.seconds_remaining, S.event_type, S.action_type, S.shot_type,
              S.shot_zone_basic, S.shot_zone_area, S.shot_zone_range, S.shot_distance, S.loc_x, S.loc_y,
              S.shot_attempted_flag, S.shot_made_flag, S.game_date, S.htm, S.vtm, S.raw, S.loaded_at)
    """

    query_job = client.query(merge_sql)
    query_job.result()
    client.delete_table(temp_table, not_found_ok=True)

    return len(data)
