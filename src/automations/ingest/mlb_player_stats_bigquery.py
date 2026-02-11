from __future__ import annotations

from datetime import date

from src.integrations.mlb.statsapi import MlbStatsApi
from src.utils.bigquery import (
    BigQueryConfig,
    get_client,
    ensure_raw_dataset,
    ensure_mlb_tables,
    upsert_mlb_player_batting_stats,
    upsert_mlb_player_pitching_stats,
)
from src.utils.logger import get_run_logger
from src.utils.settings import get_settings


def ingest_mlb_player_game_stats_bigquery(
    *,
    season: int,
    game_types: str = "R",
    start_date: date | None = None,
    end_date: date | None = None,
) -> tuple[int, int]:
    """Fetch MLB player game-by-game stats and land them into BigQuery raw tables.

    This fetches player batting and pitching statistics for each game in the specified
    season/date range and lands them into:
    - raw.mlb_player_batting_stats
    - raw.mlb_player_pitching_stats
    
    Args:
        season: The MLB season year (e.g., 2024)
        game_types: Game type filter (default "R" for regular season)
        start_date: Optional start date to filter games
        end_date: Optional end date to filter games
        
    Returns:
        (batting_stats_count, pitching_stats_count)
    """

    logger = get_run_logger()
    settings = get_settings()

    cfg = BigQueryConfig(
        project_id=settings.gcp_project_id,
        location="US",
        credentials_path=settings.gcp_credentials_path,
    )

    client = get_client(cfg)
    api = MlbStatsApi()

    # First, get the list of games for the season/date range
    if start_date is not None or end_date is not None:
        logger.info(
            f"Fetching MLB games season={season} game_types={game_types} start_date={start_date} end_date={end_date}"
        )
    else:
        logger.info(f"Fetching MLB games season={season} game_types={game_types}")

    games = api.list_games(season=season, game_types=game_types, start_date=start_date, end_date=end_date)
    
    logger.info(f"Found {len(games)} games, fetching player stats for each game...")

    all_batting_stats = []
    all_pitching_stats = []
    
    # Fetch player stats for each game
    for i, game in enumerate(games, 1):
        if i % 10 == 0:
            logger.info(f"Processing game {i}/{len(games)} (game_id={game.game_id})")
        
        try:
            batting_stats, pitching_stats = api.get_player_game_stats(game_id=game.game_id)
            all_batting_stats.extend(batting_stats)
            all_pitching_stats.extend(pitching_stats)
        except Exception as e:
            logger.warning(f"Failed to fetch stats for game_id={game.game_id}: {e}")
            continue

    logger.info(
        f"Fetched {len(all_batting_stats)} batting stat records and {len(all_pitching_stats)} pitching stat records"
    )

    # Prepare data rows for BigQuery
    batting_rows = [
        {
            "game_id": b.game_id,
            "player_id": b.player_id,
            "team_id": b.team_id,
            "player_name": b.player_name,
            "batting_order": b.batting_order,
            "position": b.position,
            "at_bats": b.at_bats,
            "runs": b.runs,
            "hits": b.hits,
            "doubles": b.doubles,
            "triples": b.triples,
            "home_runs": b.home_runs,
            "rbi": b.rbi,
            "stolen_bases": b.stolen_bases,
            "walks": b.walks,
            "strikeouts": b.strikeouts,
            "left_on_base": b.left_on_base,
            "avg": b.avg,
            "obp": b.obp,
            "slg": b.slg,
            "ops": b.ops,
            "raw": b.raw,
        }
        for b in all_batting_stats
    ]

    pitching_rows = [
        {
            "game_id": p.game_id,
            "player_id": p.player_id,
            "team_id": p.team_id,
            "player_name": p.player_name,
            "innings_pitched": p.innings_pitched,
            "hits": p.hits,
            "runs": p.runs,
            "earned_runs": p.earned_runs,
            "walks": p.walks,
            "strikeouts": p.strikeouts,
            "home_runs": p.home_runs,
            "pitches": p.pitches,
            "strikes": p.strikes,
            "era": p.era,
            "raw": p.raw,
        }
        for p in all_pitching_stats
    ]

    logger.info(f"Connecting to BigQuery project={cfg.project_id}")

    ensure_raw_dataset(client, cfg.project_id)
    ensure_mlb_tables(client, cfg.project_id)

    inserted_batting = upsert_mlb_player_batting_stats(client, cfg.project_id, batting_rows)
    inserted_pitching = upsert_mlb_player_pitching_stats(client, cfg.project_id, pitching_rows)

    logger.info(
        f"Ingest complete season={season} batting_stats={inserted_batting} pitching_stats={inserted_pitching}"
    )
    return inserted_batting, inserted_pitching
