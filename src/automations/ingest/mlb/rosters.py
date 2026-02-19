"""MLB roster ingestion to BigQuery.

This module provides functions to fetch MLB team rosters (team-player mappings)
and load them into BigQuery raw tables. Rosters provide an efficient way to
discover players and their team affiliations without iterating over game stats.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    ensure_mlb_tables,
    ensure_raw_dataset,
    get_client,
    upsert_mlb_rosters,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def fetch_team_roster(team_id: int, season: int) -> list[dict]:
    """Fetch roster for a single team and season.
    
    Args:
        team_id: The MLB team ID
        season: The MLB season year
        
    Returns:
        List of roster entry dictionaries
    """
    api = MlbStatsApi()
    logger = get_run_logger()
    
    try:
        roster_entries = api.get_roster(team_id=team_id, season=season)
        
        return [
            {
                "team_id": entry.team_id,
                "player_id": entry.player_id,
                "season": entry.season,
                "player_name": entry.player_name,
                "position_code": entry.position_code,
                "position_name": entry.position_name,
                "position_abbr": entry.position_abbr,
                "raw": entry.raw,
            }
            for entry in roster_entries
        ]
    except Exception as e:
        logger.warning(f"Failed to fetch roster for team_id={team_id}, season={season}: {e}")
        return []


def ingest_mlb_rosters_bigquery(
    *,
    season: int,
    team_ids: list[int] | None = None,
    parallel: bool = True,
    max_workers: int = 5,
) -> int:
    """Fetch MLB rosters for all teams in a season and load to BigQuery.
    
    This is far more efficient than deriving team-player relationships from game stats.
    For a full MLB season:
    - Roster approach: 30 API calls (one per team)
    - Game stats approach: 4,860+ API calls (one per game)
    
    Args:
        season: The MLB season year (e.g., 2024)
        team_ids: Optional list of specific team IDs to fetch. If None, fetches all teams.
        parallel: Whether to fetch rosters in parallel (default: True)
        max_workers: Number of concurrent workers for parallel mode (default: 5)
        
    Returns:
        Number of roster entries inserted
    """
    logger = get_run_logger()
    settings = get_settings()

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )

    client = get_client(cfg)
    api = MlbStatsApi()

    # Get team IDs if not provided
    if team_ids is None:
        logger.info(f"Fetching teams for season={season}")
        teams = api.list_teams(season=season)
        team_ids = [t.team_id for t in teams]
        logger.info(f"Found {len(team_ids)} teams")
    
    all_roster_rows = []
    
    if parallel:
        logger.info(f"Fetching rosters for {len(team_ids)} teams in parallel (max_workers={max_workers})...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(fetch_team_roster, team_id, season): team_id
                for team_id in team_ids
            }
            
            for future in as_completed(futures):
                team_id = futures[future]
                try:
                    roster_rows = future.result()
                    all_roster_rows.extend(roster_rows)
                    logger.debug(f"Fetched {len(roster_rows)} roster entries for team_id={team_id}")
                except Exception as e:
                    logger.warning(f"Error fetching roster for team_id={team_id}: {e}")
    else:
        logger.info(f"Fetching rosters for {len(team_ids)} teams sequentially...")
        for i, team_id in enumerate(team_ids, 1):
            if i % 10 == 0:
                logger.info(f"Processing team {i}/{len(team_ids)}...")
            roster_rows = fetch_team_roster(team_id, season)
            all_roster_rows.extend(roster_rows)

    logger.info(f"Fetched {len(all_roster_rows)} total roster entries")

    # Ensure BigQuery tables exist
    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    # Upsert roster data
    inserted = upsert_mlb_rosters(client, cfg.project_id, all_roster_rows)

    logger.info(f"Roster ingest complete: season={season} entries={inserted}")
    return inserted


def get_unique_player_ids_from_rosters(season: int) -> set[int]:
    """Query BigQuery to get all unique player IDs from roster table.
    
    This is more efficient than querying game stats tables when you just need
    to know which players are on teams.
    
    Args:
        season: The MLB season year
        
    Returns:
        Set of unique player IDs
    """
    from google.cloud import bigquery
    
    logger = get_run_logger()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key
    )
    
    client = get_client(cfg)
    
    query = f"""
    SELECT DISTINCT CAST(player_id AS INT64) as player_id
    FROM `{cfg.project_id}.raw.mlb_rosters`
    WHERE season = {season}
        AND player_id IS NOT NULL
    ORDER BY player_id
    """
    
    logger.info(f"Querying BigQuery for unique player IDs from rosters (season={season})...")
    query_job = client.query(query)
    results = query_job.result()
    
    player_ids = {row.player_id for row in results}
    logger.info(f"Found {len(player_ids)} unique players in rosters for season {season}")
    
    return player_ids
