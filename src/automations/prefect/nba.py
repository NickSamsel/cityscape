"""Prefect flows for NBA data ingestion.

This module defines Prefect workflows for ingesting NBA team, game, and player
statistics data into BigQuery.
"""

from __future__ import annotations

from datetime import date

from prefect import flow, task
from prefect.task_runners import ConcurrentTaskRunner

from src.automations.ingest.nba_bigquery import (
    ingest_nba_teams_bigquery,
    ingest_nba_games_bigquery,
    ingest_nba_player_game_stats_bigquery,
)
from src.integrations.nba import NbaStatsApi
from src.utils.logger import get_run_logger
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_nba_tables,
    upsert_nba_teams,
    upsert_nba_games,
    upsert_nba_conferences,
    upsert_nba_divisions,
)
from src.utils.settings import get_settings


@flow(name="nba-season-ingestion", log_prints=False)
def nba_season_ingestion(
    *,
    season: int,
    season_type: str = "Regular Season",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, int]:
    """Prefect flow that ingests NBA season data into BigQuery.

    Args:
        season: The NBA season year (e.g., 2024 for 2024-25 season)
        season_type: Season type (Regular Season, Playoffs, etc.)
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        Dictionary with counts of teams, games, conferences, and divisions inserted
    """
    logger = get_run_logger()
    logger.info(
        f"Starting NBA ingestion season={season} season_type={season_type} "
        f"start_date={start_date} end_date={end_date}"
    )

    # Step 1: Ingest teams, conferences, and divisions (reference data)
    teams = ingest_nba_teams_bigquery()
    logger.info(f"Ingested {teams} teams")

    # Conferences and divisions
    api = NbaStatsApi()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )
    client = get_client(cfg)

    # Ingest conferences
    conferences_data = api.list_conferences()
    conference_rows = [
        {
            "conference_id": c.conference_id,
            "conference_name": c.conference_name,
            "conference_abbr": c.conference_abbr,
            "raw": c.raw,
        }
        for c in conferences_data
    ]
    conferences = upsert_nba_conferences(client, cfg.project_id, conference_rows)
    logger.info(f"Ingested {conferences} conferences")

    # Ingest divisions
    divisions_data = api.list_divisions()
    division_rows = [
        {
            "division_id": d.division_id,
            "division_name": d.division_name,
            "division_abbr": d.division_abbr,
            "conference_id": d.conference_id,
            "raw": d.raw,
        }
        for d in divisions_data
    ]
    divisions = upsert_nba_divisions(client, cfg.project_id, division_rows)
    logger.info(f"Ingested {divisions} divisions")

    # Step 2: Ingest games
    games = ingest_nba_games_bigquery(
        season=season,
        season_type=season_type,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(f"Ingested {games} games")

    # Step 3: Ingest player game stats
    player_stats = ingest_nba_player_game_stats_bigquery(
        season=season,
        season_type=season_type,
        start_date=start_date,
        end_date=end_date,
    )
    logger.info(f"Ingested {player_stats} player game stats")

    logger.info(
        f"Finished NBA ingestion season={season} teams={teams} games={games} "
        f"player_stats={player_stats} conferences={conferences} divisions={divisions}"
    )

    return {
        "teams": teams,
        "games": games,
        "player_stats": player_stats,
        "conferences": conferences,
        "divisions": divisions,
    }


@task(name="fetch-nba-season-data")
def fetch_nba_season_data_task(
    season: int,
    season_type: str = "Regular Season",
) -> dict[str, any]:
    """Task wrapper for fetching NBA season data (without writing to BigQuery).

    This allows parallel fetch operations without hitting BigQuery rate limits.

    Args:
        season: The NBA season year
        season_type: Season type (Regular Season, Playoffs, etc.)

    Returns:
        Dictionary with game rows for this season
    """
    logger = get_run_logger()
    logger.info(f"Fetching data for NBA season {season}")

    api = NbaStatsApi()

    # Fetch games
    games = api.list_games(season=season, season_type=season_type)

    game_rows = [
        {
            "game_id": g.game_id,
            "season": g.season,
            "season_type": g.season_type,
            "game_date": g.game_date,
            "status": g.status,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "arena": g.arena,
            "attendance": g.attendance,
            "raw": g.raw,
        }
        for g in games
    ]

    logger.info(f"Fetched season {season}: games={len(game_rows)}")
    return {
        "season": season,
        "game_rows": game_rows,
    }


@flow(
    name="nba-multi-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=10),
)
def nba_multi_season_ingestion_parallel(
    *,
    start_year: int,
    end_year: int,
    season_type: str = "Regular Season",
    max_workers: int = 10,
) -> dict[str, int | list]:
    """Ingest NBA teams and games for multiple seasons IN PARALLEL.

    Fetches data from multiple seasons concurrently, then performs a single batch
    write to BigQuery to avoid rate limits.

    Args:
        start_year: First season year to ingest
        end_year: Last season year to ingest (inclusive)
        season_type: Season type (default "Regular Season")
        max_workers: Number of concurrent seasons to fetch (default 10)

    Returns:
        Dictionary with summary statistics
    """
    logger = get_run_logger()
    logger.info(
        f"Starting PARALLEL NBA multi-season ingestion: {start_year} to {end_year} "
        f"with {max_workers} concurrent workers"
    )

    # Step 1: Ingest reference data (teams, conferences, divisions) - only need once
    logger.info("Ingesting NBA reference data (teams, conferences, divisions)...")
    teams = ingest_nba_teams_bigquery()

    api = NbaStatsApi()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )
    client = get_client(cfg)

    # Conferences
    conferences_data = api.list_conferences()
    conference_rows = [
        {
            "conference_id": c.conference_id,
            "conference_name": c.conference_name,
            "conference_abbr": c.conference_abbr,
            "raw": c.raw,
        }
        for c in conferences_data
    ]
    conferences = upsert_nba_conferences(client, cfg.project_id, conference_rows)

    # Divisions
    divisions_data = api.list_divisions()
    division_rows = [
        {
            "division_id": d.division_id,
            "division_name": d.division_name,
            "division_abbr": d.division_abbr,
            "conference_id": d.conference_id,
            "raw": d.raw,
        }
        for d in divisions_data
    ]
    divisions = upsert_nba_divisions(client, cfg.project_id, division_rows)

    logger.info(
        f"Reference data ingested: teams={teams}, conferences={conferences}, divisions={divisions}"
    )

    # Step 2: Fetch all season data in parallel
    seasons = list(range(start_year, end_year + 1))
    logger.info(f"Fetching data for {len(seasons)} seasons in parallel...")

    futures = fetch_nba_season_data_task.map(
        seasons, season_type=[season_type] * len(seasons)
    )

    # Wait for all futures to complete
    from prefect.futures import wait

    wait(futures)

    # Collect all results
    all_game_rows = []
    seasons_processed = []

    for future in futures:
        result = future.result()
        seasons_processed.append(result["season"])
        all_game_rows.extend(result["game_rows"])

    logger.info(
        f"Collected data from {len(seasons_processed)} seasons: "
        f"{len(all_game_rows)} game records"
    )

    # Step 3: Write all games to BigQuery in a single batch
    logger.info("Writing all games to BigQuery in batch...")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    inserted_games = upsert_nba_games(client, cfg.project_id, all_game_rows)

    logger.info(
        f"Completed PARALLEL NBA multi-season ingestion: {len(seasons_processed)} seasons, "
        f"{inserted_games} games written to BigQuery"
    )

    return {
        "seasons_processed": len(seasons_processed),
        "total_teams": teams,
        "total_games": inserted_games,
        "total_conferences": conferences,
        "total_divisions": divisions,
        "seasons": sorted(seasons_processed),
    }


@flow(name="nba-multi-season-ingestion", log_prints=False)
def nba_multi_season_ingestion(
    *,
    start_year: int,
    end_year: int,
    season_type: str = "Regular Season",
) -> dict[str, int | list]:
    """Ingest NBA data for multiple seasons SEQUENTIALLY.

    Args:
        start_year: First season year to ingest
        end_year: Last season year to ingest (inclusive)
        season_type: Season type (default "Regular Season")

    Returns:
        Dictionary with summary statistics
    """
    logger = get_run_logger()
    logger.info(f"Starting sequential NBA multi-season ingestion: {start_year} to {end_year}")

    results = []
    total_games = 0
    total_player_stats = 0

    for season in range(start_year, end_year + 1):
        logger.info(f"Processing season {season}...")
        result = nba_season_ingestion(season=season, season_type=season_type)

        total_games += result["games"]
        total_player_stats += result["player_stats"]
        results.append({"season": season, **result})

    logger.info(
        f"Completed sequential NBA multi-season ingestion: {len(results)} seasons, "
        f"{total_games} total games, {total_player_stats} total player stats"
    )

    return {
        "seasons_processed": len(results),
        "total_games": total_games,
        "total_player_stats": total_player_stats,
        "seasons": [r["season"] for r in results],
    }


@task(name="fetch-nba-player-stats-for-game")
def fetch_nba_player_stats_for_game_task(game_id: str) -> list[dict]:
    """Task wrapper for fetching player stats for a single game.

    Args:
        game_id: The NBA game ID

    Returns:
        List of player stat dictionaries
    """
    api = NbaStatsApi()
    try:
        player_stats = api.get_player_game_stats(game_id=game_id)
        return [
            {
                "game_id": s.game_id,
                "player_id": s.player_id,
                "team_id": s.team_id,
                "player_name": s.player_name,
                "starter": s.starter,
                "minutes": s.minutes,
                "field_goals_made": s.field_goals_made,
                "field_goals_attempted": s.field_goals_attempted,
                "field_goal_pct": s.field_goal_pct,
                "three_pointers_made": s.three_pointers_made,
                "three_pointers_attempted": s.three_pointers_attempted,
                "three_point_pct": s.three_point_pct,
                "free_throws_made": s.free_throws_made,
                "free_throws_attempted": s.free_throws_attempted,
                "free_throw_pct": s.free_throw_pct,
                "offensive_rebounds": s.offensive_rebounds,
                "defensive_rebounds": s.defensive_rebounds,
                "total_rebounds": s.total_rebounds,
                "assists": s.assists,
                "steals": s.steals,
                "blocks": s.blocks,
                "turnovers": s.turnovers,
                "personal_fouls": s.personal_fouls,
                "points": s.points,
                "plus_minus": s.plus_minus,
                "raw": s.raw,
            }
            for s in player_stats
        ]
    except Exception as e:
        logger = get_run_logger()
        logger.warning(f"Failed to fetch player stats for game_id={game_id}: {e}")
        return []


@flow(
    name="nba-player-stats-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=20),
)
def nba_player_stats_season_ingestion_parallel(
    *,
    season: int,
    season_type: str = "Regular Season",
    max_workers: int = 20,
) -> dict[str, int]:
    """Prefect flow that ingests NBA player stats in PARALLEL (much faster!).

    Uses concurrent task runner to fetch player stats from multiple games simultaneously.

    Args:
        season: The NBA season year
        season_type: Season type (default "Regular Season")
        max_workers: Number of concurrent workers (default 20)

    Returns:
        Dictionary with count of player stats inserted
    """
    logger = get_run_logger()
    logger.info(
        f"Starting PARALLEL NBA player stats ingestion season={season} season_type={season_type} "
        f"with {max_workers} concurrent workers"
    )

    # Step 1: Get all games for the season
    api = NbaStatsApi()
    games = api.list_games(season=season, season_type=season_type)
    game_ids = [g.game_id for g in games]

    logger.info(f"Found {len(game_ids)} games, fetching player stats in parallel...")

    # Step 2: Fetch player stats for all games in parallel
    futures = fetch_nba_player_stats_for_game_task.map(game_ids)

    # Wait for all futures to complete
    from prefect.futures import wait

    wait(futures)

    # Step 3: Collect all results
    all_player_stats = []
    for future in futures:
        result = future.result()
        all_player_stats.extend(result)

    logger.info(f"Collected {len(all_player_stats)} player stat records")

    # Step 4: Write to BigQuery
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )

    client = get_client(cfg)
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    from src.utils.bigquery import upsert_nba_player_game_stats

    inserted = upsert_nba_player_game_stats(client, cfg.project_id, all_player_stats)

    logger.info(f"Finished PARALLEL NBA player stats ingestion: {inserted} player stats inserted")

    return {"player_stats": inserted}


@task(name="fetch-nba-season-with-player-stats")
def fetch_nba_season_with_player_stats_task(
    season: int,
    season_type: str = "Regular Season",
) -> dict[str, any]:
    """Task wrapper for fetching NBA season data INCLUDING player stats (without writing to BigQuery).

    This allows full parallel fetch operations for both games and player stats.

    Args:
        season: The NBA season year
        season_type: Season type (Regular Season, Playoffs, etc.)

    Returns:
        Dictionary with game rows and player stats rows for this season
    """
    logger = get_run_logger()
    logger.info(f"Fetching games and player stats for NBA season {season}")

    api = NbaStatsApi()

    # Fetch games
    games = api.list_games(season=season, season_type=season_type)

    game_rows = [
        {
            "game_id": g.game_id,
            "season": g.season,
            "season_type": g.season_type,
            "game_date": g.game_date,
            "status": g.status,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "arena": g.arena,
            "attendance": g.attendance,
            "raw": g.raw,
        }
        for g in games
    ]

    # Fetch player stats AND shot data for all games
    all_player_stats = []
    all_shots = []
    for i, game in enumerate(games, 1):
        if i % 50 == 0:
            logger.info(f"Season {season}: Processing game {i}/{len(games)}")

        try:
            # Fetch player game stats
            player_stats = api.get_player_game_stats(game_id=game.game_id)
            stat_rows = [
                {
                    "game_id": s.game_id,
                    "player_id": s.player_id,
                    "team_id": s.team_id,
                    "player_name": s.player_name,
                    "starter": s.starter,
                    "minutes": s.minutes,
                    "field_goals_made": s.field_goals_made,
                    "field_goals_attempted": s.field_goals_attempted,
                    "field_goal_pct": s.field_goal_pct,
                    "three_pointers_made": s.three_pointers_made,
                    "three_pointers_attempted": s.three_pointers_attempted,
                    "three_point_pct": s.three_point_pct,
                    "free_throws_made": s.free_throws_made,
                    "free_throws_attempted": s.free_throws_attempted,
                    "free_throw_pct": s.free_throw_pct,
                    "offensive_rebounds": s.offensive_rebounds,
                    "defensive_rebounds": s.defensive_rebounds,
                    "total_rebounds": s.total_rebounds,
                    "assists": s.assists,
                    "steals": s.steals,
                    "blocks": s.blocks,
                    "turnovers": s.turnovers,
                    "personal_fouls": s.personal_fouls,
                    "points": s.points,
                    "plus_minus": s.plus_minus,
                    "raw": s.raw,
                }
                for s in player_stats
            ]
            all_player_stats.extend(stat_rows)

            # Fetch shot chart data (individual shots)
            shots = api.get_shot_chart_detail(game_id=game.game_id)
            shot_rows = [
                {
                    "game_id": shot.game_id,
                    "game_event_id": shot.game_event_id,
                    "player_id": shot.player_id,
                    "player_name": shot.player_name,
                    "team_id": shot.team_id,
                    "team_name": shot.team_name,
                    "period": shot.period,
                    "minutes_remaining": shot.minutes_remaining,
                    "seconds_remaining": shot.seconds_remaining,
                    "event_type": shot.event_type,
                    "action_type": shot.action_type,
                    "shot_type": shot.shot_type,
                    "shot_zone_basic": shot.shot_zone_basic,
                    "shot_zone_area": shot.shot_zone_area,
                    "shot_zone_range": shot.shot_zone_range,
                    "shot_distance": shot.shot_distance,
                    "loc_x": shot.loc_x,
                    "loc_y": shot.loc_y,
                    "shot_attempted_flag": shot.shot_attempted_flag,
                    "shot_made_flag": shot.shot_made_flag,
                    "game_date": shot.game_date,
                    "htm": shot.htm,
                    "vtm": shot.vtm,
                    "raw": shot.raw,
                }
                for shot in shots
            ]
            all_shots.extend(shot_rows)
        except Exception as e:
            logger.warning(f"Season {season}: Failed to fetch data for game_id={game.game_id}: {e}")
            continue

    logger.info(
        f"Fetched season {season}: games={len(game_rows)}, player_stats={len(all_player_stats)}, shots={len(all_shots)}"
    )
    return {
        "season": season,
        "game_rows": game_rows,
        "player_stats_rows": all_player_stats,
        "shot_rows": all_shots,
    }


@flow(
    name="nba-complete-multi-season-ingestion-parallel",
    log_prints=False,
    task_runner=ConcurrentTaskRunner(max_workers=15),
)
def nba_complete_multi_season_ingestion_parallel(
    *,
    start_year: int,
    end_year: int,
    season_type: str = "Regular Season",
    max_workers: int = 15,
) -> dict[str, int | list]:
    """FULLY PARALLEL NBA ingestion: teams, games, AND player stats for multiple seasons.

    This is the RECOMMENDED way to ingest historical NBA data. It processes multiple
    seasons concurrently, fetching both games and player stats in parallel, then
    performs a single batch write to BigQuery.

    Perfect for backfilling historical data (e.g., 1960-2024).

    Args:
        start_year: First season year to ingest (supports back to 1960)
        end_year: Last season year to ingest (inclusive)
        season_type: Season type (default "Regular Season")
        max_workers: Number of concurrent seasons to fetch (default 15)

    Returns:
        Dictionary with summary statistics

    Example:
        # Ingest all NBA data from 1960 to 2024
        result = nba_complete_multi_season_ingestion_parallel(
            start_year=1960,
            end_year=2024,
            max_workers=20
        )
    """
    logger = get_run_logger()
    logger.info(
        f"Starting COMPLETE PARALLEL NBA ingestion: {start_year} to {end_year} "
        f"({season_type}) with {max_workers} concurrent workers"
    )

    # Step 1: Ingest reference data (teams, conferences, divisions) - only need once
    logger.info("Ingesting NBA reference data (teams, conferences, divisions)...")
    teams = ingest_nba_teams_bigquery()

    api = NbaStatsApi()
    settings = get_settings()
    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )
    client = get_client(cfg)

    # Conferences
    conferences_data = api.list_conferences()
    conference_rows = [
        {
            "conference_id": c.conference_id,
            "conference_name": c.conference_name,
            "conference_abbr": c.conference_abbr,
            "raw": c.raw,
        }
        for c in conferences_data
    ]
    conferences = upsert_nba_conferences(client, cfg.project_id, conference_rows)

    # Divisions
    divisions_data = api.list_divisions()
    division_rows = [
        {
            "division_id": d.division_id,
            "division_name": d.division_name,
            "division_abbr": d.division_abbr,
            "conference_id": d.conference_id,
            "raw": d.raw,
        }
        for d in divisions_data
    ]
    divisions = upsert_nba_divisions(client, cfg.project_id, division_rows)

    logger.info(
        f"Reference data ingested: teams={teams}, conferences={conferences}, divisions={divisions}"
    )

    # Step 2: Fetch ALL data (games + player stats) for all seasons in parallel
    seasons = list(range(start_year, end_year + 1))
    logger.info(
        f"Fetching games AND player stats for {len(seasons)} seasons in parallel "
        f"(this may take a while for historical data)..."
    )

    futures = fetch_nba_season_with_player_stats_task.map(
        seasons, season_type=[season_type] * len(seasons)
    )

    # Wait for all futures to complete
    from prefect.futures import wait

    wait(futures)

    # Step 3: Collect all results
    all_game_rows = []
    all_player_stats_rows = []
    all_shot_rows = []
    seasons_processed = []

    for future in futures:
        result = future.result()
        seasons_processed.append(result["season"])
        all_game_rows.extend(result["game_rows"])
        all_player_stats_rows.extend(result["player_stats_rows"])
        all_shot_rows.extend(result["shot_rows"])

    logger.info(
        f"Collected data from {len(seasons_processed)} seasons: "
        f"{len(all_game_rows)} games, {len(all_player_stats_rows)} player stat records, "
        f"{len(all_shot_rows)} individual shots"
    )

    # Step 4: Write all data to BigQuery in batch operations
    logger.info("Writing all data to BigQuery in batches...")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    # Write games
    from src.utils.bigquery import upsert_nba_games, upsert_nba_player_game_stats, upsert_nba_shot_chart

    inserted_games = upsert_nba_games(client, cfg.project_id, all_game_rows)
    logger.info(f"Wrote {inserted_games} games to BigQuery")

    # Write player stats
    inserted_player_stats = upsert_nba_player_game_stats(
        client, cfg.project_id, all_player_stats_rows
    )
    logger.info(f"Wrote {inserted_player_stats} player stat records to BigQuery")

    # Write shot chart data
    inserted_shots = upsert_nba_shot_chart(client, cfg.project_id, all_shot_rows)
    logger.info(f"Wrote {inserted_shots} individual shots to BigQuery")

    logger.info(
        f"✅ Completed COMPLETE PARALLEL NBA ingestion: {len(seasons_processed)} seasons processed\n"
        f"   Teams: {teams:,}\n"
        f"   Games: {inserted_games:,}\n"
        f"   Player stats: {inserted_player_stats:,}\n"
        f"   Shot chart: {inserted_shots:,}\n"
        f"   Conferences: {conferences}\n"
        f"   Divisions: {divisions}"
    )

    return {
        "seasons_processed": len(seasons_processed),
        "total_teams": teams,
        "total_games": inserted_games,
        "total_player_stats": inserted_player_stats,
        "total_shots": inserted_shots,
        "total_conferences": conferences,
        "total_divisions": divisions,
        "seasons": sorted(seasons_processed),
    }


if __name__ == "__main__":
    # Handy local invocation: `uv run python -m src.automations.prefect.nba`
    nba_season_ingestion(season=2024)
