"""Ingest NBA data into BigQuery."""

from __future__ import annotations

from datetime import date

from src.integrations.nba import NbaStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_nba_tables,
    upsert_nba_teams,
    upsert_nba_games,
    upsert_nba_player_game_stats,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def ingest_nba_teams_bigquery() -> int:
    """Fetch NBA teams and land them into BigQuery raw.nba_teams table.

    Returns:
        Number of teams inserted/updated
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
    api = NbaStatsApi()

    logger.info("Fetching NBA teams")
    teams = api.list_teams()
    logger.info(f"Fetched {len(teams)} teams")

    # Prepare data rows for BigQuery
    team_rows = [
        {
            "team_id": t.team_id,
            "team_name": t.team_name,
            "team_abbr": t.team_abbr,
            "team_city": t.team_city,
            "conference_id": t.conference_id,
            "division_id": t.division_id,
            "year_founded": t.year_founded,
            "raw": t.raw,
        }
        for t in teams
    ]

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    inserted = upsert_nba_teams(client, cfg.project_id, team_rows)
    logger.info(f"Ingest complete teams={inserted}")

    return inserted


def ingest_nba_games_bigquery(
    *,
    season: int,
    season_type: str = "Regular Season",
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Fetch NBA games for a season and land them into BigQuery raw.nba_games table.

    Args:
        season: The NBA season year (e.g., 2024 for 2024-25 season)
        season_type: Season type (Regular Season, Playoffs, etc.)
        start_date: Optional start date to filter games
        end_date: Optional end date to filter games

    Returns:
        Number of games inserted/updated
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
    api = NbaStatsApi()

    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching NBA games season={season} season_type={season_type} start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching NBA games season={season} season_type={season_type}")

    games = api.list_games(
        season=season, season_type=season_type, start_date=start_date, end_date=end_date
    )

    logger.info(f"Fetched {len(games)} games")

    # Prepare data rows for BigQuery
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

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    inserted = upsert_nba_games(client, cfg.project_id, game_rows)
    logger.info(f"Ingest complete games={inserted}")

    return inserted


def ingest_nba_player_game_stats_bigquery(
    *,
    season: int,
    season_type: str = "Regular Season",
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Fetch NBA player game-by-game stats and land them into BigQuery raw tables.

    This fetches player statistics for each game in the specified
    season/date range and lands them into raw.nba_player_game_stats.

    Args:
        season: The NBA season year (e.g., 2024 for 2024-25 season)
        season_type: Season type (Regular Season, Playoffs, etc.)
        start_date: Optional start date to filter games
        end_date: Optional end date to filter games

    Returns:
        Number of player stat records inserted/updated
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
    api = NbaStatsApi()

    # First, get the list of games for the season/date range
    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching NBA games season={season} season_type={season_type} start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching NBA games season={season} season_type={season_type}")

    games = api.list_games(
        season=season, season_type=season_type, start_date=start_date, end_date=end_date
    )

    logger.info(f"Found {len(games)} games, fetching player stats for each game...")

    all_player_stats = []

    # Fetch player stats for each game
    for i, game in enumerate(games, 1):
        if i % 10 == 0:
            logger.info(f"Processing game {i}/{len(games)} (game_id={game.game_id})")

        try:
            player_stats = api.get_player_game_stats(game_id=game.game_id)
            all_player_stats.extend(player_stats)
        except Exception as e:
            logger.warning(f"Failed to fetch stats for game_id={game.game_id}: {e}")
            continue

    logger.info(f"Fetched {len(all_player_stats)} player stat records")

    # Prepare data rows for BigQuery
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
        for s in all_player_stats
    ]

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_nba_tables(client, cfg.project_id)

    inserted = upsert_nba_player_game_stats(client, cfg.project_id, stat_rows)
    logger.info(f"Ingest complete player_stats={inserted}")

    return inserted
