from __future__ import annotations

from datetime import date

from cityscape.integrations.mlb.statsapi import MlbStatsApi
from cityscape.utils.db import (
    PostgresConfig,
    connect,
    ensure_mlb_tables,
    ensure_raw_schema,
    upsert_mlb_games,
    upsert_mlb_teams,
)
from cityscape.utils.logger import get_run_logger
from cityscape.utils.settings import get_settings


def ingest_mlb_season(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int]:
    """Fetch MLB teams + games for a season and land them into Postgres raw tables.

    Lands into:
    - raw.mlb_teams
    - raw.mlb_games
    """

    logger = get_run_logger()
    settings = get_settings()

    cfg = PostgresConfig(
        host=settings.postgres_host or "postgres",
        port=settings.postgres_port or 5432,
        user=settings.postgres_user or "postgres",
        password=settings.postgres_password or "postgres",
        dbname=settings.postgres_dbname or "cityscape",
    )

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

    logger.info(f"Connecting to Postgres host={cfg.host} port={cfg.port} dbname={cfg.dbname}")

    with connect(cfg) as conn:
        conn.autocommit = False
        ensure_raw_schema(conn)
        ensure_mlb_tables(conn)

        inserted_teams = upsert_mlb_teams(conn, team_rows)
        inserted_games = upsert_mlb_games(conn, game_rows)

        conn.commit()

    logger.info(f"Ingest complete season={season} teams={inserted_teams} games={inserted_games}")
    return inserted_teams, inserted_games
