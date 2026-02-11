from __future__ import annotations

from datetime import date

from src.integrations.mlb.statsapi import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_games,
    upsert_mlb_teams,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def ingest_mlb_season_bigquery(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int]:
    """Fetch MLB teams + games for a season and land them into BigQuery raw tables.

    Lands into:
    - raw.mlb_teams
    - raw.mlb_games
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

    logger.info(f"Fetching MLB teams season={season}")
    teams = api.list_teams(season=season)

    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching MLB games season={season} game_types={game_types} start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching MLB games season={season} game_types={game_types}")

    games = api.list_games(season=season, game_types=game_types, start_date=start_date, end_date=end_date)

    team_rows = [
        {
            "team_id": t.team_id,
            "season": season,
            "team_name": t.team_name,
            "team_abbr": t.team_abbr,
            "league_id": t.league_id,
            "division_id": t.division_id,
            "raw": t.raw,
        }
        for t in teams
    ]

    game_rows = [
        {
            "game_id": g.game_id,
            "season": g.season,
            "game_date": g.game_date,
            "game_type": g.game_type,
            "status": g.status,
            "home_team_id": g.home_team_id,
            "away_team_id": g.away_team_id,
            "home_score": g.home_score,
            "away_score": g.away_score,
            "raw": g.raw,
        }
        for g in games
    ]

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted_teams = upsert_mlb_teams(client, cfg.project_id, team_rows)
    inserted_games = upsert_mlb_games(client, cfg.project_id, game_rows)

    logger.info(f"Ingest complete season={season} teams={inserted_teams} games={inserted_games}")
    return inserted_teams, inserted_games
