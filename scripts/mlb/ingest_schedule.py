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

def mian():
    """Main entry point for MLB schedule ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest MLB schedule data to BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    # Season selection
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season to ingest (e.g., 2024)",
    )
    
    # Options
    parser.add_argument(
        "--game-types",
        type=str,
        default="R,P",
        help=(
            "Comma-separated game types to ingest (default: R,P). "
            "Refer to MLB API docs for valid game type codes."
        ),
    )

    args = parser.parse_args()

    from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery

    inserted = ingest_mlb_schedule_bigquery(
        season=args.season,
        game_types=args.game_types,
    )
    print(f"ingested mlb schedule: season={args.season} games={inserted}")