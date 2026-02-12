"""Ingest MLB standings data.

This script ingests MLB standings data for specified seasons.

Example usage:
    # Single season end-of-season standings
    python scripts/mlb/ingest_standings.py --season 2024
    
    # Single season with weekly snapshots (historical backfill)
    python scripts/mlb/ingest_standings.py --season 2024 --historical
    
    # Multiple seasons with weekly snapshots 
    python scripts/mlb/ingest_standings.py --start-season 2020 --end-season 2024
    
    # Adjust snapshot frequency (every 3 days instead of weekly)
    python scripts/mlb/ingest_standings.py --start-season 2020 --end-season 2024 --interval-days 3
    
    # Use sequential processing instead of parallel (slower but safer)
    python scripts/mlb/ingest_standings.py --start-season 2020 --end-season 2024 --no-parallel
    
    # Specific date snapshot
    python scripts/mlb/ingest_standings.py --season 2024 --date 2024-08-15
"""

import argparse
import logging
import warnings
from datetime import datetime

from src.automations.prefect.mlb import (
    mlb_standings_season_ingestion,
    mlb_standings_historical_ingestion,
    mlb_standings_multi_season_ingestion,
)


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for MLB standings ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB standings data to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Season selection
    parser.add_argument(
        "--season",
        type=int,
        help="Single season to ingest (e.g., 2024)",
    )
    parser.add_argument(
        "--start-season",
        type=int,
        help="Start season for multi-season ingestion (inclusive)",
    )
    parser.add_argument(
        "--end-season",
        type=int,
        help="End season for multi-season ingestion (inclusive)",
    )
    
    # Options
    parser.add_argument(
        "--date",
        type=str,
        help="Specific date for standings snapshot (YYYY-MM-DD). Only valid with --season.",
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Fetch weekly snapshots throughout the season (instead of just end-of-season)",
    )
    parser.add_argument(
        "--interval-days",
        type=int,
        default=7,
        help="Days between standings snapshots (default: 7 = weekly)",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=0.5,
        help="Delay between API calls (only used with --no-parallel, default: 0.5)",
    )
    parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel processing (slower but uses less resources)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum concurrent workers for parallel processing (default: 10)",
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.season and (args.start_season or args.end_season):
        parser.error("Cannot specify both --season and --start-season/--end-season")
    
    if not args.season and not (args.start_season and args.end_season):
        parser.error("Must specify either --season or both --start-season and --end-season")
    
    if args.date and not args.season:
        parser.error("--date can only be used with --season")
    
    if args.date and args.historical:
        parser.error("Cannot specify both --date and --historical")
    
    # Parse date if provided
    standings_date = None
    if args.date:
        try:
            standings_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"Invalid date format: {args.date}. Use YYYY-MM-DD")
    
    # Execute appropriate flow
    parallel = not args.no_parallel
    mode_str = "parallel" if parallel else "sequential"
    
    if args.season:
        if args.historical:
            # Historical snapshots for single season
            print(f"Ingesting historical standings for season {args.season} (every {args.interval_days} days, {mode_str})...")
            result = mlb_standings_historical_ingestion(
                season=args.season,
                interval_days=args.interval_days,
                delay_seconds=args.delay_seconds,
                parallel=parallel,
                max_workers=args.max_workers,
            )
            print(f"✓ Completed: {result['records']} records inserted")
        else:
            # Single season snapshot (end-of-season or specific date)
            date_str = f" as of {standings_date}" if standings_date else ""
            print(f"Ingesting standings for season {args.season}{date_str}...")
            result = mlb_standings_season_ingestion(
                season=args.season,
                standings_date=standings_date,
            )
            print(f"✓ Completed: {result['records']} records inserted")
    
    else:
        # Multi-season ingestion
        print(
            f"Ingesting standings for seasons {args.start_season}-{args.end_season} "
            f"(every {args.interval_days} days, {mode_str})..."
        )
        result = mlb_standings_multi_season_ingestion(
            start_season=args.start_season,
            end_season=args.end_season,
            interval_days=args.interval_days,
            delay_seconds=args.delay_seconds,
            parallel=parallel,
            max_workers=args.max_workers,
        )
        print(f"✓ Completed: {result['seasons_processed']} seasons, {result['total_records']} total records")
        print(f"  Seasons: {', '.join(map(str, result['seasons']))}")


if __name__ == "__main__":
    main()
