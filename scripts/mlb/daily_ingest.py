#!/usr/bin/env python3
"""Daily MLB data ingestion script for GitHub Actions.

This script runs the full MLB daily ingestion pipeline without requiring
a Prefect server. It calls the same underlying ingestion functions used
by the Prefect flows.

Usage:
    uv run python scripts/mlb/daily_ingest.py
    uv run python scripts/mlb/daily_ingest.py --season 2025 --lookback-days 3
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mlb_daily_ingest")


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily MLB data ingestion to BigQuery")
    parser.add_argument(
        "--season",
        type=int,
        default=date.today().year,
        help="MLB season year (default: current year)",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=2,
        help="Number of days to look back for late updates (default: 2)",
    )
    parser.add_argument(
        "--game-types",
        type=str,
        default="R",
        help="Game type filter (default: R for regular season)",
    )
    parser.add_argument(
        "--skip-statcast",
        action="store_true",
        help="Skip Statcast data ingestion (faster runs)",
    )
    args = parser.parse_args()

    from src.integrations.mlb import MlbStatsApi

    # Check season bounds — skip if off-season
    api = MlbStatsApi()
    start, end = api.get_regular_season_bounds(season=args.season)
    today = date.today()

    if start is not None and today < start:
        logger.info(f"Skipping: season {args.season} has not started yet (start={start})")
        return 0

    if end is not None and today > end + timedelta(days=14):
        logger.info(f"Skipping: season {args.season} appears finished (end={end})")
        return 0

    window_start = today - timedelta(days=max(1, args.lookback_days))
    window_end = today

    logger.info(
        f"Starting MLB daily ingestion: season={args.season} "
        f"window={window_start}..{window_end} game_types={args.game_types}"
    )

    # Step 1: Teams, games, leagues, divisions
    logger.info("Step 1/5: Ingesting teams, games, and reference data...")
    from src.automations.ingest.mlb import ingest_mlb_season_bigquery

    teams, games, leagues, divisions = ingest_mlb_season_bigquery(
        season=args.season,
        game_types=args.game_types,
        start_date=window_start,
        end_date=window_end,
    )
    logger.info(f"  teams={teams} games={games} leagues={leagues} divisions={divisions}")

    # Step 2: Player batting + pitching stats
    logger.info("Step 2/5: Ingesting player stats...")
    from src.automations.ingest.mlb import ingest_player_stats_sequential

    batting, pitching = ingest_player_stats_sequential(
        season=args.season,
        game_types=args.game_types,
        start_date=window_start,
        end_date=window_end,
    )
    logger.info(f"  batting_stats={batting} pitching_stats={pitching}")

    # Step 3: Statcast data
    if not args.skip_statcast:
        logger.info("Step 3/5: Ingesting Statcast data...")
        from src.automations.ingest.mlb import ingest_mlb_statcast_data_bigquery

        pitches, batted_balls = ingest_mlb_statcast_data_bigquery(
            season=args.season,
            start_date=window_start,
            end_date=window_end,
            batch_size=50,
            max_workers=3,
        )
        logger.info(f"  pitches={pitches:,} batted_balls={batted_balls:,}")
    else:
        logger.info("Step 3/5: Skipping Statcast data (--skip-statcast)")

    # Step 4: Standings snapshot
    logger.info("Step 4/5: Ingesting standings...")
    from src.automations.ingest.mlb import ingest_standings_snapshot

    standings = ingest_standings_snapshot(season=args.season, standings_date=today)
    logger.info(f"  standings_records={standings}")

    # Step 5: Schedule, probable pitchers, broadcasts, lineups
    logger.info("Step 5/5: Ingesting schedule, pitchers, broadcasts, and lineups...")
    from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery

    schedule, broadcasts, lineups = ingest_mlb_schedule_bigquery(
        season=args.season,
        game_types=args.game_types,
        start_date=window_start,
        end_date=window_end,
    )
    logger.info(f"  schedule={schedule} broadcasts={broadcasts} lineups={lineups}")

    logger.info("MLB daily ingestion complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
