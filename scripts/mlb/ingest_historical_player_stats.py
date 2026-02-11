"""Ingest historical MLB player stats for multiple seasons.

This script ingests player game-by-game statistics using the parallel ingestion
approach for optimal performance.

Example usage:
    # Default: last 20 years (2005-2024)
    python scripts/ingest_historical_player_stats.py
    
    # Specific range
    python scripts/ingest_historical_player_stats.py --start-year 2010 --end-year 2024
    
    # Single season
    python scripts/ingest_historical_player_stats.py --start-year 2024 --end-year 2024
    
    # Custom workers and game types
    python scripts/ingest_historical_player_stats.py --start-year 2020 --end-year 2024 --max-workers 30 --game-types R,F
"""

import argparse
import logging
import warnings
from datetime import date

from src.automations.prefect.mlb import mlb_player_stats_multi_season_ingestion_parallel


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for historical player stats ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB player game-by-game statistics for multiple seasons",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: last 20 years
  python scripts/ingest_historical_player_stats.py
  
  # Specific range
  python scripts/ingest_historical_player_stats.py --start-year 2010 --end-year 2024
  
  # Single season
  python scripts/ingest_historical_player_stats.py --start-year 2024 --end-year 2024
        """
    )
    
    current_year = date.today().year - 1  # Default to last completed season
    default_start_year = current_year - 19  # Last 20 years
    
    parser.add_argument(
        "--start-year",
        type=int,
        default=default_start_year,
        help=f"First season to ingest (default: {default_start_year})"
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=current_year,
        help=f"Last season to ingest, inclusive (default: {current_year})"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=20,
        help="Number of parallel workers (default: 20)"
    )
    parser.add_argument(
        "--game-types",
        type=str,
        default="R",
        help="Game types to ingest: R=regular, S=spring, F=wild card, etc. (default: R)"
    )
    
    args = parser.parse_args()
    
    # Validate year range
    if args.start_year > args.end_year:
        parser.error(f"start-year ({args.start_year}) cannot be greater than end-year ({args.end_year})")
    
    if args.start_year < 1900 or args.end_year > date.today().year:
        parser.error(f"Year range must be between 1900 and {date.today().year}")
    
    num_seasons = args.end_year - args.start_year + 1
    estimated_minutes = num_seasons * 3  # ~3 minutes per season with parallel
    
    print(f"\n{'='*80}")
    print(f"MLB Historical Player Stats Ingestion: {args.start_year}-{args.end_year}")
    print(f"{'='*80}\n")
    print(f"Seasons to ingest: {num_seasons}")
    print(f"Game types: {args.game_types}")
    print(f"Parallel workers: {args.max_workers}")
    print(f"Estimated time: ~{estimated_minutes} minutes\n")
    print(f"Starting ingestion...\n")
    
    result = mlb_player_stats_multi_season_ingestion_parallel(
        start_year=args.start_year,
        end_year=args.end_year,
        game_types=args.game_types,
        max_workers=args.max_workers,
    )
    
    print(f"\n{'='*80}")
    print(f"✅ Historical Ingestion Complete!")
    print(f"{'='*80}")
    print(f"Seasons processed: {result['seasons_processed']}")
    print(f"Total batting stats: {result['total_batting_stats']:,}")
    print(f"Total pitching stats: {result['total_pitching_stats']:,}")
    print(f"{'='*80}")
    print(f"Shutting down Prefect server...")
    print()


if __name__ == "__main__":
    main()

