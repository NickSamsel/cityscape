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
