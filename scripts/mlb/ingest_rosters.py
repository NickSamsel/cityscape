#!/usr/bin/env python3
"""Ingest MLB team rosters data.

This script fetches roster data (team-player mappings) for MLB teams.
Rosters provide an efficient way to discover players and their team
affiliations without iterating through thousands of game stats.

Efficiency comparison for a full season:
- Roster approach: ~30 API calls (one per team)
- Game stats approach: ~4,860 API calls (one per game)

Example usage:
    # Default: current season, all teams, parallel
    python scripts/mlb/ingest_rosters.py
    
    # Specific season
    python scripts/mlb/ingest_rosters.py --season 2024
    
    # Sequential mode (more stable, slower)
    python scripts/mlb/ingest_rosters.py --season 2024 --sequential
    
    # Specific teams only
    python scripts/mlb/ingest_rosters.py --season 2024 --team-ids 147,121,119
"""

import argparse
import logging
import sys
import warnings
from datetime import date
from pathlib import Path


# Allow running via: `python scripts/mlb/ingest_rosters.py ...`
# without requiring an editable install.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.automations.ingest.mlb import ingest_mlb_rosters_bigquery


# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main():
    """Main entry point for MLB roster ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB team rosters to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Default: current season, all teams, parallel
  python scripts/mlb/ingest_rosters.py
  
  # Specific season
  python scripts/mlb/ingest_rosters.py --season 2024
  
  # Sequential mode (more stable, slower)
  python scripts/mlb/ingest_rosters.py --season 2024 --sequential
  
  # Specific teams only (NYY=147, LAD=119, BOS=111)
  python scripts/mlb/ingest_rosters.py --season 2024 --team-ids 147,119,111
  
  # More concurrent workers for faster processing
  python scripts/mlb/ingest_rosters.py --season 2024 --max-workers 10
        """
    )
    
    current_year = date.today().year
    
    parser.add_argument(
        "--season",
        type=int,
        default=current_year,
        help=f"Season to ingest rosters for (default: {current_year})"
    )
    
    parser.add_argument(
        "--team-ids",
        type=str,
        help="Comma-separated list of team IDs to fetch (e.g., 147,121,119). If omitted, fetches all teams."
    )
    
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Use sequential processing instead of parallel (slower but more stable)"
    )
    
    parser.add_argument(
        "--max-workers",
        type=int,
        default=5,
        help="Number of concurrent workers for parallel mode (default: 5, max recommended: 10)"
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
    
    # Parse team IDs if provided
    team_ids = None
    if args.team_ids:
        team_ids = [int(tid.strip()) for tid in args.team_ids.split(",")]
    
    # Display header
    mode = "sequential" if args.sequential else f"parallel (workers={args.max_workers})"
    team_desc = f"{len(team_ids)} specific teams" if team_ids else "all teams"
    
    print(f"\n{'='*60}")
    print(f"MLB Roster Ingestion to BigQuery")
    print(f"{'='*60}")
    print(f"Season:      {args.season}")
    print(f"Teams:       {team_desc}")
    print(f"Mode:        {mode}")
    print(f"{'='*60}\n")
    
    # Run ingestion
    try:
        entries = ingest_mlb_rosters_bigquery(
            season=args.season,
            team_ids=team_ids,
            parallel=not args.sequential,
            max_workers=args.max_workers,
        )
        
        print(f"\n{'='*60}")
        print(f"✅ Roster ingestion complete!")
        print(f"{'='*60}")
        print(f"Total entries:  {entries:,}")
        print(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error during ingestion: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
