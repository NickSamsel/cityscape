"""Ingest MLB teams and games data.

This script ingests MLB teams and games data for specified seasons.

Example usage:
    # Default: last completed season
    python scripts/mlb/ingest_teams_and_games.py
    
    # Specific season
    python scripts/mlb/ingest_teams_and_games.py --season 2024
    
    # Multiple seasons
    python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024
    
    # Multiple seasons with parallel processing (faster!)
    python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel
    
    Note: Parallel mode fetches data concurrently but writes in a single batch to avoid BigQuery rate limits.
    
    # Specific date range
    python scripts/mlb/ingest_teams_and_games.py --season 2024 --start-date 2024-04-01 --end-date 2024-04-30
    
    # Different game types (R=regular, S=spring, F=wild card, D=division, L=championship, W=world series)
    python scripts/mlb/ingest_teams_and_games.py --season 2024 --game-types R,F,D,L,W
"""

import argparse
import logging
import warnings
from datetime import date, datetime

from src.automations.prefect.mlb import (
    mlb_season_ingestion,
    mlb_multi_season_ingestion,
    mlb_multi_season_ingestion_parallel,
)


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for MLB teams and games ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB teams and games data to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: last completed season
  python scripts/mlb/ingest_teams_and_games.py
  
  # Specific season
  python scripts/mlb/ingest_teams_and_games.py --season 2024
  
  # Multiple seasons (sequential)
  python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024
  
  # Multiple seasons (parallel - much faster!)
  python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel
  
  # Specific date range within a season
  python scripts/mlb/ingest_teams_and_games.py --season 2024 --start-date 2024-04-01 --end-date 2024-04-30
        """
    )
    
    current_year = date.today().year - 1  # Default to last completed season
    
    # Create mutually exclusive group for single vs multi-season
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--season",
        type=int,
        help=f"Single season to ingest (default: {current_year})"
    )
    mode_group.add_argument(
        "--start-year",
        type=int,
        help="First season for multi-season ingestion"
    )
    
    parser.add_argument(
        "--end-year",
        type=int,
        help="Last season for multi-season ingestion (inclusive)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date for filtering games (YYYY-MM-DD), only valid with --season"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date for filtering games (YYYY-MM-DD), only valid with --season"
    )
    parser.add_argument(
        "--game-types",
        type=str,
        default="R",
        help="Game types to ingest: R=regular, S=spring, F=wild card, etc. (default: R)"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Number of concurrent workers for parallel multi-season ingestion (default: 10)"
    )
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use parallel processing for multi-season ingestion (much faster)"
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start_year and not args.end_year:
        parser.error("--end-year is required when --start-year is specified")
    
    if args.end_year and not args.start_year:
        parser.error("--start-year is required when --end-year is specified")
    
    if (args.start_date or args.end_date) and args.start_year:
        parser.error("Date filtering (--start-date, --end-date) is only valid with --season")
    
    # Parse dates if provided
    start_date = None
    end_date = None
    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"Invalid start date format: {args.start_date}. Use YYYY-MM-DD")
    
    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
        except ValueError:
            parser.error(f"Invalid end date format: {args.end_date}. Use YYYY-MM-DD")
    
    # Determine mode: multi-season or single season
    if args.start_year:
        # Multi-season mode
        if args.start_year > args.end_year:
            parser.error(f"start-year ({args.start_year}) cannot be greater than end-year ({args.end_year})")
        
        if args.start_year < 1900 or args.end_year > date.today().year:
            parser.error(f"Year range must be between 1900 and {date.today().year}")
        
        num_seasons = args.end_year - args.start_year + 1
        
        print(f"\n{'='*80}")
        print(f"MLB Teams & Games Ingestion: {args.start_year}-{args.end_year}")
        print(f"{'='*80}\n")
        print(f"Seasons to ingest: {num_seasons}")
        print(f"Game types: {args.game_types}")
        print(f"Processing mode: {'PARALLEL' if args.parallel else 'SEQUENTIAL'}")
        if args.parallel:
            print(f"Concurrent workers: {args.max_workers}")
        print(f"\nStarting ingestion...\n")
        
        if args.parallel:
            result = mlb_multi_season_ingestion_parallel(
                start_year=args.start_year,
                end_year=args.end_year,
                game_types=args.game_types,
                max_workers=args.max_workers,
            )
        else:
            result = mlb_multi_season_ingestion(
                start_year=args.start_year,
                end_year=args.end_year,
                game_types=args.game_types,
            )
        
        print(f"\n{'='*80}")
        print(f"✅ Multi-Season Ingestion Complete!")
        print(f"{'='*80}")
        print(f"Seasons processed: {len(result['seasons'])}")
        print(f"Total teams: {result['total_teams']:,}")
        print(f"Total games: {result['total_games']:,}")
        print(f"Total leagues: {result.get('total_leagues', 0):,}")
        print(f"Total divisions: {result.get('total_divisions', 0):,}")
        if args.parallel:
            print(f"\n💡 Parallel mode processed {num_seasons} seasons concurrently!")
            print(f"   Sequential would take ~{num_seasons * 7} seconds")
        print(f"{'='*80}")
        print(f"Shutting down Prefect server...")
        print()
        
    else:
        # Single season mode
        season = args.season if args.season else current_year
        
        print(f"\n{'='*80}")
        print(f"MLB Teams & Games Ingestion: {season}")
        print(f"{'='*80}\n")
        print(f"Season: {season}")
        print(f"Game types: {args.game_types}")
        if start_date or end_date:
            print(f"Date range: {start_date or 'season start'} to {end_date or 'season end'}")
        print(f"\nStarting ingestion...\n")
        
        # Note: The mlb_season_ingestion flow doesn't currently support date filtering
        # We would need to modify the flow or call the underlying function directly
        if start_date or end_date:
            print("⚠️  Note: Date filtering requires calling the function directly")
            from src.automations.ingest.mlb import ingest_mlb_season_bigquery
            teams, games, leagues, divisions = ingest_mlb_season_bigquery(
                season=season,
                game_types=args.game_types,
                start_date=start_date,
                end_date=end_date
            )
            result = {"teams": teams, "games": games, "leagues": leagues, "divisions": divisions}
        else:
            result = mlb_season_ingestion(season=season, game_types=args.game_types)
        
        print(f"\n{'='*80}")
        print(f"✅ Ingestion Complete!")
        print(f"{'='*80}")
        print(f"Teams: {result['teams']:,}")
        print(f"Games: {result['games']:,}")
        print(f"Leagues: {result.get('leagues', 0):,}")
        print(f"Divisions: {result.get('divisions', 0):,}")
        print(f"{'='*80}")
        print(f"Shutting down Prefect server...")
        print()


if __name__ == "__main__":
    main()
