#!/usr/bin/env python3
"""Ingest MLB venue (ballpark) reference data into BigQuery.

This script loads ballpark metadata into `raw.mlb_venues`.

Modes:
1) Derive venue IDs from schedule for the full season (default)
2) Derive venue IDs from schedule in a date window
3) Provide explicit venue IDs

Examples:
    # Derive from the full season schedule (all parks teams played in)
    uv run python -m scripts.mlb.ingest_venues --season 2024 --game-types R,P

    # Derive from a date window
    uv run python -m scripts.mlb.ingest_venues --season 2024 --start-date 2024-04-01 --end-date 2024-04-07

  # Explicit venue IDs
    uv run python -m scripts.mlb.ingest_venues --season 2024 --venue-ids 3,10,12
"""

from __future__ import annotations

import argparse
import sys
from datetime import date


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest MLB venue (ballpark) data to BigQuery")
    parser.add_argument("--season", type=int, required=True, help="MLB season year (e.g., 2024)")
    parser.add_argument(
        "--game-types",
        type=str,
        default="R,P",
        help=(
            "Game type filter used only when deriving venue IDs from schedule "
            "(default: R,P)"
        ),
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="Start date YYYY-MM-DD (used only when deriving venue IDs from schedule)",
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="End date YYYY-MM-DD (used only when deriving venue IDs from schedule)",
    )
    parser.add_argument(
        "--venue-ids",
        type=str,
        help="Comma-separated venue IDs (skips schedule derivation)",
    )

    args = parser.parse_args()

    start_date: date | None = date.fromisoformat(args.start_date) if args.start_date else None
    end_date: date | None = date.fromisoformat(args.end_date) if args.end_date else None
    venue_ids: list[int] | None = None
    if args.venue_ids:
        venue_ids = [int(v.strip()) for v in args.venue_ids.split(",") if v.strip()]

    from src.automations.ingest.mlb import ingest_mlb_venues_bigquery

    inserted = ingest_mlb_venues_bigquery(
        season=args.season,
        venue_ids=venue_ids,
        game_types=args.game_types,
        start_date=start_date,
        end_date=end_date,
    )
    print(f"ingested mlb venues: season={args.season} venues={inserted}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
