from __future__ import annotations

"""BigQuery helpers.

This module was converted from a single file into a package so we can add
sport-specific modules (e.g. nfl.py) and shared engines without a monolith.

Backwards compatibility: existing imports like
`from src.utils.bigquery import upsert_mlb_players` still work.
"""

# Re-export the legacy API surface.
from .legacy import *  # noqa: F403

# New Option-B building blocks.
from .engine import UpsertTableConfig, build_merge_sql, ensure_table, upsert_dataframe

# MLB schedule upserts migrated to the generic engine (override legacy symbols).
from .mlb import (
    ensure_mlb_tables,
    ensure_mlb_schedule_tables,
    upsert_mlb_game_broadcasts,
    upsert_mlb_game_lineups,
    upsert_mlb_games,
    upsert_mlb_divisions,
    upsert_mlb_leagues,
    upsert_mlb_player_batting_stats,
    upsert_mlb_player_pitching_stats,
    upsert_mlb_players,
    upsert_mlb_schedule,
    upsert_mlb_standings,
    upsert_mlb_statcast_batted_balls,
    upsert_mlb_statcast_pitches,
    upsert_mlb_teams,
    upsert_mlb_venues,
)

from .nba import ensure_nba_tables, upsert_nba_games, upsert_nba_teams

__all__ = [
    # legacy exports
    *[n for n in globals().keys() if not n.startswith("_")],
]
