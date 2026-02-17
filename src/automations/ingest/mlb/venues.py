"""MLB venue (ballpark) reference data ingestion to BigQuery."""

from __future__ import annotations

from datetime import date

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_venues,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


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
