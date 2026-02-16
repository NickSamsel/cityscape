from __future__ import annotations

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
    upsert_mlb_schedule,
    upsert_mlb_game_broadcasts,
    upsert_mlb_game_lineups,
    upsert_mlb_venues,
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
    game_types: str = "R",
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


def ingest_mlb_schedule_bigquery(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int, int]:
    """Fetch MLB schedule (with venues, probable pitchers, broadcasts, lineups) and land into BigQuery.

    Lands into:
    - raw.mlb_schedule
    - raw.mlb_game_broadcasts
    - raw.mlb_game_lineups

    Returns:
        Tuple of (schedule_count, broadcasts_count, lineups_count)
    """

    logger = get_run_logger()
    settings = get_settings()
    api = MlbStatsApi()

    logger.info(
        f"Fetching MLB schedule season={season} game_types={game_types} "
        f"start_date={start_date} end_date={end_date}"
    )

    schedule_entries, broadcasts, lineup_entries = api.list_schedule(
        season=season,
        game_types=game_types,
        start_date=start_date,
        end_date=end_date,
    )

    logger.info(
        f"Fetched schedule={len(schedule_entries)} broadcasts={len(broadcasts)} "
        f"lineups={len(lineup_entries)}"
    )

    schedule_rows = [
        {
            "game_id": e.game_id,
            "season": e.season,
            "game_date": e.game_date,
            "game_datetime": e.game_datetime,
            "game_type": e.game_type,
            "status": e.status,
            "day_night": e.day_night,
            "venue_id": e.venue_id,
            "venue_name": e.venue_name,
            "home_team_id": e.home_team_id,
            "away_team_id": e.away_team_id,
            "home_probable_pitcher_id": e.home_probable_pitcher_id,
            "home_probable_pitcher_name": e.home_probable_pitcher_name,
            "away_probable_pitcher_id": e.away_probable_pitcher_id,
            "away_probable_pitcher_name": e.away_probable_pitcher_name,
            "scheduled_innings": e.scheduled_innings,
            "series_description": e.series_description,
            "raw": e.raw,
        }
        for e in schedule_entries
    ]

    broadcast_rows = [
        {
            "game_id": b.game_id,
            "broadcast_name": b.broadcast_name,
            "broadcast_type": b.broadcast_type,
            "call_sign": b.call_sign,
            "is_national": b.is_national,
            "home_away": b.home_away,
            "language": b.language,
            "raw": b.raw,
        }
        for b in broadcasts
    ]

    lineup_rows = [
        {
            "game_id": l.game_id,
            "player_id": l.player_id,
            "team_side": l.team_side,
            "full_name": l.full_name,
            "position_abbreviation": l.position_abbreviation,
            "batting_order": l.batting_order,
            "raw": l.raw,
        }
        for l in lineup_entries
    ]

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )

    client = get_client(cfg)
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    venue_ids = sorted({int(e.venue_id) for e in schedule_entries if e.venue_id is not None})
    if venue_ids:
        venues = api.list_venues(venue_ids=venue_ids, season=season)
        venue_rows = [
            {
                "venue_id": v.venue_id,
                "season": v.season,
                "venue_name": v.venue_name,
                "active": v.active,
                "city": v.city,
                "state": v.state,
                "state_abbrev": v.state_abbrev,
                "country": v.country,
                "latitude": v.latitude,
                "longitude": v.longitude,
                "capacity": v.capacity,
                "turf_type": v.turf_type,
                "roof_type": v.roof_type,
                "left_line": v.left_line,
                "right_line": v.right_line,
                "center": v.center,
                "left": v.left,
                "right": v.right,
                "left_center": v.left_center,
                "right_center": v.right_center,
                "raw": v.raw,
            }
            for v in venues
        ]
        inserted_venues = upsert_mlb_venues(client, cfg.project_id, venue_rows)
        logger.info(f"Upserted venues={inserted_venues}")

    inserted_schedule = upsert_mlb_schedule(client, cfg.project_id, schedule_rows)
    inserted_broadcasts = upsert_mlb_game_broadcasts(client, cfg.project_id, broadcast_rows)
    inserted_lineups = upsert_mlb_game_lineups(client, cfg.project_id, lineup_rows)

    logger.info(
        f"Ingest complete: schedule={inserted_schedule} broadcasts={inserted_broadcasts} "
        f"lineups={inserted_lineups}"
    )
    return inserted_schedule, inserted_broadcasts, inserted_lineups


def ingest_mlb_venues_bigquery(
    *,
    season: int,
    venue_ids: list[int] | None = None,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> int:
    """Ingest only MLB venue (ballpark) reference data into BigQuery.

    If `venue_ids` is not provided, the function derives venue IDs from the
    schedule within the provided date window.

    Lands into:
    - raw.mlb_venues

    Returns:
        Number of venue rows upserted
    """

    logger = get_run_logger()
    settings = get_settings()
    api = MlbStatsApi()

    resolved_venue_ids: list[int]
    if venue_ids is not None:
        resolved_venue_ids = sorted({int(v) for v in venue_ids})
    else:
        logger.info(
            f"Deriving venue IDs from schedule season={season} game_types={game_types} "
            f"start_date={start_date} end_date={end_date}"
        )
        schedule_entries, _, _ = api.list_schedule(
            season=season,
            game_types=game_types,
            start_date=start_date,
            end_date=end_date,
        )
        resolved_venue_ids = sorted({int(e.venue_id) for e in schedule_entries if e.venue_id is not None})

    if not resolved_venue_ids:
        logger.info("No venue IDs found; skipping venue ingestion")
        return 0

    logger.info(f"Fetching venues count={len(resolved_venue_ids)}")
    venues = api.list_venues(venue_ids=resolved_venue_ids, season=season)

    venue_rows = [
        {
            "venue_id": v.venue_id,
            "season": v.season,
            "venue_name": v.venue_name,
            "active": v.active,
            "city": v.city,
            "state": v.state,
            "state_abbrev": v.state_abbrev,
            "country": v.country,
            "latitude": v.latitude,
            "longitude": v.longitude,
            "capacity": v.capacity,
            "turf_type": v.turf_type,
            "roof_type": v.roof_type,
            "left_line": v.left_line,
            "right_line": v.right_line,
            "center": v.center,
            "left": v.left,
            "right": v.right,
            "left_center": v.left_center,
            "right_center": v.right_center,
            "raw": v.raw,
        }
        for v in venues
    ]

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )

    client = get_client(cfg)
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted_venues = upsert_mlb_venues(client, cfg.project_id, venue_rows)
    logger.info(f"Ingest complete: venues={inserted_venues}")
    return inserted_venues
