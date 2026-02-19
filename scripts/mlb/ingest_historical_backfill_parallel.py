#!/usr/bin/env python3
"""PARALLEL historical MLB data backfill - processes multiple seasons concurrently.

This is a faster version of ingest_historical_backfill.py that processes multiple
seasons in parallel. Use this for large historical loads (e.g., 2000-2026).

SPEED IMPROVEMENT: ~5-10x faster than sequential version

Usage:
    # Full historical backfill with 5 concurrent seasons
    uv run python scripts/mlb/ingest_historical_backfill_parallel.py --max-season-workers 5

    # Skip Statcast for even faster initial load
    uv run python scripts/mlb/ingest_historical_backfill_parallel.py --skip-statcast --max-season-workers 8
"""

from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.automations.ingest.mlb import (
    ingest_mlb_rosters_bigquery,
    ingest_mlb_schedule_bigquery,
    ingest_mlb_season_bigquery,
    ingest_mlb_statcast_data_bigquery,
    ingest_players_from_rosters,
    ingest_standings_bulk_historical,
)
from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mlb_parallel_backfill")


def ingest_season_data(season: int, game_types: str, skip_statcast: bool) -> dict:
    """Ingest all data for a single season."""
    result = {
        "season": season,
        "success": True,
        "errors": [],
        "completed_steps": [],
        "failed_steps": []
    }
    
    try:
        # Rosters
        logger.info(f"[{season}] Ingesting rosters...")
        try:
            roster_entries = ingest_mlb_rosters_bigquery(
                season=season,
                parallel=True,
                max_workers=10,
            )
            result["roster_entries"] = roster_entries
            result["completed_steps"].append("rosters")
        except Exception as e:
            error_msg = f"Rosters: {str(e)[:100]}"
            result["errors"].append(error_msg)
            result["failed_steps"].append("rosters")
            logger.error(f"[{season}] Roster ingestion failed: {e}")
        
        # Teams & Games
        logger.info(f"[{season}] Ingesting teams & games...")
        try:
            teams, games, leagues, divisions = ingest_mlb_season_bigquery(
                season=season,
                game_types=game_types,
            )
            result.update({"teams": teams, "games": games, "leagues": leagues, "divisions": divisions})
            result["completed_steps"].append("teams_games")
        except Exception as e:
            error_msg = f"Teams/Games: {str(e)[:100]}"
            result["errors"].append(error_msg)
            result["failed_steps"].append("teams_games")
            logger.error(f"[{season}] Teams/Games ingestion failed: {e}")
        
        # Schedule
        logger.info(f"[{season}] Ingesting schedule...")
        try:
            schedule, broadcasts, lineups = ingest_mlb_schedule_bigquery(
                season=season,
                game_types=game_types,
            )
            result.update({"schedule": schedule, "broadcasts": broadcasts, "lineups": lineups})
            result["completed_steps"].append("schedule")
        except Exception as e:
            error_msg = f"Schedule: {str(e)[:100]}"
            result["errors"].append(error_msg)
            result["failed_steps"].append("schedule")
            logger.error(f"[{season}] Schedule ingestion failed: {e}")
        
        # Statcast (2015+ only)
        if not skip_statcast and season >= 2015:
            logger.info(f"[{season}] Ingesting Statcast data...")
            try:
                pitches, batted_balls = ingest_mlb_statcast_data_bigquery(
                    season=season,
                    batch_size=100,
                    max_workers=10,
                )
                result.update({"pitches": pitches, "batted_balls": batted_balls})
                result["completed_steps"].append("statcast")
            except Exception as e:
                error_msg = f"Statcast: {str(e)[:100]}"
                result["errors"].append(error_msg)
                result["failed_steps"].append("statcast")
                logger.error(f"[{season}] Statcast ingestion failed: {e}")
        
        # Mark as failed if any critical steps failed
        if "teams_games" in result["failed_steps"]:
            result["success"] = False
        
        if result["success"]:
            logger.info(f"[{season}] ✓ Complete! Steps: {', '.join(result['completed_steps'])}")
        else:
            logger.warning(f"[{season}] ⚠ Partial success. Failed: {', '.join(result['failed_steps'])}")
        
    except Exception as e:
        logger.error(f"[{season}] Critical failure: {e}")
        result["success"] = False
        result["errors"].append(f"Critical: {str(e)[:100]}")
    
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PARALLEL historical MLB data backfill (5-10x faster)"
    )
    parser.add_argument("--start-year", type=int, default=2000)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument("--skip-statcast", action="store_true")
    parser.add_argument("--skip-venues", action="store_true")
    parser.add_argument("--skip-standings", action="store_true")
    parser.add_argument("--skip-players", action="store_true")
    parser.add_argument("--game-types", type=str, default="R,F,D,L,W")
    parser.add_argument(
        "--max-season-workers",
        type=int,
        default=5,
        help="Number of seasons to process concurrently (default: 5, max recommended: 8)",
    )
    
    args = parser.parse_args()
    
    seasons = list(range(args.start_year, args.end_year + 1))
    total_seasons = len(seasons)
    
    logger.info("=" * 80)
    logger.info(f"PARALLEL MLB HISTORICAL BACKFILL: {args.start_year}-{args.end_year}")
    logger.info(f"Total seasons: {total_seasons}")
    logger.info(f"Concurrent seasons: {args.max_season_workers}")
    logger.info("=" * 80)
    
    # Venues (once)
    if not args.skip_venues:
        logger.info("Ingesting venues...")
        try:
            venues = ingest_mlb_venues_bigquery()
            logger.info(f"✓ Venues: {venues}")
        except Exception as e:
            logger.error(f"Venues failed: {e}")
    
    # Process seasons in parallel
    logger.info(f"\nProcessing {total_seasons} seasons with {args.max_season_workers} workers...")
    results = []
    
    with ThreadPoolExecutor(max_workers=args.max_season_workers) as executor:
        futures = {
            executor.submit(ingest_season_data, season, args.game_types, args.skip_statcast): season
            for season in seasons
        }
        
        completed = 0
        for future in as_completed(futures):
            completed += 1
            season = futures[future]
            result = future.result()
            results.append(result)
            
            if result["success"]:
                logger.info(f"[{completed}/{total_seasons}] ✓ Season {season} complete")
            else:
                logger.error(f"[{completed}/{total_seasons}] ✗ Season {season} FAILED")
    
    # Standings (bulk - already fast)
    if not args.skip_standings:
        logger.info("\nIngesting standings (bulk parallel mode)...")
        try:
            standings_results = ingest_standings_bulk_historical(
                start_season=args.start_year,
                end_season=args.end_year,
                interval_days=7,
                parallel=True,
                max_workers=15,  # Increased from 10
            )
            total_records = sum(standings_results.values())
            logger.info(f"✓ Standings: {total_records} records")
        except Exception as e:
            logger.error(f"Standings failed: {e}")
    
    # Players (once at the end)
    players_failed = False
    if not args.skip_players:
        logger.info("\nIngesting player dimension from rosters...")
        try:
            players = ingest_players_from_rosters(season=args.end_year)
            logger.info(f"✓ Players: {players}")
        except Exception as e:
            logger.error(f"Players failed: {e}")
            players_failed = True
    
    # Detailed Summary
    successful = sum(1 for r in results if r["success"])
    failed_seasons = [r for r in results if not r["success"]]
    partial_seasons = [r for r in results if r["success"] and r.get("failed_steps")]
    
    logger.info("\n" + "=" * 80)
    logger.info("BACKFILL SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ Successful: {successful}/{len(seasons)} seasons")
    if failed_seasons:
        logger.info(f"✗ Failed: {len(failed_seasons)} seasons")
    if partial_seasons:
        logger.info(f"⚠ Partial: {len(partial_seasons)} seasons (some steps failed)")
    
    # Failed seasons detail
    if failed_seasons:
        logger.info("\n" + "-" * 80)
        logger.info("FAILED SEASONS (Re-run Required)")
        logger.info("-" * 80)
        for r in sorted(failed_seasons, key=lambda x: x["season"]):
            logger.info(f"  Season {r['season']}: {', '.join(r['errors'])}")
            logger.info(f"    Re-run: uv run python scripts/mlb/ingest_historical_backfill_parallel.py "
                       f"--start-year {r['season']} --end-year {r['season']}")
    
    # Partial seasons detail
    if partial_seasons:
        logger.info("\n" + "-" * 80)
        logger.info("PARTIAL SUCCESSES (Optional Fixes)")
        logger.info("-" * 80)
        for r in sorted(partial_seasons, key=lambda x: x["season"]):
            failed = r.get("failed_steps", [])
            logger.info(f"  Season {r['season']} - Failed: {', '.join(failed)}")
            
            # Suggest specific re-run commands
            if "rosters" in failed:
                logger.info(f"    Fix rosters: uv run python scripts/mlb/ingest_rosters.py --season {r['season']}")
            if "statcast" in failed:
                logger.info(f"    Fix Statcast: uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_statcast_data_bigquery; "
                           f"ingest_mlb_statcast_data_bigquery(season={r['season']})\"")
            if "schedule" in failed:
                logger.info(f"    Fix schedule: uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery; "
                           f"ingest_mlb_schedule_bigquery(season={r['season']})\"")
    
    # Global failures
    if players_failed:
        logger.info("\n" + "-" * 80)
        logger.info("GLOBAL FAILURES")
        logger.info("-" * 80)
        logger.info(f"  ✗ Player dimension ingestion failed")
        logger.info(f"    Re-run: uv run python -c \"from src.automations.ingest.mlb import ingest_players_from_rosters; "
                   f"ingest_players_from_rosters(season={args.end_year})\"")
    
    logger.info("\n" + "=" * 80)
    if not failed_seasons and not partial_seasons and not players_failed:
        logger.info("🎉 ALL DATA LOADED SUCCESSFULLY!")
    elif not failed_seasons:
        logger.info("✓ Core data loaded. Review partial failures above.")
    else:
        logger.info("⚠ Some seasons failed. Review errors and re-run commands above.")
    logger.info("=" * 80)
    
    return 0 if len(failed_seasons) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
