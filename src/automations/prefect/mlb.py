"""Prefect flows for MLB data ingestion.

This module defines Prefect workflows for ingesting MLB team, game, and player
statistics data into BigQuery.
"""

from __future__ import annotations

from datetime import date, timedelta

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.automations.ingest.mlb import (
    ingest_player_stats_parallel,
    ingest_player_stats_sequential,
)
from src.automations.ingest.mlb_bigquery import ingest_mlb_season_bigquery, fetch_mlb_season_data
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

    logger = get_run_logger()
    logger.info(f"Starting multi-season ingestion: {start_year} to {end_year}")

    results = []
    total_teams = 0
    total_games = 0

    for season in range(start_year, end_year + 1):
        logger.info(f"Processing season {season}...")
        result = mlb_season_ingestion(season=season, game_types=game_types)
        
        total_teams += result["teams"]
        total_games += result["games"]
        results.append({"season": season, **result})

    logger.info(
        f"Completed multi-season ingestion: {len(results)} seasons, "
        f"{total_teams} total teams, {total_games} total games"
    )

    return {
        "seasons_processed": len(results),
        "total_teams": total_teams,
        "total_games": total_games,
        "seasons": [r["season"] for r in results],
    }


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

    logger = get_run_logger()
    logger.info(
        f"Starting PARALLEL multi-season ingestion: {start_year} to {end_year} "
        f"with {max_workers} concurrent workers"
    )

    # Create list of seasons to process
    seasons = list(range(start_year, end_year + 1))
    
    # Fetch all season data in parallel
    logger.info(f"Fetching data for {len(seasons)} seasons in parallel...")
    futures = fetch_single_season_data_task.map(seasons, game_types=[game_types] * len(seasons))
    
    # Wait for all futures to complete
    from prefect.futures import wait
    wait(futures)
    
    # Collect all results
    all_team_rows = []
    all_game_rows = []
    seasons_processed = []
    
    for future in futures:
        result = future.result()
        seasons_processed.append(result["season"])
        all_team_rows.extend(result["team_rows"])
        all_game_rows.extend(result["game_rows"])
    
    logger.info(
        f"Collected data from {len(seasons_processed)} seasons: "
        f"{len(all_team_rows)} team records, {len(all_game_rows)} game records"
    )
    
    # Fetch reference data (leagues and divisions) - only need to do this once
    logger.info("Fetching reference data (leagues and divisions)...")
    from src.automations.ingest.mlb_bigquery import fetch_mlb_reference_data
    league_rows, division_rows = fetch_mlb_reference_data()
    
    # Now write all data to BigQuery in a single batch operation
    logger.info("Writing all data to BigQuery in batch...")
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
    )
    
    client = get_client(cfg)
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)
    
    inserted_teams = upsert_mlb_teams(client, cfg.project_id, all_team_rows)
    inserted_games = upsert_mlb_games(client, cfg.project_id, all_game_rows)
    inserted_leagues = upsert_mlb_leagues(client, cfg.project_id, league_rows)
    inserted_divisions = upsert_mlb_divisions(client, cfg.project_id, division_rows)
    
    logger.info(
        f"Completed PARALLEL multi-season ingestion: {len(seasons_processed)} seasons, "
        f"{inserted_teams} teams, {inserted_games} games, "
        f"{inserted_leagues} leagues, {inserted_divisions} divisions written to BigQuery"
    )

    return {
        "seasons_processed": len(seasons_processed),
        "total_teams": inserted_teams,
        "total_games": inserted_games,
        "total_leagues": inserted_leagues,
        "total_divisions": inserted_divisions,
        "seasons": sorted(seasons_processed),
    }


if __name__ == "__main__":
    # Handy local invocation: `uv run python -m cityscape.automations.prefect.mlb`
    mlb_season_ingestion(season=2024)


@flow(name="mlb-player-stats-season-ingestion", log_prints=False)
def mlb_player_stats_season_ingestion(*, season: int, game_types: str = "R") -> dict[str, int]:
    """Prefect flow that ingests MLB player game-by-game stats into BigQuery.

    This wraps `ingest_mlb_player_game_stats_bigquery` so logs are attached to the Prefect run.
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
    *, season: int, game_types: str = "R", max_workers: int = 20
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
