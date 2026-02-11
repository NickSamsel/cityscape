"""Ingest MLB Statcast pitch and batted ball data.

This script fetches Statcast data (pitch velocity, spin rate, exit velocity, 
launch angle, etc.) for games and loads them into BigQuery.

Example usage:
    # Fetch Statcast data for 2024 season
    python scripts/mlb/ingest_statcast_data.py --season 2024
    
    # Fetch multiple seasons (2015-2023)
    python scripts/mlb/ingest_statcast_data.py --start-year 2015 --end-year 2023
    
    # Fetch for specific date range
    python scripts/mlb/ingest_statcast_data.py --season 2024 --start-date 2024-06-01 --end-date 2024-06-30
    
    # Fetch for specific game IDs
    python scripts/mlb/ingest_statcast_data.py --game-ids 717612,717613,717614
    
Note: Statcast data is only available from 2015 onwards.
"""

import argparse
import logging
import warnings
from datetime import date

from src.automations.prefect.mlb import mlb_statcast_ingestion


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("prefect.server.utilities.messaging.memory").setLevel(logging.ERROR)
logging.getLogger("prefect.task_runs").setLevel(logging.WARNING)
logging.getLogger("prefect.flow_runs").setLevel(logging.INFO)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for MLB Statcast data ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB Statcast data to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch Statcast data for 2024 season (default: 5 workers, 100 games/batch)
  python scripts/mlb/ingest_statcast_data.py --season 2024
  
  # Fetch multiple seasons (Statcast available 2015+)
  python scripts/mlb/ingest_statcast_data.py --start-year 2015 --end-year 2023
  
  # Faster with more parallel workers (10 threads)
  python scripts/mlb/ingest_statcast_data.py --season 2024 --max-workers 10
  
  # Conservative mode for low memory (fewer workers, smaller batches)
  python scripts/mlb/ingest_statcast_data.py --season 2024 --max-workers 3 --batch-size 50
  
  # Fetch for specific date range
  python scripts/mlb/ingest_statcast_data.py --season 2024 --start-date 2024-06-01 --end-date 2024-06-30
  
  # Fetch for specific game IDs with parallel processing
  python scripts/mlb/ingest_statcast_data.py --game-ids 717612,717613,717614 --max-workers 10
  
  # With verbose output
  python scripts/mlb/ingest_statcast_data.py --season 2024 --verbose
        """
    )
    
    # Create mutually exclusive group for single vs multi-season
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--season",
        type=int,
        help="MLB season year (e.g., 2024)"
    )
    mode_group.add_argument(
        "--start-year",
        type=int,
        help="First season for multi-season ingestion (Statcast available 2015+)"
    )
    
    parser.add_argument(
        "--end-year",
        type=int,
        help="Last season for multi-season ingestion (inclusive, used with --start-year)"
    )
    
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date in YYYY-MM-DD format"
    )
    
    parser.add_argument(
        "--game-ids",
        type=str,
        help="Comma-separated list of game IDs (e.g., 717612,717613)"
    )
    
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of games to process per batch (default: 100, helps with memory management)"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Number of concurrent threads for parallel API calls (default: 5, range: 1-20)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if args.start_date:
        start_date = date.fromisoformat(args.start_date)
    
    if args.end_date:
        end_date = date.fromisoformat(args.end_date)
    
    # Parse game IDs if provided
    game_ids = None
    if args.game_ids:
        game_ids = [int(gid.strip()) for gid in args.game_ids.split(",")]
    
    # Determine if multi-season mode
    is_multi_season = args.start_year is not None
    seasons = []
    
    # Validate inputs
    if is_multi_season:
        if not args.end_year:
            parser.error("--end-year is required when using --start-year")
        if args.start_year < 2015:
            parser.error("Statcast data is only available from 2015 onwards")
        if args.start_year > args.end_year:
            parser.error("--start-year must be less than or equal to --end-year")
        if args.start_date or args.end_date:
            parser.error("--start-date and --end-date cannot be used with multi-season mode")
        seasons = list(range(args.start_year, args.end_year + 1))
    elif not args.season and not game_ids:
        parser.error("Either --season, --start-year/--end-year, or --game-ids must be specified")
    elif args.season and args.season < 2015:
        print(f"⚠️  Warning: Statcast data is only available from 2015 onwards. Season {args.season} will have no data.")
    
    # Display header
    print(f"\n{'='*80}")
    print(f"MLB Statcast Data Ingestion")
    print(f"{'='*80}\n")
    
    if game_ids:
        print(f"Game IDs: {len(game_ids)} specified")
    elif is_multi_season:
        print(f"Seasons: {args.start_year}-{args.end_year} ({len(seasons)} seasons)")
        print(f"Years: {', '.join(map(str, seasons))}")
    else:
        print(f"Season: {args.season}")
        if start_date:
            print(f"Start date: {start_date}")
        if end_date:
            print(f"End date: {end_date}")
    
    print(f"\nStarting ingestion...\n")
    
    # Display processing info
    print(f"Batch size: {args.batch_size} games per batch")
    print(f"Parallel workers: {args.max_workers} concurrent threads")
    
    if args.batch_size > 200:
        print(f"⚠️  Warning: Large batch size may cause memory issues")
    if args.max_workers > 10:
        print(f"⚠️  Warning: Many workers may trigger API rate limits")
    
    # Run the flow
    try:
        if is_multi_season:
            # Process multiple seasons sequentially
            total_pitches = 0
            total_batted_balls = 0
            
            for season_num, season in enumerate(seasons, 1):
                print(f"\n{'='*80}")
                print(f"Processing Season {season} ({season_num}/{len(seasons)})")
                print(f"{'='*80}\n")
                
                result = mlb_statcast_ingestion(
                    season=season,
                    start_date=None,
                    end_date=None,
                    game_ids=None,
                    batch_size=args.batch_size,
                    max_workers=args.max_workers,
                )
                
                total_pitches += result['pitches']
                total_batted_balls += result['batted_balls']
                
                print(f"\nSeason {season} complete:")
                print(f"  Pitches: {result['pitches']:,}")
                print(f"  Batted balls: {result['batted_balls']:,}")
            
            # Display final results
            print(f"\n{'='*80}")
            print(f"✅ Multi-Season Statcast Data Ingestion Complete!")
            print(f"{'='*80}")
            print(f"Total pitches loaded: {total_pitches:,}")
            print(f"Total batted balls loaded: {total_batted_balls:,}")
            print(f"Seasons processed: {len(seasons)}")
            print(f"{'='*80}")
            print(f"Shutting down Prefect server...")
            print()
        else:
            # Single season or game IDs
            result = mlb_statcast_ingestion(
                season=args.season,
                start_date=start_date,
                end_date=end_date,
                game_ids=game_ids,
                batch_size=args.batch_size,
                max_workers=args.max_workers,
            )
            
            # Display results
            print(f"\n{'='*80}")
            print(f"✅ Statcast Data Ingestion Complete!")
            print(f"{'='*80}")
            print(f"Pitches loaded: {result['pitches']:,}")
            print(f"Batted balls loaded: {result['batted_balls']:,}")
            print(f"{'='*80}")
            print(f"Shutting down Prefect server...")
            print()
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}")
        raise


if __name__ == "__main__":
    main()
