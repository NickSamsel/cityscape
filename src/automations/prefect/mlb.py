"""Prefect flows for MLB data ingestion.

This module defines Prefect workflows for ingesting MLB team, game, and player
statistics data into BigQuery.
"""

from __future__ import annotations

from datetime import date, timedelta

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.automations.ingest.mlb import (
    fetch_mlb_reference_data,
    fetch_mlb_season_data,
    get_unique_player_ids_from_bigquery,
    ingest_mlb_multi_season_bigquery,
    ingest_mlb_season_bigquery,
    ingest_mlb_statcast_data_bigquery,
    ingest_player_stats_parallel,
    ingest_player_stats_sequential,
    ingest_players_from_stats,
    ingest_players_parallel,
    ingest_standings_historical,
    ingest_standings_historical_parallel,
    ingest_standings_snapshot,
)
from src.integrations.mlb import MlbStatsApi
from src.utils.logger import get_run_logger
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_teams,
    upsert_mlb_games,
    upsert_mlb_leagues,
    upsert_mlb_divisions,
)
from src.utils.settings import get_settings


@flow(name="mlb-season-ingestion", log_prints=False)
def mlb_season_ingestion(*, season: int, game_types: str = "R") -> dict[str, int]:
    """Prefect flow that ingests MLB season data into BigQuery.

    This wraps `ingest_mlb_season_bigquery` so logs are attached to the Prefect run.
    """

    logger = get_run_logger()
    logger.info(f"Starting MLB ingestion season={season} game_types={game_types}")

    teams, games, leagues, divisions = ingest_mlb_season_bigquery(season=season, game_types=game_types)

    logger.info(
        f"Finished MLB ingestion season={season} teams={teams} games={games} "
        f"leagues={leagues} divisions={divisions}"
    )
    return {"teams": teams, "games": games, "leagues": leagues, "divisions": divisions}


@flow(name="mlb-daily-ingestion", log_prints=False)
def mlb_daily_ingestion(
    *,
    season: int,
    game_types: str = "R",
    lookback_days: int = 2,
) -> dict[str, int | str]:
    """Daily MLB ingestion.

    - Skips automatically until the regular season start date.
    - Loads a small rolling window (default 2 days) to handle late updates.
    """

    logger = get_run_logger()

    api = MlbStatsApi()
    start, end = api.get_regular_season_bounds(season=season)
    today = date.today()

    if start is not None and today < start:
        logger.info(f"Skipping: season {season} has not started yet (start={start}).")
        return {"status": "skipped_preseason", "season": season, "start": start.isoformat()}

    if end is not None and today > end + timedelta(days=14):
        logger.info(f"Skipping: season {season} appears finished (end={end}).")
        return {"status": "skipped_postseason", "season": season, "end": end.isoformat()}

    window_end = today
    window_start = today - timedelta(days=max(1, lookback_days))

    logger.info(
        f"Running MLB daily ingest season={season} game_types={game_types} window={window_start}..{window_end}"
    )

    teams, games, leagues, divisions = ingest_mlb_season_bigquery(
        season=season,
        game_types=game_types,
        start_date=window_start,
        end_date=window_end,
    )

    return {
        "status": "ok",
        "teams": teams,
        "games": games,
        "leagues": leagues,
        "divisions": divisions,
        "season": season,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }


@flow(name="mlb-multi-season-ingestion", log_prints=False)
def mlb_multi_season_ingestion(
    *,
    start_year: int,
    end_year: int,
    game_types: str = "R",
) -> dict[str, int | list]:
    """Ingest MLB data for multiple seasons from start_year to end_year (inclusive).

    Example: start_year=2020, end_year=2024 will ingest seasons 2020, 2021, 2022, 2023, 2024
    """

    return ingest_mlb_multi_season_bigquery(
        start_year=start_year,
        end_year=end_year,
        game_types=game_types,
        parallel=False,
    )


@task(name="fetch-single-season-data")
def fetch_single_season_data_task(season: int, game_types: str = "R") -> dict[str, any]:
    """Task wrapper for fetching MLB season data (without writing to BigQuery).
    
    This allows parallel fetch operations without hitting BigQuery rate limits.
    """
    logger = get_run_logger()
    logger.info(f"Fetching data for season {season}")
    
    team_rows, game_rows = fetch_mlb_season_data(season=season, game_types=game_types)
    
    logger.info(f"Fetched season {season}: teams={len(team_rows)}, games={len(game_rows)}")
    return {
        "season": season,
        "team_rows": team_rows,
        "game_rows": game_rows,
    }


@flow(
    name="mlb-multi-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
def mlb_multi_season_ingestion_parallel(
    *,
    start_year: int,
    end_year: int,
    game_types: str = "R",
    max_workers: int = 10,
) -> dict[str, int | list]:
    """Ingest MLB teams and games for multiple seasons IN PARALLEL.

    Fetches data from multiple seasons concurrently, then performs a single batch
    write to BigQuery to avoid rate limits.
    
    Example: start_year=2020, end_year=2024 will ingest seasons 2020, 2021, 2022, 2023, 2024
    
    Args:
        start_year: First season year to ingest
        end_year: Last season year to ingest (inclusive)
        game_types: Game type filter (default "R" for regular season)
        max_workers: Number of concurrent seasons to fetch (default 10)
    """

    return ingest_mlb_multi_season_bigquery(
        start_year=start_year,
        end_year=end_year,
        game_types=game_types,
        parallel=True,
        max_workers=max_workers,
    )


if __name__ == "__main__":
    # Handy local invocation: `uv run python -m cityscape.automations.prefect.mlb`
    mlb_season_ingestion(season=2024)


@flow(name="mlb-player-stats-season-ingestion", log_prints=False)
def mlb_player_stats_season_ingestion(*, season: int, game_types: str = "R") -> dict[str, int]:
    """Prefect flow that ingests MLB player game-by-game stats into BigQuery.

    This wraps `ingest_player_stats_sequential` so logs are attached to the Prefect run.
    """

    logger = get_run_logger()
    logger.info(f"Starting MLB player stats ingestion season={season} game_types={game_types}")

    batting_stats, pitching_stats = ingest_player_stats_sequential(season=season, game_types=game_types)

    logger.info(
        f"Finished MLB player stats ingestion season={season} batting={batting_stats} pitching={pitching_stats}"
    )
    return {"batting_stats": batting_stats, "pitching_stats": pitching_stats}


@flow(name="mlb-player-stats-daily-ingestion", log_prints=False)
def mlb_player_stats_daily_ingestion(
    *,
    season: int,
    game_types: str = "R",
    lookback_days: int = 2,
) -> dict[str, int | str]:
    """Daily MLB player stats ingestion.

    - Skips automatically until the regular season start date.
    - Loads a small rolling window (default 2 days) to handle late updates.
    """

    logger = get_run_logger()

    api = MlbStatsApi()
    start, end = api.get_regular_season_bounds(season=season)
    today = date.today()

    if start is not None and today < start:
        logger.info(f"Skipping: season {season} has not started yet (start={start}).")
        return {"status": "skipped_preseason", "season": season, "start": start.isoformat()}

    if end is not None and today > end + timedelta(days=14):
        logger.info(f"Skipping: season {season} appears finished (end={end}).")
        return {"status": "skipped_postseason", "season": season, "end": end.isoformat()}

    window_end = today
    window_start = today - timedelta(days=max(1, lookback_days))

    logger.info(
        f"Running MLB player stats daily ingest season={season} game_types={game_types} window={window_start}..{window_end}"
    )

    batting_stats, pitching_stats = ingest_player_stats_sequential(
        season=season,
        game_types=game_types,
        start_date=window_start,
        end_date=window_end,
    )

    return {
        "status": "ok",
        "batting_stats": batting_stats,
        "pitching_stats": pitching_stats,
        "season": season,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }


@flow(name="mlb-player-stats-multi-season-ingestion", log_prints=False)
def mlb_player_stats_multi_season_ingestion(
    *,
    start_year: int,
    end_year: int,
    game_types: str = "R",
) -> dict[str, int | list]:
    """Ingest MLB player stats for multiple seasons from start_year to end_year (inclusive).

    Example: start_year=2020, end_year=2024 will ingest seasons 2020, 2021, 2022, 2023, 2024
    """

    logger = get_run_logger()
    logger.info(f"Starting multi-season player stats ingestion: {start_year} to {end_year}")

    results = []
    total_batting_stats = 0
    total_pitching_stats = 0

    for season in range(start_year, end_year + 1):
        logger.info(f"Processing season {season}...")
        result = mlb_player_stats_season_ingestion(season=season, game_types=game_types)
        
        total_batting_stats += result["batting_stats"]
        total_pitching_stats += result["pitching_stats"]
        results.append({"season": season, **result})

    logger.info(
        f"Completed multi-season player stats ingestion: {len(results)} seasons, "
        f"{total_batting_stats} total batting stats, {total_pitching_stats} total pitching stats"
    )

    return {
        "seasons_processed": len(results),
        "total_batting_stats": total_batting_stats,
        "total_pitching_stats": total_pitching_stats,
        "results": results,
    }


# ============================================================================
# PARALLEL VERSIONS (using concurrent task runner for faster processing)
# ============================================================================


@flow(
    name="mlb-player-stats-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=20),
)
def mlb_player_stats_season_ingestion_parallel(
    *, season: int, game_types: str = "R,F,L,W", max_workers: int = 20
) -> dict[str, int]:
    """Prefect flow that ingests MLB player stats in PARALLEL (much faster!).

    Uses concurrent task runner to fetch player stats from multiple games simultaneously.
    Recommended for full season ingestion (~2,400 games).
    
    Args:
        season: The MLB season year
        game_types: Game type filter (default "R" for regular season)
        max_workers: Number of concurrent workers (default 20)
    """

    logger = get_run_logger()
    logger.info(
        f"Starting PARALLEL MLB player stats ingestion season={season} game_types={game_types} "
        f"with {max_workers} concurrent workers"
    )

    batting_stats, pitching_stats = ingest_player_stats_parallel(
        season=season, game_types=game_types
    )

    logger.info(
        f"Finished PARALLEL MLB player stats ingestion season={season} "
        f"batting={batting_stats} pitching={pitching_stats}"
    )
    return {"batting_stats": batting_stats, "pitching_stats": pitching_stats}


@flow(
    name="mlb-player-stats-daily-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
def mlb_player_stats_daily_ingestion_parallel(
    *,
    season: int,
    game_types: str = "R",
    lookback_days: int = 2,
    max_workers: int = 10,
) -> dict[str, int | str]:
    """Daily MLB player stats ingestion with PARALLEL processing.

    - Skips automatically until the regular season start date.
    - Loads a small rolling window (default 2 days) to handle late updates.
    - Uses parallel task execution for faster processing.
    """

    logger = get_run_logger()

    api = MlbStatsApi()
    start, end = api.get_regular_season_bounds(season=season)
    today = date.today()

    if start is not None and today < start:
        logger.info(f"Skipping: season {season} has not started yet (start={start}).")
        return {"status": "skipped_preseason", "season": season, "start": start.isoformat()}

    if end is not None and today > end + timedelta(days=14):
        logger.info(f"Skipping: season {season} appears finished (end={end}).")
        return {"status": "skipped_postseason", "season": season, "end": end.isoformat()}

    window_end = today
    window_start = today - timedelta(days=max(1, lookback_days))

    logger.info(
        f"Running PARALLEL MLB player stats daily ingest season={season} game_types={game_types} "
        f"window={window_start}..{window_end} with {max_workers} workers"
    )

    batting_stats, pitching_stats = ingest_player_stats_parallel(
        season=season,
        game_types=game_types,
        start_date=window_start,
        end_date=window_end,
    )

    return {
        "status": "ok",
        "batting_stats": batting_stats,
        "pitching_stats": pitching_stats,
        "season": season,
        "window_start": window_start.isoformat(),
        "window_end": window_end.isoformat(),
    }


@flow(
    name="mlb-player-stats-multi-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=20),
)
def mlb_player_stats_multi_season_ingestion_parallel(
    *,
    start_year: int,
    end_year: int,
    game_types: str = "R",
    max_workers: int = 20,
) -> dict[str, int | list]:
    """Ingest MLB player stats for multiple seasons with PARALLEL processing.

    Example: start_year=2020, end_year=2024 will ingest seasons 2020, 2021, 2022, 2023, 2024
    
    Args:
        start_year: First season year to ingest
        end_year: Last season year to ingest (inclusive)
        game_types: Game type filter (default "R")
        max_workers: Number of concurrent workers per season (default 20)
    """

    logger = get_run_logger()
    logger.info(
        f"Starting PARALLEL multi-season player stats ingestion: {start_year} to {end_year} "
        f"with {max_workers} workers"
    )

    results = []
    total_batting_stats = 0
    total_pitching_stats = 0

    for season in range(start_year, end_year + 1):
        logger.info(f"Processing season {season} in parallel...")
        result = mlb_player_stats_season_ingestion_parallel(
            season=season, game_types=game_types, max_workers=max_workers
        )
        
        total_batting_stats += result["batting_stats"]
        total_pitching_stats += result["pitching_stats"]
        results.append({"season": season, **result})

    logger.info(
        f"Completed PARALLEL multi-season player stats ingestion: {len(results)} seasons, "
        f"{total_batting_stats} total batting stats, {total_pitching_stats} total pitching stats"
    )

    return {
        "seasons_processed": len(results),
        "total_batting_stats": total_batting_stats,
        "total_pitching_stats": total_pitching_stats,
        "results": results,
    }


@flow(name="mlb-player-dimension-ingestion", log_prints=False)
def mlb_player_dimension_ingestion() -> dict[str, int]:
    """Ingest MLB player dimension data from existing player stats tables.

    This flow queries raw.mlb_player_batting_stats and raw.mlb_player_pitching_stats
    to find all unique player IDs, then fetches dimension data for each player
    and loads it into raw.mlb_players.

    Returns:
        Dictionary with the number of players loaded
    """
    logger = get_run_logger()
    logger.info("Starting MLB player dimension ingestion from stats tables")

    players_loaded = ingest_players_from_stats()

    logger.info(f"Finished MLB player dimension ingestion: {players_loaded} players loaded")
    return {"players": players_loaded}


@flow(
    name="mlb-player-dimension-ingestion-parallel",
    log_prints=False,
)
def mlb_player_dimension_ingestion_parallel(
    player_ids: list[int] | None = None,
    max_workers: int = 3,
) -> dict[str, int]:
    """Ingest MLB player dimension data with PARALLEL processing.

    Args:
        player_ids: Optional list of specific player IDs to fetch. If None, fetches all
                   unique players from stats tables.
        max_workers: Number of concurrent workers (default 50)

    Returns:
        Dictionary with the number of players loaded
    """
    logger = get_run_logger()
    
    if player_ids is None:
        logger.info("Querying BigQuery for unique player IDs from stats tables...")
        settings = get_settings()
        player_ids = list(get_unique_player_ids_from_bigquery(settings.gcp_project_id))
        logger.info(f"Found {len(player_ids)} unique players")
    else:
        logger.info(f"Processing {len(player_ids)} specified player IDs")

    logger.info(f"Starting PARALLEL MLB player dimension ingestion with {max_workers} workers")

    players_loaded = ingest_players_parallel(player_ids, max_workers=max_workers)

    logger.info(f"Finished PARALLEL MLB player dimension ingestion: {players_loaded} players loaded")
    return {"players": players_loaded}


@flow(name="mlb-statcast-ingestion", log_prints=False)
def mlb_statcast_ingestion(
    *,
    season: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    game_ids: list[int] | None = None,
    batch_size: int = 100,
    max_workers: int = 5,
) -> dict[str, int]:
    """Prefect flow that ingests MLB Statcast data into BigQuery with parallel processing.
    
    Args:
        season: MLB season year (used if game_ids not provided)
        start_date: Optional start date filter
        end_date: Optional end date filter
        game_ids: Specific game IDs to fetch Statcast data for
        batch_size: Number of games to process per batch (default: 100)
        max_workers: Number of concurrent threads for API calls (default: 5)
    
    Returns:
        Dictionary with counts of pitches and batted balls processed
    """
    
    logger = get_run_logger()
    logger.info(
        f"Starting MLB Statcast ingestion: season={season} "
        f"start_date={start_date} end_date={end_date} game_ids={game_ids} "
        f"batch_size={batch_size} max_workers={max_workers}"
    )

    pitches, batted_balls = ingest_mlb_statcast_data_bigquery(
        season=season,
        start_date=start_date,
        end_date=end_date,
        game_ids=game_ids,
        batch_size=batch_size,
        max_workers=max_workers,
    )
    
    logger.info(
        f"Finished MLB Statcast ingestion: "
        f"pitches={pitches:,} batted_balls={batted_balls:,}"
    )
    
    return {
        "pitches": pitches,
        "batted_balls": batted_balls,
    }


@flow(name="mlb-standings-season-ingestion", log_prints=False)
def mlb_standings_season_ingestion(
    *,
    season: int,
    standings_date: date | None = None,
) -> dict[str, int]:
    """Prefect flow that ingests MLB standings for a single season.
    
    Args:
        season: The MLB season year (e.g., 2024)
        standings_date: Optional date for historical snapshot. If None, fetches
                        end-of-season standings.
    
    Returns:
        Dictionary with count of standings records inserted
    """
    logger = get_run_logger()
    logger.info(f"Starting MLB standings ingestion: season={season} date={standings_date}")
    
    records = ingest_standings_snapshot(season=season, standings_date=standings_date)
    
    logger.info(f"Finished MLB standings ingestion: season={season} records={records}")
    return {"records": records, "season": season}


@flow(name="mlb-standings-historical-ingestion", log_prints=False)
def mlb_standings_historical_ingestion(
    *,
    season: int,
    interval_days: int = 7,
    delay_seconds: float = 0.5,
    parallel: bool = True,
    max_workers: int = 10,
) -> dict[str, int]:
    """Prefect flow that ingests weekly MLB standings snapshots for a season.
    
    Args:
        season: The MLB season year
        interval_days: Days between snapshots (default: 7 = weekly)
        delay_seconds: Delay between API calls (only used if parallel=False)
        parallel: Use parallel processing (default: True, much faster)
        max_workers: Max concurrent workers for parallel mode (default: 10)
    
    Returns:
        Dictionary with total records inserted
    """
    logger = get_run_logger()
    logger.info(
        f"Starting MLB historical standings ingestion: season={season} "
        f"interval_days={interval_days} parallel={parallel}"
    )
    
    if parallel:
        records = ingest_standings_historical_parallel(
            season=season,
            interval_days=interval_days,
            max_workers=max_workers,
        )
    else:
        records = ingest_standings_historical(
            season=season,
            interval_days=interval_days,
            delay_seconds=delay_seconds,
        )
    
    logger.info(f"Finished MLB historical standings ingestion: season={season} records={records}")
    return {"records": records, "season": season}


@flow(name="mlb-standings-multi-season-ingestion", log_prints=False)
def mlb_standings_multi_season_ingestion(
    *,
    start_season: int,
    end_season: int,
    interval_days: int = 7,
    delay_seconds: float = 0.5,
    parallel: bool = True,
    max_workers: int = 10,
) -> dict[str, int | list]:
    """Prefect flow that backfills standings for multiple seasons.
    
    Args:
        start_season: First season to backfill
        end_season: Last season to backfill (inclusive)
        interval_days: Days between snapshots per season
        delay_seconds: Delay between API calls (only used if parallel=False)
        parallel: Use parallel processing (default: True)
        max_workers: Max concurrent workers for parallel mode (default: 10)
    
    Returns:
        Dictionary with summary of seasons processed and total records
    """
    logger = get_run_logger()
    mode_str = "parallel" if parallel else "sequential"
    logger.info(
        f"Starting multi-season standings ingestion: {start_season} to {end_season} "
        f"(interval={interval_days} days, {mode_str})"
    )
    
    results = []
    total_records = 0
    
    for season in range(start_season, end_season + 1):
        logger.info(f"Processing season {season}...")
        try:
            result = mlb_standings_historical_ingestion(
                season=season,
                interval_days=interval_days,
                delay_seconds=delay_seconds,
                parallel=parallel,
                max_workers=max_workers,
            )
            total_records += result["records"]
            results.append({"season": season, "records": result["records"]})
        except Exception as e:
            logger.error(f"Season {season} failed: {e}")
            results.append({"season": season, "records": 0, "error": str(e)})
    
    logger.info(
        f"Completed multi-season standings ingestion: {len(results)} seasons, "
        f"{total_records} total records"
    )
    
    return {
        "seasons_processed": len(results),
        "total_records": total_records,
        "seasons": [r["season"] for r in results],
        "details": results,
    }

