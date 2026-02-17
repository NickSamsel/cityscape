import argparse
import logging
import warnings
from datetime import datetime

# Suppress noisy cleanup warnings
logging.getLogger("sqlalchemy.pool").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*no active connection.*")


def main() -> None:
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
        default="R",
        help=(
            "Comma-separated game types to ingest (default: R). "
            "Refer to MLB API docs for valid game type codes."
        ),
    )

    parser.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date filter (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date filter (YYYY-MM-DD)",
    )

    args = parser.parse_args()

    start_date = (
        datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
    )
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else None

    from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery

    inserted = ingest_mlb_schedule_bigquery(
        season=args.season,
        game_types=args.game_types,
        start_date=start_date,
        end_date=end_date,
    )
    print(f"ingested mlb schedule: season={args.season} games={inserted}")


if __name__ == "__main__":
    main()