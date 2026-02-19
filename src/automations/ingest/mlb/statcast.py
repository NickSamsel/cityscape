"""MLB Statcast data ingestion to BigQuery."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date

from src.integrations.mlb import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def _fetch_game_statcast_data(game_id: int, api: MlbStatsApi) -> tuple[list[dict], list[dict]]:
    """Fetch Statcast data for a single game.

    Args:
        game_id: MLB game ID
        api: MlbStatsApi client instance

    Returns:
        Tuple of (pitch_rows, batted_ball_rows)
    """
    try:
        pitches, batted_balls = api.get_game_statcast_data(game_id=game_id)

        pitch_rows = [
            {
                "play_id": p.play_id,
                "game_id": p.game_id,
                "at_bat_index": p.at_bat_index,
                "pitcher_id": p.pitcher_id,
                "batter_id": p.batter_id,
                "catcher_id": p.catcher_id,
                "umpire_id": p.umpire_id,
                "pitch_number": p.pitch_number,
                "pitch_type": p.pitch_type,
                "pitch_type_description": p.pitch_type_description,
                "release_speed": p.release_speed,
                "release_spin_rate": p.release_spin_rate,
                "release_extension": p.release_extension,
                "release_pos_x": p.release_pos_x,
                "release_pos_y": p.release_pos_y,
                "release_pos_z": p.release_pos_z,
                "zone": p.zone,
                "plate_x": p.plate_x,
                "plate_z": p.plate_z,
                "strikes": p.strikes,
                "balls": p.balls,
                "outs": p.outs,
                "pitch_result": p.pitch_result,
                "pitch_result_description": p.pitch_result_description,
                "raw": p.raw,
            }
            for p in pitches
        ]

        batted_ball_rows = [
            {
                "play_id": b.play_id,
                "game_id": b.game_id,
                "at_bat_index": b.at_bat_index,
                "batter_id": b.batter_id,
                "pitcher_id": b.pitcher_id,
                "launch_speed": b.launch_speed,
                "launch_angle": b.launch_angle,
                "launch_distance": b.launch_distance,
                "hit_location": b.hit_location,
                "hit_trajectory": b.hit_trajectory,
                "hit_result": b.hit_result,
                "sprint_speed": b.sprint_speed,
                "is_barrel": b.is_barrel,
                "is_hard_hit": b.is_hard_hit,
                "raw": b.raw,
            }
            for b in batted_balls
        ]

        return pitch_rows, batted_ball_rows

    except Exception:
        return [], []


def fetch_mlb_statcast_data(
    *,
    season: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    game_ids: list[int] | None = None,
    batch_size: int = 100,
    max_workers: int = 5,
) -> tuple[list[dict], list[dict]]:
    """Fetch MLB Statcast pitch and batted ball data with parallel processing.

    Args:
        season: MLB season year (used to fetch games if game_ids not provided)
        start_date: Optional start date filter
        end_date: Optional end date filter
        game_ids: Specific game IDs to fetch (if None, fetches from season)
        batch_size: Number of games to process before yielding (memory management)
        max_workers: Number of concurrent threads for API calls (default: 5)

    Returns:
        Tuple of (pitch_rows, batted_ball_rows)
    """

    logger = get_run_logger()
    api = MlbStatsApi()

    if game_ids is None:
        if season is None:
            raise ValueError("Either season or game_ids must be provided")

        logger.info(
            f"Fetching games for Statcast data: season={season} "
            f"start_date={start_date} end_date={end_date}"
        )
        games = api.list_games(
            season=season,
            game_types="R",
            start_date=start_date,
            end_date=end_date,
        )
        game_ids = [g.game_id for g in games]
        logger.info(f"Found {len(game_ids)} games to process")
    else:
        logger.info(f"Processing {len(game_ids)} specified game IDs")

    all_pitches = []
    all_batted_balls = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_game = {
            executor.submit(_fetch_game_statcast_data, game_id, api): game_id
            for game_id in game_ids
        }

        completed = 0
        failed = 0

        for future in as_completed(future_to_game):
            game_id = future_to_game[future]
            completed += 1

            try:
                pitch_rows, batted_ball_rows = future.result()

                if pitch_rows or batted_ball_rows:
                    all_pitches.extend(pitch_rows)
                    all_batted_balls.extend(batted_ball_rows)
                else:
                    failed += 1
                    logger.warning(f"No Statcast data returned for game {game_id}")

                if completed % 10 == 0:
                    logger.info(
                        f"Progress: {completed}/{len(game_ids)} games processed "
                        f"({failed} failed) - {len(all_pitches):,} pitches, "
                        f"{len(all_batted_balls):,} batted balls so far"
                    )

            except Exception as e:
                failed += 1
                logger.warning(f"Failed to fetch Statcast data for game {game_id}: {e}")

    logger.info(
        f"Fetched Statcast data: games={len(game_ids)} "
        f"pitches={len(all_pitches)} batted_balls={len(all_batted_balls)}"
    )

    return all_pitches, all_batted_balls


def ingest_mlb_statcast_data_bigquery(
    *,
    season: int | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    game_ids: list[int] | None = None,
    batch_size: int = 100,
    max_workers: int = 5,
) -> tuple[int, int]:
    """Fetch and load MLB Statcast data into BigQuery in batches with parallel processing.

    NOTE: 
    - Statcast data is only available from 2015 onwards. Earlier seasons will return 0 records.
    - Scheduled games are automatically filtered out (Statcast only exists for completed games).

    Args:
        season: MLB season year (Statcast available 2015+)
        start_date: Optional start date filter
        end_date: Optional end date filter
        game_ids: Specific game IDs to fetch
        batch_size: Number of games to process per batch (default: 100)
        max_workers: Number of concurrent threads for API calls (default: 5)

    Returns:
        Tuple of (pitches_loaded, batted_balls_loaded) counts
    """

    logger = get_run_logger()
    settings = get_settings()
    api = MlbStatsApi()

    if game_ids is None:
        if season is None:
            raise ValueError("Either season or game_ids must be provided")
        
        # Statcast data only available from 2015 onwards
        if season < 2015:
            logger.info(f"Skipping Statcast for season {season} (Statcast only available 2015+)")
            return (0, 0)

        logger.info(
            f"Fetching games for Statcast data: season={season} "
            f"start_date={start_date} end_date={end_date}"
        )
        games = api.list_games(
            season=season,
            game_types="R",
            start_date=start_date,
            end_date=end_date,
        )
        
        # Filter out scheduled games - Statcast only available for completed games
        completed_games = [g for g in games if g.status and g.status.lower() != "scheduled"]
        skipped = len(games) - len(completed_games)
        if skipped > 0:
            logger.info(f"Skipped {skipped} scheduled games (Statcast only for completed games)")
        
        game_ids = [g.game_id for g in completed_games]
        logger.info(f"Found {len(game_ids)} completed games to process")
    else:
        logger.info(f"Processing {len(game_ids)} specified game IDs")

    bq_cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        credentials_path=settings.gcp_credentials_path,
        service_account_key=settings.gcp_service_account_key,
    )
    client = get_client(bq_cfg)

    logger.info("Ensuring BigQuery datasets and tables exist")
    ensure_raw_dataset(client, settings.gcp_project_id)
    ensure_mlb_tables(client, settings.gcp_project_id)

    from src.utils.bigquery import upsert_mlb_statcast_pitches, upsert_mlb_statcast_batted_balls

    total_pitches = 0
    total_batted_balls = 0
    total_games = len(game_ids)

    for batch_start in range(0, total_games, batch_size):
        batch_end = min(batch_start + batch_size, total_games)
        batch_game_ids = game_ids[batch_start:batch_end]

        logger.info(
            f"Processing batch: games {batch_start + 1}-{batch_end} of {total_games} "
            f"({len(batch_game_ids)} games in this batch) with {max_workers} workers"
        )

        pitch_rows, batted_ball_rows = fetch_mlb_statcast_data(
            game_ids=batch_game_ids,
            batch_size=batch_size,
            max_workers=max_workers,
        )

        if pitch_rows:
            logger.info(f"Loading {len(pitch_rows)} pitch records for batch")
            pitches_loaded = upsert_mlb_statcast_pitches(client, settings.gcp_project_id, pitch_rows)
            total_pitches += pitches_loaded

        if batted_ball_rows:
            logger.info(f"Loading {len(batted_ball_rows)} batted ball records for batch")
            batted_balls_loaded = upsert_mlb_statcast_batted_balls(client, settings.gcp_project_id, batted_ball_rows)
            total_batted_balls += batted_balls_loaded

        logger.info(
            f"Batch complete. Total so far: pitches={total_pitches:,} batted_balls={total_batted_balls:,}"
        )

    logger.info(
        f"Statcast ingestion complete: pitches={total_pitches:,} batted_balls={total_batted_balls:,}"
    )

    return total_pitches, total_batted_balls
