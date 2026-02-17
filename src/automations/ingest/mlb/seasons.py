"""MLB season data (teams, games, leagues, divisions) ingestion to BigQuery."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_games,
    upsert_mlb_teams,
    upsert_mlb_leagues,
    upsert_mlb_divisions,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def fetch_mlb_season_data(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[list[dict], list[dict]]:
    """Fetch MLB teams + games data for a season (without writing to BigQuery).

    Returns raw data dictionaries ready for BigQuery ingestion.

    Returns:
        Tuple of (team_rows, game_rows)
    """

    logger = get_run_logger()
    api = MlbStatsApi()

    logger.info(f"Fetching MLB teams season={season}")
    teams = api.list_teams(season=season)

    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching MLB games season={season} game_types={game_types} "
            f"start_date={start_date} end_date={end_date}"
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
            "venue_id": g.venue_id,
            "raw": g.raw,
        }
        for g in games
    ]

    logger.info(f"Fetched season={season} teams={len(team_rows)} games={len(game_rows)}")
    return team_rows, game_rows


def fetch_mlb_reference_data() -> tuple[list[dict], list[dict]]:
    """Fetch MLB reference data (leagues and divisions).

    Returns raw data dictionaries ready for BigQuery ingestion.

    Returns:
        Tuple of (league_rows, division_rows)
    """

    logger = get_run_logger()
    api = MlbStatsApi()

    logger.info("Fetching MLB leagues and divisions")
    leagues = api.list_leagues()
    divisions = api.list_divisions()

    league_rows = [
        {
            "league_id": lg.league_id,
            "league_name": lg.league_name,
            "league_abbr": lg.league_abbr,
            "raw": lg.raw,
        }
        for lg in leagues
    ]

    division_rows = [
        {
            "division_id": d.division_id,
            "division_name": d.division_name,
            "division_abbr": d.division_abbr,
            "league_id": d.league_id,
            "raw": d.raw,
        }
        for d in divisions
    ]

    logger.info(f"Fetched leagues={len(league_rows)} divisions={len(division_rows)}")
    return league_rows, division_rows


def ingest_mlb_season_bigquery(
    *,
    season: int,
    game_types: str = "R,F,D,L,W",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int, int, int]:
    """Fetch MLB teams + games + reference data for a season and land them into BigQuery raw tables.

    Lands into:
    - raw.mlb_teams
    - raw.mlb_games
    - raw.mlb_leagues
    - raw.mlb_divisions

    Returns:
        Tuple of (teams_count, games_count, leagues_count, divisions_count)
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

    # Fetch season data
    team_rows, game_rows = fetch_mlb_season_data(
        season=season,
        game_types=game_types,
        start_date=start_date,
        end_date=end_date
    )

    # Fetch reference data (leagues and divisions)
    league_rows, division_rows = fetch_mlb_reference_data()

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted_teams = upsert_mlb_teams(client, cfg.project_id, team_rows)
    inserted_games = upsert_mlb_games(client, cfg.project_id, game_rows)
    inserted_leagues = upsert_mlb_leagues(client, cfg.project_id, league_rows)
    inserted_divisions = upsert_mlb_divisions(client, cfg.project_id, division_rows)

    logger.info(
        f"Ingest complete season={season} teams={inserted_teams} games={inserted_games} "
        f"leagues={inserted_leagues} divisions={inserted_divisions}"
    )
    return inserted_teams, inserted_games, inserted_leagues, inserted_divisions


def ingest_mlb_multi_season_bigquery(
    *,
    start_year: int,
    end_year: int,
    game_types: str = "R,F,D,L,W",
    parallel: bool = False,
    max_workers: int = 10,
) -> dict[str, int | list[int]]:
    """Ingest MLB teams/games/leagues/divisions for a year range.

    This is the shared implementation for scripts and Prefect flows.
    It fetches per-season team/game rows (optionally in parallel) and performs
    a single batch write to BigQuery to reduce rate-limit pressure.
    """

    if start_year > end_year:
        raise ValueError(f"start_year ({start_year}) cannot be greater than end_year ({end_year})")

    logger = get_run_logger()
    settings = get_settings()

    seasons = list(range(start_year, end_year + 1))
    logger.info(
        f"Fetching MLB multi-season data seasons={start_year}..{end_year} "
        f"game_types={game_types} parallel={parallel}"
    )

    all_team_rows: list[dict] = []
    all_game_rows: list[dict] = []

    if parallel:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(fetch_mlb_season_data, season=s, game_types=game_types): s for s in seasons
            }
            for fut in as_completed(futures):
                season = futures[fut]
                team_rows, game_rows = fut.result()
                logger.info(f"Fetched season={season} teams={len(team_rows)} games={len(game_rows)}")
                all_team_rows.extend(team_rows)
                all_game_rows.extend(game_rows)
    else:
        for season in seasons:
            team_rows, game_rows = fetch_mlb_season_data(season=season, game_types=game_types)
            all_team_rows.extend(team_rows)
            all_game_rows.extend(game_rows)

    league_rows, division_rows = fetch_mlb_reference_data()

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )
    client = get_client(cfg)

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted_teams = upsert_mlb_teams(client, cfg.project_id, all_team_rows)
    inserted_games = upsert_mlb_games(client, cfg.project_id, all_game_rows)
    inserted_leagues = upsert_mlb_leagues(client, cfg.project_id, league_rows)
    inserted_divisions = upsert_mlb_divisions(client, cfg.project_id, division_rows)

    logger.info(
        f"Multi-season ingest complete seasons={start_year}..{end_year} teams={inserted_teams} "
        f"games={inserted_games} leagues={inserted_leagues} divisions={inserted_divisions}"
    )

    return {
        "seasons_processed": len(seasons),
        "total_teams": inserted_teams,
        "total_games": inserted_games,
        "total_leagues": inserted_leagues,
        "total_divisions": inserted_divisions,
        "seasons": seasons,
    }
