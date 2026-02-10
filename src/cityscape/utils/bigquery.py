from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Iterable

from google.cloud import bigquery
import pandas as pd


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    project_id: str
    location: str = "US"
    credentials_path: str | None = None


def get_client(cfg: BigQueryConfig) -> bigquery.Client:
    """Create BigQuery client with optional credentials."""
    if cfg.credentials_path:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = cfg.credentials_path
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
