"""MLB player dimension ingestion to BigQuery.

This module provides functions to fetch MLB player information
and load them into BigQuery raw tables.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    ensure_mlb_tables,
    ensure_raw_dataset,
    get_client,
    upsert_mlb_players,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def fetch_player_info(player_id: int, retries: int = 2) -> dict[str, Any] | None:
    """Fetch player information for a single player with retry logic.
    
    Args:
        player_id: The MLB player ID to fetch info for
        retries: Number of retries on failure (default: 2)
        
    Returns:
        Dictionary with player data, or None if fetch failed
    """
    api = MlbStatsApi()
    logger = get_run_logger()
    
    try:
        player = api.get_player_info(player_id=player_id)
        
        if player is None:
            logger.warning(f"No data found for player_id={player_id}")
            return None
        
        return {
            "player_id": player.player_id,
            "full_name": player.full_name,
            "first_name": player.first_name,
            "last_name": player.last_name,
            "primary_number": player.primary_number,
            "birth_date": player.birth_date,
            "current_age": player.current_age,
            "birth_city": player.birth_city,
            "birth_state_province": player.birth_state_province,
            "birth_country": player.birth_country,
            "height": player.height,
            "weight": player.weight,
            "primary_position_code": player.primary_position_code,
            "primary_position_name": player.primary_position_name,
            "primary_position_abbr": player.primary_position_abbr,
            "bat_side_code": player.bat_side_code,
            "bat_side_description": player.bat_side_description,
            "pitch_hand_code": player.pitch_hand_code,
            "pitch_hand_description": player.pitch_hand_description,
            "mlb_debut_date": player.mlb_debut_date,
            "active": player.active,
            "raw": player.raw,
        }
        
    except Exception as e:
        logger.warning(f"Failed to fetch info for player_id={player_id}: {e}")
        return None


def get_unique_player_ids_from_bigquery(project_id: str) -> set[int]:
    """Query BigQuery to get all unique player IDs from stats tables.
    
    Args:
        project_id: GCP project ID
        
    Returns:
        Set of unique player IDs
    """
    from google.cloud import bigquery
    
    logger = get_run_logger()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=project_id,
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key
    )
    
    client = get_client(cfg)
    
    # Query both batting and pitching stats tables
    query = f"""
    SELECT DISTINCT CAST(player_id AS INT64) as player_id
    FROM (
        SELECT player_id FROM `{project_id}.raw.mlb_player_batting_stats`
        UNION DISTINCT
        SELECT player_id FROM `{project_id}.raw.mlb_player_pitching_stats`
    )
    WHERE player_id IS NOT NULL
    ORDER BY player_id
    """
    
    logger.info("Querying BigQuery for unique player IDs...")
    query_job = client.query(query)
    results = query_job.result()
    
    player_ids = {row.player_id for row in results}
    logger.info(f"Found {len(player_ids)} unique players in stats tables")
    
    return player_ids


def ingest_players_from_stats(batch_size: int = 100) -> int:
    """Fetch player info for all players found in stats tables and load to BigQuery.

    Args:
        batch_size: Number of players to process in each BigQuery upsert batch

    Returns:
        Number of players successfully loaded
    """
    logger = get_run_logger()
    settings = get_settings()

    player_ids = get_unique_player_ids_from_bigquery(settings.gcp_project_id)

    if not player_ids:
        logger.warning("No player IDs found in stats tables")
        return 0

    return ingest_players_parallel(player_ids=sorted(player_ids), batch_size=batch_size)


def ingest_players_parallel(player_ids: list[int], batch_size: int = 100, max_workers: int = 10) -> int:
    """Fetch player info in parallel and load to BigQuery.

    Args:
        player_ids: List of player IDs to fetch
        batch_size: Number of players to process in each BigQuery upsert batch
        max_workers: Maximum number of concurrent workers (default 10)

    Returns:
        Number of players successfully loaded
    """
    logger = get_run_logger()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key
    )

    client = get_client(cfg)
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    logger.info(f"Fetching dimension data for {len(player_ids)} players (parallel with {max_workers} workers)...")

    all_player_rows = []
    total_failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_player_info, player_id): player_id for player_id in player_ids}

        for i, future in enumerate(as_completed(futures), 1):
            result = future.result()
            if result:
                all_player_rows.append(result)
            else:
                total_failed += 1
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{len(player_ids)} players fetched...")

    logger.info(f"Successfully fetched {len(all_player_rows)} players")
    if total_failed > 0:
        logger.warning(f"Failed to fetch {total_failed} players")

    if not all_player_rows:
        logger.warning("No player data to upload")
        return 0

    total_upserted = 0
    for i in range(0, len(all_player_rows), batch_size):
        batch = all_player_rows[i:i + batch_size]
        rows_upserted = upsert_mlb_players(client, cfg.project_id, batch)
        total_upserted += rows_upserted

    logger.info(f"Total upserted: {total_upserted} players to raw.mlb_players")
    return total_upserted


def ingest_players_from_rosters(season: int, batch_size: int = 100) -> int:
    """Fetch player info for all players found in roster table and load to BigQuery.

    Args:
        season: The MLB season year to fetch players for
        batch_size: Number of players to process in each BigQuery upsert batch

    Returns:
        Number of players successfully loaded
    """
    logger = get_run_logger()

    from .rosters import get_unique_player_ids_from_rosters
    player_ids = get_unique_player_ids_from_rosters(season=season)

    if not player_ids:
        logger.warning(f"No player IDs found in rosters for season {season}")
        return 0

    return ingest_players_parallel(player_ids=sorted(player_ids), batch_size=batch_size)
