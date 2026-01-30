from __future__ import annotations

from datetime import date, timedelta

from prefect import flow

from cityscape.automations.ingest.mlb import ingest_mlb_season
from cityscape.integrations.mlb.statsapi import MlbStatsApi
from cityscape.utils.logger import get_run_logger


@flow(name="mlb-season-ingestion", log_prints=False)
def mlb_season_ingestion(*, season: int, game_types: str = "R") -> dict[str, int]:
    """Prefect flow that ingests MLB season data into Postgres.

    This wraps `ingest_mlb_season` so logs are attached to the Prefect run.
    """

    logger = get_run_logger()
    logger.info(f"Starting MLB ingestion season={season} game_types={game_types}")

    teams, games = ingest_mlb_season(season=season, game_types=game_types)

    logger.info(f"Finished MLB ingestion season={season} teams={teams} games={games}")
    return {"teams": teams, "games": games}


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

    teams, games = ingest_mlb_season(
        season=season,
        game_types=game_types,
        start_date=window_start,
        end_date=window_end,
    )

    return {
        "status": "ok",
        "teams": teams,
        "games": games,
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
        "results": results,
    }


if __name__ == "__main__":
    # Handy local invocation: `uv run python -m cityscape.automations.prefect.mlb`
    mlb_season_ingestion(season=2024)
