"""Ingest MLB player dimension data.

This script fetches player information for all unique players found in the 
player stats tables and loads them into BigQuery as a dimension table.

Example usage:
    # Fetch all unique players (sequential - most stable)
    python scripts/mlb/ingest_players.py
    
    # Fetch all unique players (parallel - faster but uses more resources)
    python scripts/mlb/ingest_players.py --parallel --max-workers 3
    
    # Specific player IDs
    python scripts/mlb/ingest_players.py --player-ids 545361,660271,592450
"""

import argparse
import logging
import warnings

from src.automations.prefect.mlb import (
    mlb_player_dimension_ingestion,
    mlb_player_dimension_ingestion_parallel,
)


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("prefect.server.utilities.messaging.memory").setLevel(logging.ERROR)
logging.getLogger("prefect.task_runs").setLevel(logging.WARNING)
logging.getLogger("prefect.flow_runs").setLevel(logging.INFO)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for MLB player ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB player dimension data to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch all unique players (sequential - most stable, no Prefect overhead)
  python scripts/mlb/ingest_players.py
  
  # Fetch all unique players (parallel - faster, uses 3 workers)
  python scripts/mlb/ingest_players.py --parallel
  
  # Parallel with more workers (requires more system resources)
  python scripts/mlb/ingest_players.py --parallel --max-workers 5
  
  # Specific player IDs
  python scripts/mlb/ingest_players.py --player-ids 545361,660271,592450
  
  # With verbose output
  python scripts/mlb/ingest_players.py --verbose
        """
    )
    
    parser.add_argument(
        "--player-ids",
        type=str,
        help="Comma-separated list of player IDs to fetch (e.g., 545361,660271)"
    )
    
    parser.add_argument(
        "--parallel",
        action="store_true",
        help="Use parallel processing (faster but uses more system resources)"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Number of concurrent workers for parallel mode (default: 3, recommended: 3-10, max: 20)"
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
    
    # Parse player IDs if provided
    player_ids = None
    if args.player_ids:
        player_ids = [int(pid.strip()) for pid in args.player_ids.split(",")]
    
    # Display header
    print(f"\n{'='*80}")
    print(f"MLB Player Dimension Ingestion")
    print(f"{'='*80}\n")
    
    if player_ids:
        print(f"Player IDs: {len(player_ids)} specified")
    else:
        print(f"Mode: Fetch all unique players from stats tables")
    
    print(f"Processing: {'PARALLEL' if args.parallel else 'SEQUENTIAL (more stable)'}")  
    
    if args.parallel:
        print(f"Max workers: {args.max_workers}")
        if args.max_workers > 10:
            print(f"⚠️  Warning: {args.max_workers} workers may be unstable. Recommended: 3-10")
    
    print(f"\nStarting ingestion...\n")
    
    # Run the appropriate flow
    try:
        if args.parallel:
            result = mlb_player_dimension_ingestion_parallel(
                player_ids=player_ids,
                max_workers=args.max_workers,
            )
        else:
            if player_ids:
                print("⚠️  Note: Specific player IDs work best with --parallel flag")
                # For non-parallel with specific IDs, still use parallel function but it won't be as fast
                result = mlb_player_dimension_ingestion_parallel(
                    player_ids=player_ids,
                    max_workers=1,  # Sequential
                )
            else:
                result = mlb_player_dimension_ingestion()
        
        # Display results
        print(f"\n{'='*80}")
        print(f"✅ Player Dimension Ingestion Complete!")
        print(f"{'='*80}")
        print(f"Players loaded: {result['players']:,}")
        
        if args.parallel and not player_ids:
            print(f"\n💡 Parallel mode completed much faster than sequential!")
        
        print(f"{'='*80}")
        print(f"Shutting down Prefect server...")
        print()
        
    except Exception as e:
        print(f"\n{'='*80}")
        print(f"❌ Ingestion Failed!")
        print(f"{'='*80}")
        print(f"Error: {e}")
        print(f"{'='*80}\n")
        raise


if __name__ == "__main__":
    main()
