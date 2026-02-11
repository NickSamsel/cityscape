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
