#!/usr/bin/env python3
"""Ingest MLB venue (ballpark) reference data into BigQuery across multiple seasons.

This script loads ballpark metadata into `raw.mlb_venues`.

Examples:
    # Ingest venues for a single season
    uv run python -m scripts.mlb.ingest_venues --start-season 2024

    # Ingest venues for a range of seasons (e.g., 2020 to 2024)
    uv run python -m scripts.mlb.ingest_venues --start-season 2020 --end-season 2024

    # Provide explicit venue IDs for a specific season
    uv run python -m scripts.mlb.ingest_venues --start-season 2024 --venue-ids 3,10,12
"""

from __future__ import annotations

import argparse
import sys

def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest MLB venue (ballpark) data to BigQuery")
    
    # Season Range Arguments
    parser.add_argument("--start-season", type=int, required=True, help="Beginning season year (e.g., 2020)")
    parser.add_argument("--end-season", type=int, help="Ending season year (optional, defaults to start-season)")
    
    parser.add_argument(
        "--game-types",
        type=str,
        default="R,P",
        help="Game type filter (default: R,P)",
    )
    parser.add_argument(
        "--venue-ids",
        type=str,
        help="Comma-separated venue IDs (skips schedule derivation)",
    )

    args = parser.parse_args()

    # Determine the range of years to process
    end_season = args.end_season if args.end_season else args.start_season
    seasons = range(args.start_season, end_season + 1)

    venue_ids: list[int] | None = None
    if args.venue_ids:
        venue_ids = [int(v.strip()) for v in args.venue_ids.split(",") if v.strip()]

    from src.automations.ingest.mlb import ingest_mlb_venues_bigquery

    for season in seasons:
        print(f"Processing season: {season}...")
        
        # We pass None for start_date and end_date as per your requirement 
        # to avoid individual date-based calls.
        inserted = ingest_mlb_venues_bigquery(
            season=season,
            venue_ids=venue_ids,
            game_types=args.game_types,
            start_date=None,
            end_date=None,
        )
        print(f"Completed {season}: ingested {inserted} venues.")

    return 0


if __name__ == "__main__":
    sys.exit(main())