"""MLB standings ingestion to BigQuery.

This module provides functions to fetch MLB standings data
and load them into BigQuery raw tables.

Supports:
- End-of-season standings (one snapshot per season)
- Historical weekly snapshots for division race tracking
- Current-date standings for live updates
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta
from typing import Any

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    ensure_mlb_tables,
    ensure_raw_dataset,
    get_client,
    upsert_mlb_standings,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def _standings_to_rows(records: list, standings_date: date) -> list[dict[str, Any]]:
    """Convert MlbStandingsRecord objects to row dicts for BigQuery."""
    rows = []
    for r in records:
        rows.append({
            "team_id": r.team_id,
            "season": r.season,
            "standings_date": standings_date,
            "league_id": r.league_id,
            "division_id": r.division_id,
            "division_rank": r.division_rank,
            "wins": r.wins,
            "losses": r.losses,
            "win_pct": r.win_pct,
            "games_back": r.games_back,
            "wildcard_games_back": r.wildcard_games_back,
            "streak": r.streak,
            "last_ten_record": r.last_ten_record,
            "runs_scored": r.runs_scored,
            "runs_allowed": r.runs_allowed,
            "run_differential": r.run_differential,
            "home_wins": r.home_wins,
            "home_losses": r.home_losses,
            "away_wins": r.away_wins,
            "away_losses": r.away_losses,
            "raw": r.raw,
        })
    return rows


def _fetch_standings_for_date(season: int, standings_date: date, retries: int = 2) -> tuple[date, list[dict[str, Any]] | None]:
    """Fetch standings for a single date with retry logic.
    
    Args:
        season: MLB season year
        standings_date: Date to fetch standings for
        retries: Number of retries on failure (default: 2)
        
    Returns:
        Tuple of (date, rows) where rows is None if fetch failed
    """
    api = MlbStatsApi()
    for attempt in range(retries):
        try:
            records = api.list_standings(season=season, standings_date=standings_date)
            if records:
                return standings_date, _standings_to_rows(records, standings_date)
            return standings_date, None
        except Exception:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            return standings_date, None


def ingest_standings_snapshot(
    *,
    season: int,
    standings_date: date | None = None,
) -> int:
    """Fetch MLB standings for a season (optionally as of a date) and load to BigQuery.

    Args:
        season: The MLB season year (e.g., 2024)
        standings_date: Optional date for historical snapshot. If None, fetches
                        end-of-season standings.

    Returns:
        Number of standings records inserted/updated.
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
    api = MlbStatsApi()

    logger.info(f"Fetching standings season={season} date={standings_date}")
    records = api.list_standings(season=season, standings_date=standings_date)

    if not records:
        logger.warning(f"No standings data returned for season={season} date={standings_date}")
        return 0

    # If no date provided, use the last day of the regular season
    effective_date = standings_date
    if effective_date is None:
        _, end_date = api.get_regular_season_bounds(season=season)
        effective_date = end_date or date(season, 10, 1)

    rows = _standings_to_rows(records, effective_date)

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")
    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted = upsert_mlb_standings(client, cfg.project_id, rows)
    logger.info(f"Standings ingest complete season={season} date={effective_date} records={inserted}")
    return inserted


def ingest_standings_historical(
    *,
    season: int,
    interval_days: int = 7,
    delay_seconds: float = 0.5,
) -> int:
    """Fetch weekly standings snapshots for an entire season.

    Takes snapshots every `interval_days` from opening day through end of
    regular season. Designed for historical backfill (2000-present).

    Args:
        season: The MLB season year
        interval_days: Days between snapshots (default: 7 = weekly)
        delay_seconds: Delay between API calls to avoid rate limiting

    Returns:
        Total number of standings records inserted/updated.
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
    api = MlbStatsApi()

    # Get season bounds
    start_date, end_date = api.get_regular_season_bounds(season=season)
    if start_date is None or end_date is None:
        logger.warning(f"Could not determine season bounds for {season}, using defaults")
        start_date = date(season, 4, 1)
        end_date = date(season, 10, 1)

    logger.info(
        f"Backfilling standings for season={season} "
        f"from {start_date} to {end_date} every {interval_days} days"
    )

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    total_inserted = 0
    current_date = start_date + timedelta(days=interval_days)
    snapshot_count = 0

    while current_date <= end_date:
        try:
            records = api.list_standings(season=season, standings_date=current_date)

            if records:
                rows = _standings_to_rows(records, current_date)
                inserted = upsert_mlb_standings(client, cfg.project_id, rows)
                total_inserted += inserted
                snapshot_count += 1

                if snapshot_count % 5 == 0:
                    logger.info(
                        f"Progress: {snapshot_count} snapshots, "
                        f"current_date={current_date}, total_records={total_inserted}"
                    )
            else:
                logger.warning(f"No standings data for {current_date}")

        except Exception as e:
            logger.warning(f"Failed to fetch standings for {current_date}: {e}")

        current_date += timedelta(days=interval_days)
        time.sleep(delay_seconds)

    # Always capture end-of-season final standings
    try:
        records = api.list_standings(season=season, standings_date=end_date)
        if records:
            rows = _standings_to_rows(records, end_date)
            inserted = upsert_mlb_standings(client, cfg.project_id, rows)
            total_inserted += inserted
            snapshot_count += 1
    except Exception as e:
        logger.warning(f"Failed to fetch final standings for {end_date}: {e}")

    logger.info(
        f"Historical standings complete season={season} "
        f"snapshots={snapshot_count} total_records={total_inserted}"
    )
    return total_inserted


def ingest_standings_historical_parallel(
    *,
    season: int,
    interval_days: int = 7,
    max_workers: int = 10,
) -> int:
    """Fetch weekly standings snapshots for an entire season using parallel processing.

    Much faster than ingest_standings_historical - fetches multiple dates concurrently.
    Takes snapshots every `interval_days` from opening day through end of regular season.

    Args:
        season: The MLB season year
        interval_days: Days between snapshots (default: 7 = weekly)
        max_workers: Maximum number of concurrent API calls (default: 10)

    Returns:
        Total number of standings records inserted/updated.
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
    api = MlbStatsApi()

    # Get season bounds
    start_date, end_date = api.get_regular_season_bounds(season=season)
    if start_date is None or end_date is None:
        logger.warning(f"Could not determine season bounds for {season}, using defaults")
        start_date = date(season, 4, 1)
        end_date = date(season, 10, 1)

    # Build list of dates to fetch
    dates_to_fetch = []
    current_date = start_date + timedelta(days=interval_days)
    while current_date <= end_date:
        dates_to_fetch.append(current_date)
        current_date += timedelta(days=interval_days)
    
    # Always include final day
    if end_date not in dates_to_fetch:
        dates_to_fetch.append(end_date)

    logger.info(
        f"Fetching {len(dates_to_fetch)} snapshots for season={season} "
        f"from {start_date} to {end_date} (parallel with {max_workers} workers)"
    )

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    chunk_size = max_workers * 2
    total_inserted = 0
    snapshot_count = 0

    for chunk_start in range(0, len(dates_to_fetch), chunk_size):
        chunk_end = min(chunk_start + chunk_size, len(dates_to_fetch))
        chunk = dates_to_fetch[chunk_start:chunk_end]

        # Submit parallel tasks
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_fetch_standings_for_date, season, dt): dt for dt in chunk}
            
            # Collect results and batch insert
            batch_rows = []
            for future in as_completed(futures):
                standings_date, rows = future.result()
                if rows:
                    batch_rows.extend(rows)
                    snapshot_count += 1
                else:
                    logger.warning(f"No standings data for {standings_date}")

        # Batch insert to BigQuery
        if batch_rows:
            inserted = upsert_mlb_standings(client, cfg.project_id, batch_rows)
            total_inserted += inserted

        if chunk_end % 20 == 0 or chunk_end == len(dates_to_fetch):
            logger.info(
                f"Progress: {snapshot_count}/{len(dates_to_fetch)} snapshots, "
                f"total_records={total_inserted}"
            )

    logger.info(
        f"PARALLEL historical standings complete season={season} "
        f"snapshots={snapshot_count} total_records={total_inserted}"
    )
    return total_inserted


def ingest_standings_bulk_historical(
    *,
    start_season: int = 2000,
    end_season: int = 2025,
    interval_days: int = 7,
    delay_seconds: float = 0.5,
    parallel: bool = True,
    max_workers: int = 10,
) -> dict[int, int]:
    """Backfill standings for multiple seasons.

    Args:
        start_season: First season to backfill (default: 2000)
        end_season: Last season to backfill (default: 2025)
        interval_days: Days between snapshots per season
        delay_seconds: Delay between API calls (only used if parallel=False)
        parallel: Use parallel processing for each season (default: True, much faster!)
        max_workers: Number of concurrent workers for parallel mode (default: 10)

    Returns:
        Dict mapping season -> number of records inserted.
    """
    logger = get_run_logger()
    results: dict[int, int] = {}

    for season in range(start_season, end_season + 1):
        logger.info(f"--- Starting season {season} ---")
        try:
            if parallel:
                # Use parallel version - MUCH faster!
                count = ingest_standings_historical_parallel(
                    season=season,
                    interval_days=interval_days,
                    max_workers=max_workers,
                )
            else:
                # Use sequential version with delays
                count = ingest_standings_historical(
                    season=season,
                    interval_days=interval_days,
                    delay_seconds=delay_seconds,
                )
            results[season] = count
            logger.info(f"Season {season} complete: {count} records")
        except Exception as e:
            logger.error(f"Season {season} failed: {e}")
            results[season] = 0

    total = sum(results.values())
    logger.info(f"Bulk historical standings complete: {total} total records across {len(results)} seasons")
    return results
