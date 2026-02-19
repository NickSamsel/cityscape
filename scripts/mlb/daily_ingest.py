#!/usr/bin/env python3
"""Daily MLB data ingestion script for GitHub Actions.

This script runs the full MLB daily ingestion pipeline without requiring
a Prefect server. It calls the same underlying ingestion functions used
by the Prefect flows.

OPTIMIZATION NOTE: For optimal efficiency, run roster ingestion separately
(weekly or at start of season) before using this daily script:

    python scripts/mlb/ingest_rosters.py --season 2025

This reduces API calls by ~99% for player discovery. See docs/mlb_roster_optimization.md

Usage:
    uv run python scripts/mlb/daily_ingest.py
    uv run python scripts/mlb/daily_ingest.py --season 2025 --lookback-days 3
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import date, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mlb_daily_ingest")


def write_github_summary(
    completed_steps: list[str],
    failed_steps: list[str],
    errors: list[str],
    args: argparse.Namespace,
    window_start: date,
    window_end: date,
    today: date,
) -> None:
    """Write a formatted summary to GitHub Actions step summary if available."""
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return
    
    with open(summary_file, "a") as f:
        f.write("## 📊 MLB Daily Ingestion Summary\n\n")
        
        # Overview
        if not failed_steps:
            f.write("### ✅ All Steps Completed Successfully!\n\n")
        else:
            f.write(f"### ⚠️ {len(failed_steps)} Step(s) Failed\n\n")
        
        f.write(f"**Season:** {args.season}  \n")
        f.write(f"**Window:** {window_start} to {window_end}  \n")
        f.write(f"**Date:** {today}  \n\n")
        
        # Results table
        f.write("| Step | Status |\n")
        f.write("|------|--------|\n")
        
        all_steps = [
            ("0. Rosters", "rosters"),
            ("1. Teams/Games", "teams_games"),
            ("2. Player Stats", "player_stats"),
            ("3. Statcast", "statcast"),
            ("4. Standings", "standings"),
            ("5. Schedule", "schedule"),
            ("6. Players", "players"),
        ]
        
        for step_name, step_id in all_steps:
            if step_id in completed_steps:
                f.write(f"| {step_name} | ✅ Success |\n")
            elif step_id in failed_steps:
                f.write(f"| {step_name} | ❌ Failed |\n")
            else:
                f.write(f"| {step_name} | ⏭️ Skipped |\n")
        
        # Failed steps detail
        if failed_steps:
            f.write("\n### 🔧 Recovery Commands\n\n")
            f.write("Run these commands to fix failed steps:\n\n")
            
            if "rosters" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python scripts/mlb/ingest_rosters.py --season {args.season}\n")
                f.write(f"```\n\n")
            
            if "teams_games" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_season_bigquery; ")
                f.write(f"ingest_mlb_season_bigquery(season={args.season}, game_types='{args.game_types}', ")
                f.write(f"start_date='{window_start}', end_date='{window_end}')\"\n")
                f.write(f"```\n\n")
            
            if "player_stats" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_player_stats_sequential; ")
                f.write(f"ingest_player_stats_sequential(season={args.season}, game_types='{args.game_types}', ")
                f.write(f"start_date='{window_start}', end_date='{window_end}')\"\n")
                f.write(f"```\n\n")
            
            if "statcast" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_statcast_data_bigquery; ")
                f.write(f"ingest_mlb_statcast_data_bigquery(season={args.season}, ")
                f.write(f"start_date='{window_start}', end_date='{window_end}', batch_size=100, max_workers=10)\"\n")
                f.write(f"```\n\n")
            
            if "standings" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_standings_snapshot; ")
                f.write(f"ingest_standings_snapshot(season={args.season}, standings_date='{today}')\"\n")
                f.write(f"```\n\n")
            
            if "schedule" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery; ")
                f.write(f"ingest_mlb_schedule_bigquery(season={args.season}, game_types='{args.game_types}', ")
                f.write(f"start_date='{window_start}', end_date='{window_end}')\"\n")
                f.write(f"```\n\n")
            
            if "players" in failed_steps:
                f.write(f"```bash\n")
                f.write(f"uv run python -c \"from src.automations.ingest.mlb import ingest_players_from_rosters; ")
                f.write(f"ingest_players_from_rosters(season={args.season})\"\n")
                f.write(f"```\n\n")
            
            # Errors detail
            f.write("### ❌ Error Details\n\n")
            for i, error in enumerate(errors, 1):
                f.write(f"{i}. {error}\n")


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
        default="R,F,D,L,W,S",
        help="Game type filter (default: R,F,D,L,W,S)",
    )
    parser.add_argument(
        "--skip-statcast",
        action="store_true",
        help="Skip Statcast data ingestion (faster runs)",
    )
    parser.add_argument(
        "--skip-rosters",
        action="store_true",
        help="Skip roster ingestion (use if rosters were recently updated)",
    )
    parser.add_argument(
        "--update-rosters-weekly",
        action="store_true",
        help="Only update rosters if it's been 7+ days (default: update every run)",
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

    # Track results
    completed_steps = []
    failed_steps = []
    errors = []

    # Step 0: Rosters - for efficient player discovery
    if not args.skip_rosters:
        # Check if we should update (weekly vs every run)
        should_update = True
        if args.update_rosters_weekly:
            # Simple check: only update on Mondays (day 0)
            should_update = today.weekday() == 0
        
        if should_update:
            logger.info("Step 0/6: Updating team rosters (OPTIMIZED player discovery)...")
            from src.automations.ingest.mlb import ingest_mlb_rosters_bigquery
            
            try:
                roster_entries = ingest_mlb_rosters_bigquery(
                    season=args.season,
                    parallel=True,
                    max_workers=15,
                )
                logger.info(f"  ✓ roster_entries={roster_entries}")
                completed_steps.append("rosters")
            except Exception as e:
                error_msg = f"Rosters: {str(e)[:100]}"
                logger.error(f"  ✗ {error_msg}")
                failed_steps.append("rosters")
                errors.append(error_msg)
        else:
            logger.info("Step 0/6: Skipping roster update (not scheduled for today)")
    else:
        logger.info("Step 0/6: Skipping roster update (--skip-rosters flag)")

    # Step 1: Teams, games, leagues, divisions
    logger.info("Step 1/6: Ingesting teams, games, and reference data...")
    from src.automations.ingest.mlb import ingest_mlb_season_bigquery

    try:
        teams, games, leagues, divisions = ingest_mlb_season_bigquery(
            season=args.season,
            game_types=args.game_types,
            start_date=window_start,
            end_date=window_end,
        )
        logger.info(f"  ✓ teams={teams} games={games} leagues={leagues} divisions={divisions}")
        completed_steps.append("teams_games")
    except Exception as e:
        error_msg = f"Teams/Games: {str(e)[:100]}"
        logger.error(f"  ✗ {error_msg}")
        failed_steps.append("teams_games")
        errors.append(error_msg)

    # Step 2: Player batting + pitching stats
    logger.info("Step 2/6: Ingesting player stats...")
    from src.automations.ingest.mlb import ingest_player_stats_sequential

    try:
        batting, pitching = ingest_player_stats_sequential(
            season=args.season,
            game_types=args.game_types,
            start_date=window_start,
            end_date=window_end,
        )
        logger.info(f"  ✓ batting_stats={batting} pitching_stats={pitching}")
        completed_steps.append("player_stats")
    except Exception as e:
        error_msg = f"Player Stats: {str(e)[:100]}"
        logger.error(f"  ✗ {error_msg}")
        failed_steps.append("player_stats")
        errors.append(error_msg)

    # Step 3: Statcast data (2015+ only)
    if not args.skip_statcast and args.season >= 2015:
        logger.info("Step 3/6: Ingesting Statcast data...")
        from src.automations.ingest.mlb import ingest_mlb_statcast_data_bigquery

        try:
            pitches, batted_balls = ingest_mlb_statcast_data_bigquery(
                season=args.season,
                start_date=window_start,
                end_date=window_end,
                batch_size=100,
                max_workers=10,
            )
            logger.info(f"  ✓ pitches={pitches:,} batted_balls={batted_balls:,}")
            completed_steps.append("statcast")
        except Exception as e:
            error_msg = f"Statcast: {str(e)[:100]}"
            logger.error(f"  ✗ {error_msg}")
            failed_steps.append("statcast")
            errors.append(error_msg)
    elif not args.skip_statcast and args.season < 2015:
        logger.info(f"Step 3/6: Skipping Statcast data (not available before 2015, season={args.season})")
    else:
        logger.info("Step 3/6: Skipping Statcast data (--skip-statcast)")


    # Step 4: Standings snapshot
    logger.info("Step 4/6: Ingesting standings...")
    from src.automations.ingest.mlb import ingest_standings_snapshot

    try:
        standings = ingest_standings_snapshot(season=args.season, standings_date=today)
        logger.info(f"  ✓ standings_records={standings}")
        completed_steps.append("standings")
    except Exception as e:
        error_msg = f"Standings: {str(e)[:100]}"
        logger.error(f"  ✗ {error_msg}")
        failed_steps.append("standings")
        errors.append(error_msg)

    # Step 5: Schedule, probable pitchers, broadcasts, lineups
    logger.info("Step 5/6: Ingesting schedule, pitchers, broadcasts, and lineups...")
    from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery

    try:
        schedule, broadcasts, lineups = ingest_mlb_schedule_bigquery(
            season=args.season,
            game_types=args.game_types,
            start_date=window_start,
            end_date=window_end,
        )
        logger.info(f"  ✓ schedule={schedule} broadcasts={broadcasts} lineups={lineups}")
        completed_steps.append("schedule")
    except Exception as e:
        error_msg = f"Schedule: {str(e)[:100]}"
        logger.error(f"  ✗ {error_msg}")
        failed_steps.append("schedule")
        errors.append(error_msg)
    
    # Step 6: Update player dimension from rosters (if rosters were updated)
    if not args.skip_rosters:
        logger.info("Step 6/6: Updating player dimension data from rosters...")
        from src.automations.ingest.mlb import ingest_players_from_rosters
        
        try:
            players = ingest_players_from_rosters(season=args.season)
            logger.info(f"  ✓ players={players}")
            completed_steps.append("players")
        except Exception as e:
            error_msg = f"Players: {str(e)[:100]}"
            logger.error(f"  ✗ {error_msg}")
            failed_steps.append("players")
            errors.append(error_msg)
    else:
        logger.info("Step 6/6: Skipping player dimension update (rosters were skipped)")

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("DAILY INGESTION SUMMARY")
    logger.info("=" * 80)
    logger.info(f"✓ Completed: {len(completed_steps)} steps")
    if failed_steps:
        logger.info(f"✗ Failed: {len(failed_steps)} steps")
    
    if failed_steps:
        logger.info("\n" + "-" * 80)
        logger.info("FAILED STEPS (Recovery Commands)")
        logger.info("-" * 80)
        
        for i, error in enumerate(errors):
            logger.info(f"  {i+1}. {error}")
        
        logger.info("\n  Re-run individual steps:")
        
        if "rosters" in failed_steps:
            logger.info(f"    Rosters: uv run python scripts/mlb/ingest_rosters.py --season {args.season}")
        
        if "teams_games" in failed_steps:
            logger.info(f"    Teams/Games: uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_season_bigquery; "
                       f"ingest_mlb_season_bigquery(season={args.season}, game_types='{args.game_types}', "
                       f"start_date='{window_start}', end_date='{window_end}')\"")
        
        if "player_stats" in failed_steps:
            logger.info(f"    Player Stats: uv run python -c \"from src.automations.ingest.mlb import ingest_player_stats_sequential; "
                       f"ingest_player_stats_sequential(season={args.season}, game_types='{args.game_types}', "
                       f"start_date='{window_start}', end_date='{window_end}')\"")
        
        if "statcast" in failed_steps:
            logger.info(f"    Statcast: uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_statcast_data_bigquery; "
                       f"ingest_mlb_statcast_data_bigquery(season={args.season}, "
                       f"start_date='{window_start}', end_date='{window_end}', batch_size=100, max_workers=10)\"")
        
        if "standings" in failed_steps:
            logger.info(f"    Standings: uv run python -c \"from src.automations.ingest.mlb import ingest_standings_snapshot; "
                       f"ingest_standings_snapshot(season={args.season}, standings_date='{today}')\"")
        
        if "schedule" in failed_steps:
            logger.info(f"    Schedule: uv run python -c \"from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery; "
                       f"ingest_mlb_schedule_bigquery(season={args.season}, game_types='{args.game_types}', "
                       f"start_date='{window_start}', end_date='{window_end}')\"")
        
        if "players" in failed_steps:
            logger.info(f"    Players: uv run python -c \"from src.automations.ingest.mlb import ingest_players_from_rosters; "
                       f"ingest_players_from_rosters(season={args.season})\"")
        
        logger.info("\n  Or re-run entire daily ingestion:")
        logger.info(f"    uv run python scripts/mlb/daily_ingest.py --season {args.season} "
                   f"--lookback-days {args.lookback_days}")
    
    logger.info("\n" + "=" * 80)
    if not failed_steps:
        logger.info("🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
    else:
        logger.info(f"⚠ {len(failed_steps)} step(s) failed. Review errors and re-run commands above.")
    logger.info("=" * 80)
    
    # Write GitHub Actions summary if running in CI
    write_github_summary(
        completed_steps=completed_steps,
        failed_steps=failed_steps,
        errors=errors,
        args=args,
        window_start=window_start,
        window_end=window_end,
        today=today,
    )
    
    return 0 if len(failed_steps) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
