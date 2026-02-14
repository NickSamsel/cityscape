"""Ingest NBA teams, games, and player stats data.

This script ingests NBA teams, games, and player game stats for specified seasons.
Supports historical data back to 1960!

Example usage:
    # Default: current season (teams + games + player stats)
    python scripts/nba/ingest_teams_and_games.py

    # Specific season
    python scripts/nba/ingest_teams_and_games.py --season 2024

    # Multiple seasons (sequential)
    python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024

    # Multiple seasons PARALLEL (RECOMMENDED - much faster!)
    # Ingests teams, games, AND player stats concurrently
    python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel

    # Historical backfill from 1960 to present
    python scripts/nba/ingest_teams_and_games.py --start-year 1960 --end-year 2024 --parallel --max-workers 20

    Note: Parallel mode fetches data concurrently but writes in a single batch to avoid BigQuery rate limits.

    # Regular season only (default)
    python scripts/nba/ingest_teams_and_games.py --season 2024 --season-type "Regular Season"

    # Include playoffs
    python scripts/nba/ingest_teams_and_games.py --season 2024 --season-type "Playoffs"

    # Games only (skip player stats for faster ingestion)
    python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel --games-only
"""

import argparse
import logging
import warnings
from datetime import date, datetime

from src.automations.prefect.nba import (
    nba_season_ingestion,
    nba_multi_season_ingestion,
    nba_multi_season_ingestion_parallel,
    nba_complete_multi_season_ingestion_parallel,
)


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for NBA teams and games ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest NBA teams, games, and player stats to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: current season
  python scripts/nba/ingest_teams_and_games.py

  # Specific season
  python scripts/nba/ingest_teams_and_games.py --season 2024

  # Multiple seasons (sequential)
  python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024

  # Multiple seasons PARALLEL (RECOMMENDED - much faster!)
  python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel

  # Historical backfill from 1960 to present
  python scripts/nba/ingest_teams_and_games.py --start-year 1960 --end-year 2024 --parallel --max-workers 20

  # Include playoffs
  python scripts/nba/ingest_teams_and_games.py --season 2024 --season-type "Playoffs"

  # Games only (skip player stats for faster ingestion)
  python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel --games-only
        """
    )

    current_year = date.today().year  # NBA seasons span two years, use current year

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
        "--season-type",
        type=str,
        default="Regular Season",
        help="Season type to ingest: Regular Season, Playoffs, etc. (default: Regular Season)"
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
    parser.add_argument(
        "--include-player-stats",
        action="store_true",
        default=True,
        help="Include player game stats in multi-season parallel mode (default: True)"
    )
    parser.add_argument(
        "--games-only",
        action="store_true",
        help="Skip player stats, only ingest teams and games (faster but incomplete)"
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

        if args.start_year < 1960 or args.end_year > date.today().year:
            parser.error(
                f"Year range must be between 1960 (earliest reliable NBA data) and {date.today().year}"
            )

        num_seasons = args.end_year - args.start_year + 1

        print(f"\n{'='*80}")
        print(f"NBA Teams, Games & Player Stats Ingestion: {args.start_year}-{args.end_year}")
        print(f"{'='*80}\n")
        print(f"Seasons to ingest: {num_seasons}")
        print(f"Season type: {args.season_type}")
        print(f"Processing mode: {'PARALLEL' if args.parallel else 'SEQUENTIAL'}")
        if args.parallel:
            print(f"Concurrent workers: {args.max_workers}")
        print(f"\nStarting ingestion...\n")

        if args.parallel:
            if args.games_only:
                # Games only (faster, no player stats)
                result = nba_multi_season_ingestion_parallel(
                    start_year=args.start_year,
                    end_year=args.end_year,
                    season_type=args.season_type,
                    max_workers=args.max_workers,
                )
            else:
                # Complete ingestion: games + player stats (recommended)
                result = nba_complete_multi_season_ingestion_parallel(
                    start_year=args.start_year,
                    end_year=args.end_year,
                    season_type=args.season_type,
                    max_workers=args.max_workers,
                )
        else:
            result = nba_multi_season_ingestion(
                start_year=args.start_year,
                end_year=args.end_year,
                season_type=args.season_type,
            )

        print(f"\n{'='*80}")
        print(f"✅ Multi-Season Ingestion Complete!")
        print(f"{'='*80}")
        print(f"Seasons processed: {len(result['seasons'])}")
        print(f"Total teams: {result.get('total_teams', 0):,}")
        print(f"Total games: {result.get('total_games', 0):,}")
        print(f"Total conferences: {result.get('total_conferences', 0):,}")
        print(f"Total divisions: {result.get('total_divisions', 0):,}")
        if 'total_player_stats' in result:
            print(f"Total player stats: {result['total_player_stats']:,}")
        if args.parallel:
            print(f"\n💡 Parallel mode processed {num_seasons} seasons concurrently!")
        print(f"{'='*80}")
        print(f"Shutting down Prefect server...")
        print()

    else:
        # Single season mode
        season = args.season if args.season else current_year

        print(f"\n{'='*80}")
        print(f"NBA Teams, Games & Player Stats Ingestion: {season}")
        print(f"{'='*80}\n")
        print(f"Season: {season}")
        print(f"Season type: {args.season_type}")
        if start_date or end_date:
            print(f"Date range: {start_date or 'season start'} to {end_date or 'season end'}")
        print(f"\nStarting ingestion...\n")

        result = nba_season_ingestion(
            season=season,
            season_type=args.season_type,
            start_date=start_date,
            end_date=end_date,
        )

        print(f"\n{'='*80}")
        print(f"✅ Ingestion Complete!")
        print(f"{'='*80}")
        print(f"Teams: {result.get('teams', 0):,}")
        print(f"Games: {result.get('games', 0):,}")
        print(f"Player stats: {result.get('player_stats', 0):,}")
        print(f"Conferences: {result.get('conferences', 0):,}")
        print(f"Divisions: {result.get('divisions', 0):,}")
        print(f"{'='*80}")
        print(f"Shutting down Prefect server...")
        print()


if __name__ == "__main__":
    main()
