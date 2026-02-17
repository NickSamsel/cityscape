"""MLB schedule (with broadcasts and lineups) ingestion to BigQuery."""

from __future__ import annotations

from datetime import date

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_schedule,
    upsert_mlb_game_broadcasts,
    upsert_mlb_game_lineups,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


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

    inserted_schedule = upsert_mlb_schedule(client, cfg.project_id, schedule_rows)
    inserted_broadcasts = upsert_mlb_game_broadcasts(client, cfg.project_id, broadcast_rows)
    inserted_lineups = upsert_mlb_game_lineups(client, cfg.project_id, lineup_rows)

    logger.info(
        f"Ingest complete: schedule={inserted_schedule} broadcasts={inserted_broadcasts} "
        f"lineups={inserted_lineups}"
    )
    return inserted_schedule, inserted_broadcasts, inserted_lineups
