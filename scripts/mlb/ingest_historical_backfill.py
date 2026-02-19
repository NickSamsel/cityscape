#!/usr/bin/env python3
"""Historical MLB data backfill script for multiple seasons.

This script orchestrates a complete historical backfill of MLB data using the
optimized roster-based workflow. It's designed for ingesting multiple seasons
at once (e.g., 2000-2026) with maximum efficiency.

WHAT THIS SCRIPT DOES:
1. Ingests rosters for all seasons (30 API calls per season)
2. Ingests teams and games for all seasons
3. Ingests standings for all seasons
4. Ingests schedule for all seasons
5. Ingests Statcast data (2015+ only, where available)
6. Ingests player dimension data from all rosters (once at the end)
7. Ingests venues (once, they're mostly static)

OPTIMIZATIONS:
- Uses roster-based player discovery (99.4% fewer API calls)
- Processes seasons sequentially to avoid rate limiting
- Batches player ingestion at the end (more efficient)
- Skips Statcast for seasons before 2015 (not available)

ESTIMATED TIME:
- ~30-60 seconds per season for roster + teams/games + standings + schedule
- ~2-5 minutes per season for Statcast (2015+)
- ~26 seasons (2000-2026) ≈ 30-90 minutes total

Usage:
    # Full historical backfill (2000-2026)
    uv run python scripts/mlb/ingest_historical_backfill.py

    # Specific range
    uv run python scripts/mlb/ingest_historical_backfill.py --start-year 2015 --end-year 2024

    # Skip Statcast (much faster)
    uv run python scripts/mlb/ingest_historical_backfill.py --skip-statcast

    # Skip venues (if already ingested)
    uv run python scripts/mlb/ingest_historical_backfill.py --skip-venues

    # Dry run to see what would be executed
    uv run python scripts/mlb/ingest_historical_backfill.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

# Allow running via: `python scripts/mlb/ingest_historical_backfill.py ...`
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.automations.ingest.mlb import (
    ingest_mlb_rosters_bigquery,
    ingest_mlb_schedule_bigquery,
    ingest_mlb_season_bigquery,
    ingest_mlb_statcast_data_bigquery,
    ingest_players_from_rosters,
    ingest_standings_bulk_historical,
)
from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mlb_historical_backfill")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Historical MLB data backfill for multiple seasons (optimized workflow)"
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=2000,
        help="First season to ingest (default: 2000)",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=date.today().year,
        help="Last season to ingest (default: current year)",
    )
    parser.add_argument(
        "--skip-statcast",
        action="store_true",
        help="Skip Statcast ingestion (much faster, but incomplete data for 2015+)",
    )
    parser.add_argument(
        "--skip-venues",
        action="store_true",
        help="Skip venue ingestion (if already loaded)",
    )
    parser.add_argument(
        "--skip-rosters",
        action="store_true",
        help="Skip roster ingestion (if already loaded)",
    )
    parser.add_argument(
        "--skip-teams-games",
        action="store_true",
        help="Skip teams and games ingestion (if already loaded)",
    )
    parser.add_argument(
        "--skip-standings",
        action="store_true",
        help="Skip standings ingestion (if already loaded)",
    )
    parser.add_argument(
        "--skip-schedule",
        action="store_true",
        help="Skip schedule ingestion (if already loaded)",
    )
    parser.add_argument(
        "--skip-players",
        action="store_true",
        help="Skip player dimension ingestion (if already loaded)",
    )
    parser.add_argument(
        "--game-types",
        type=str,
        default="R,F,D,L,W",
        help="Comma-separated game types (default: R,F,D,L,W for regular season + playoffs)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be executed without actually running",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    seasons = list(range(args.start_year, args.end_year + 1))
    total_seasons = len(seasons)

    logger.info("=" * 80)
    logger.info("MLB HISTORICAL BACKFILL - Optimized Roster-Based Workflow")
    logger.info("=" * 80)
    logger.info(f"Seasons: {args.start_year} to {args.end_year} ({total_seasons} total)")
    logger.info(f"Game types: {args.game_types}")
    logger.info(f"Statcast: {'SKIPPED' if args.skip_statcast else 'ENABLED (2015+ only)'}")
    logger.info("=" * 80)

    if args.dry_run:
        logger.info("DRY RUN MODE - No data will be ingested")
        logger.info("")
        logger.info("Would execute:")
        if not args.skip_rosters:
            logger.info(f"  1. Roster ingestion for {total_seasons} seasons")
        if not args.skip_teams_games:
            logger.info(f"  2. Teams & games ingestion for {total_seasons} seasons")
        if not args.skip_standings:
            logger.info(f"  3. Standings ingestion for {total_seasons} seasons")
        if not args.skip_schedule:
            logger.info(f"  4. Schedule ingestion for {total_seasons} seasons")
        if not args.skip_statcast:
            statcast_seasons = [s for s in seasons if s >= 2015]
            logger.info(f"  5. Statcast ingestion for {len(statcast_seasons)} seasons (2015+)")
        if not args.skip_players:
            logger.info(f"  6. Player dimension ingestion from rosters")
        if not args.skip_venues:
            logger.info(f"  7. Venue ingestion")
        return 0

    # Track progress
    completed_steps = []
    failed_steps = []

    # STEP 1: Ingest rosters for all seasons
    if not args.skip_rosters:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 1: ROSTER INGESTION (optimized - 30 API calls per season)")
        logger.info("=" * 80)
        for i, season in enumerate(seasons, 1):
            try:
                logger.info(f"[{i}/{total_seasons}] Ingesting rosters for {season}...")
                ingest_mlb_rosters_bigquery(
                    season=season,
                    parallel=True,  # Use parallel for speed
                    max_workers=5,
                )
                completed_steps.append(f"Rosters {season}")
            except Exception as e:
                logger.error(f"Failed to ingest rosters for {season}: {e}")
                failed_steps.append(f"Rosters {season}: {e}")
    else:
        logger.info("STEP 1: SKIPPED - Roster ingestion")

    # STEP 2: Ingest teams and games for all seasons
    if not args.skip_teams_games:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 2: TEAMS & GAMES INGESTION")
        logger.info("=" * 80)
        for i, season in enumerate(seasons, 1):
            try:
                logger.info(f"[{i}/{total_seasons}] Ingesting teams & games for {season}...")
                ingest_mlb_season_bigquery(
                    season=season,
                    game_types=args.game_types,
                )
                completed_steps.append(f"Teams & Games {season}")
            except Exception as e:
                logger.error(f"Failed to ingest teams & games for {season}: {e}")
                failed_steps.append(f"Teams & Games {season}: {e}")
    else:
        logger.info("STEP 2: SKIPPED - Teams & games ingestion")

    # STEP 3: Ingest standings for all seasons (bulk)
    if not args.skip_standings:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 3: STANDINGS INGESTION (BULK - PARALLEL MODE)")
        logger.info("=" * 80)
        try:
            logger.info(f"Ingesting standings for all seasons {args.start_year}-{args.end_year}...")
            results = ingest_standings_bulk_historical(
                start_season=args.start_year,
                end_season=args.end_year,
                interval_days=7,  # Weekly snapshots
                parallel=True,  # Use parallel processing - MUCH faster!
                max_workers=10,  # More workers for speed
            )
            total_records = sum(results.values())
            completed_steps.append(f"Standings (all seasons, {total_records} records)")
        except Exception as e:
            logger.error(f"Failed to ingest standings: {e}")
            failed_steps.append(f"Standings: {e}")
    else:
        logger.info("STEP 3: SKIPPED - Standings ingestion")

    # STEP 4: Ingest schedule for all seasons
    if not args.skip_schedule:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 4: SCHEDULE INGESTION")
        logger.info("=" * 80)
        for i, season in enumerate(seasons, 1):
            try:
                logger.info(f"[{i}/{total_seasons}] Ingesting schedule for {season}...")
                ingest_mlb_schedule_bigquery(season=season)
                completed_steps.append(f"Schedule {season}")
            except Exception as e:
                logger.error(f"Failed to ingest schedule for {season}: {e}")
                failed_steps.append(f"Schedule {season}: {e}")
    else:
        logger.info("STEP 4: SKIPPED - Schedule ingestion")

    # STEP 5: Ingest Statcast data (2015+ only)
    if not args.skip_statcast:
        statcast_seasons = [s for s in seasons if s >= 2015]
        if statcast_seasons:
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"STEP 5: STATCAST INGESTION ({len(statcast_seasons)} seasons, 2015+)")
            logger.info("=" * 80)
            for i, season in enumerate(statcast_seasons, 1):
                try:
                    logger.info(
                        f"[{i}/{len(statcast_seasons)}] Ingesting Statcast for {season}..."
                    )
                    pitches, balls = ingest_mlb_statcast_data_bigquery(
                        season=season,
                        batch_size=100,
                        max_workers=5,
                    )
                    completed_steps.append(f"Statcast {season} ({pitches} pitches, {balls} balls)")
                except Exception as e:
                    logger.error(f"Failed to ingest Statcast for {season}: {e}")
                    failed_steps.append(f"Statcast {season}: {e}")
        else:
            logger.info("STEP 5: SKIPPED - No seasons >= 2015 in range")
    else:
        logger.info("STEP 5: SKIPPED - Statcast ingestion")

    # STEP 6: Ingest player dimension data from rosters (once at the end)
    if not args.skip_players:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 6: PLAYER DIMENSION INGESTION (from rosters)")
        logger.info("=" * 80)
        try:
            logger.info(f"Ingesting player dimension data for seasons {args.start_year}-{args.end_year}...")
            ingest_players_from_rosters(seasons=seasons)
            completed_steps.append("Player Dimension")
        except Exception as e:
            logger.error(f"Failed to ingest player dimension data: {e}")
            failed_steps.append(f"Player Dimension: {e}")
    else:
        logger.info("STEP 6: SKIPPED - Player dimension ingestion")

    # STEP 7: Ingest venues (once, they're mostly static)
    if not args.skip_venues:
        logger.info("")
        logger.info("=" * 80)
        logger.info("STEP 7: VENUE INGESTION")
        logger.info("=" * 80)
        try:
            logger.info("Ingesting MLB venues...")
            ingest_mlb_venues_bigquery()
            completed_steps.append("Venues")
        except Exception as e:
            logger.error(f"Failed to ingest venues: {e}")
            failed_steps.append(f"Venues: {e}")
    else:
        logger.info("STEP 7: SKIPPED - Venue ingestion")

    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("BACKFILL COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Completed: {len(completed_steps)} tasks")
    logger.info(f"Failed: {len(failed_steps)} tasks")

    if failed_steps:
        logger.error("")
        logger.error("FAILED TASKS:")
        for step in failed_steps:
            logger.error(f"  ❌ {step}")
        return 1

    logger.info("")
    logger.info("✅ All tasks completed successfully!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Run dbt to transform the data:")
    logger.info("     dbt run")
    logger.info("")
    logger.info("  2. For daily updates, use:")
    logger.info("     uv run python scripts/mlb/daily_ingest.py --update-rosters-weekly")

    return 0


if __name__ == "__main__":
    sys.exit(main())
