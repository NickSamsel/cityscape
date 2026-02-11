"""MLB player statistics ingestion to BigQuery.

This module provides functions to fetch MLB player game-by-game statistics
and load them into BigQuery raw tables.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from prefect import task

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    ensure_mlb_tables,
    ensure_raw_dataset,
    get_client,
    upsert_mlb_player_batting_stats,
    upsert_mlb_player_pitching_stats,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


@task(retries=3, retry_delay_seconds=5)
def fetch_game_player_stats(game_id: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Fetch player stats for a single game (Prefect task for parallelization).
    
    Args:
        game_id: The MLB game ID to fetch stats for
        
    Returns:
        Tuple of (batting_rows, pitching_rows) as dictionaries
    """
    api = MlbStatsApi()
    logger = get_run_logger()
    
    try:
        batting_stats, pitching_stats = api.get_player_game_stats(game_id=game_id)
        
        batting_rows = [
            {
                "game_id": b.game_id,
                "player_id": b.player_id,
                "team_id": b.team_id,
                "player_name": b.player_name,
                "batting_order": b.batting_order,
                "position": b.position,
                "at_bats": b.at_bats,
                "runs": b.runs,
                "hits": b.hits,
                "doubles": b.doubles,
                "triples": b.triples,
                "home_runs": b.home_runs,
                "rbi": b.rbi,
                "stolen_bases": b.stolen_bases,
                "walks": b.walks,
                "strikeouts": b.strikeouts,
                "left_on_base": b.left_on_base,
                "avg": b.avg,
                "obp": b.obp,
                "slg": b.slg,
                "ops": b.ops,
                "raw": b.raw,
            }
            for b in batting_stats
        ]
        
        pitching_rows = [
            {
                "game_id": p.game_id,
                "player_id": p.player_id,
                "team_id": p.team_id,
                "player_name": p.player_name,
                "innings_pitched": p.innings_pitched,
                "hits": p.hits,
                "runs": p.runs,
                "earned_runs": p.earned_runs,
                "walks": p.walks,
                "strikeouts": p.strikeouts,
                "home_runs": p.home_runs,
                "pitches": p.pitches,
                "strikes": p.strikes,
                "era": p.era,
                "raw": p.raw,
            }
            for p in pitching_stats
        ]
        
        return batting_rows, pitching_rows
        
    except Exception as e:
        # Log error but don't fail the entire flow
        logger.warning(f"Failed to fetch stats for game_id={game_id}: {e}")
        return [], []


def ingest_player_stats_parallel(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int]:
    """Fetch MLB player stats for multiple games in parallel and load to BigQuery.
    
    This function uses Prefect task mapping to fetch player statistics from multiple
    games concurrently, significantly reducing total ingestion time.
    
    Args:
        season: The MLB season year (e.g., 2024)
        game_types: Game type filter (default "R" for regular season)
        start_date: Optional start date to filter games
        end_date: Optional end date to filter games
        
    Returns:
        Tuple of (batting_stats_count, pitching_stats_count)
    """
    logger = get_run_logger()
    settings = get_settings()

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
    )

    client = get_client(cfg)
    api = MlbStatsApi()

    # Fetch games for the season/date range
    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching MLB games season={season} game_types={game_types} "
            f"start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching MLB games season={season} game_types={game_types}")

    games = api.list_games(
        season=season, game_types=game_types, start_date=start_date, end_date=end_date
    )
    
    logger.info(f"Found {len(games)} games, fetching player stats in parallel...")

    # Extract game IDs for parallel processing
    game_ids = [game.game_id for game in games]
    
    # Fetch stats for all games in parallel using Prefect's task mapping
    logger.info(f"Starting parallel fetch of player stats for {len(game_ids)} games...")
    futures = fetch_game_player_stats.map(game_ids)
    
    # Wait for all futures to complete
    from prefect.futures import wait
    wait(futures)
    
    # Collect all results
    all_batting_rows = []
    all_pitching_rows = []
    
    for future in futures:
        batting_rows, pitching_rows = future.result()
        all_batting_rows.extend(batting_rows)
        all_pitching_rows.extend(pitching_rows)

    logger.info(
        f"Fetched {len(all_batting_rows)} batting stat records and "
        f"{len(all_pitching_rows)} pitching stat records"
    )

    # Ensure BigQuery tables exist
    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    # Upsert data to BigQuery
    inserted_batting = upsert_mlb_player_batting_stats(client, cfg.project_id, all_batting_rows)
    inserted_pitching = upsert_mlb_player_pitching_stats(client, cfg.project_id, all_pitching_rows)

    logger.info(
        f"Ingest complete season={season} batting_stats={inserted_batting} "
        f"pitching_stats={inserted_pitching}"
    )
    return inserted_batting, inserted_pitching


def ingest_player_stats_sequential(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int]:
    """Fetch MLB player stats sequentially and load to BigQuery.
    
    This is the sequential version of the ingestion. Use ingest_player_stats_parallel()
    for better performance when ingesting large date ranges.
    
    Args:
        season: The MLB season year (e.g., 2024)
        game_types: Game type filter (default "R" for regular season)
        start_date: Optional start date to filter games
        end_date: Optional end date to filter games
        
    Returns:
        Tuple of (batting_stats_count, pitching_stats_count)
    """
    logger = get_run_logger()
    settings = get_settings()

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
    )

    client = get_client(cfg)
    api = MlbStatsApi()

    # Fetch games for the season/date range
    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching MLB games season={season} game_types={game_types} "
            f"start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching MLB games season={season} game_types={game_types}")

    games = api.list_games(
        season=season, game_types=game_types, start_date=start_date, end_date=end_date
    )
    
    logger.info(f"Found {len(games)} games, fetching player stats sequentially...")

    all_batting_rows = []
    all_pitching_rows = []
    
    # Fetch stats sequentially for each game
    for i, game in enumerate(games, 1):
        if i % 100 == 0:
            logger.info(f"Processing game {i}/{len(games)}...")
            
        try:
            batting_stats, pitching_stats = api.get_player_game_stats(game_id=game.game_id)
            
            for b in batting_stats:
                all_batting_rows.append({
                    "game_id": b.game_id,
                    "player_id": b.player_id,
                    "team_id": b.team_id,
                    "player_name": b.player_name,
                    "batting_order": b.batting_order,
                    "position": b.position,
                    "at_bats": b.at_bats,
                    "runs": b.runs,
                    "hits": b.hits,
                    "doubles": b.doubles,
                    "triples": b.triples,
                    "home_runs": b.home_runs,
                    "rbi": b.rbi,
                    "stolen_bases": b.stolen_bases,
                    "walks": b.walks,
                    "strikeouts": b.strikeouts,
                    "left_on_base": b.left_on_base,
                    "avg": b.avg,
                    "obp": b.obp,
                    "slg": b.slg,
                    "ops": b.ops,
                    "raw": b.raw,
                })
            
            for p in pitching_stats:
                all_pitching_rows.append({
                    "game_id": p.game_id,
                    "player_id": p.player_id,
                    "team_id": p.team_id,
                    "player_name": p.player_name,
                    "innings_pitched": p.innings_pitched,
                    "hits": p.hits,
                    "runs": p.runs,
                    "earned_runs": p.earned_runs,
                    "walks": p.walks,
                    "strikeouts": p.strikeouts,
                    "home_runs": p.home_runs,
                    "pitches": p.pitches,
                    "strikes": p.strikes,
                    "era": p.era,
                    "raw": p.raw,
                })
                
        except Exception as e:
            logger.warning(f"Failed to fetch stats for game_id={game.game_id}: {e}")
            continue

    logger.info(
        f"Fetched {len(all_batting_rows)} batting stat records and "
        f"{len(all_pitching_rows)} pitching stat records"
    )

    # Ensure BigQuery tables exist
    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    # Upsert data to BigQuery
    inserted_batting = upsert_mlb_player_batting_stats(client, cfg.project_id, all_batting_rows)
    inserted_pitching = upsert_mlb_player_pitching_stats(client, cfg.project_id, all_pitching_rows)

    logger.info(
        f"Ingest complete season={season} batting_stats={inserted_batting} "
        f"pitching_stats={inserted_pitching}"
    )
    return inserted_batting, inserted_pitching
