"""MLB ingestion modules."""

from .player_stats import (
    fetch_game_player_stats,
    ingest_player_stats_parallel,
    ingest_player_stats_sequential,
)
from .players import (
    fetch_player_info,
    get_unique_player_ids_from_bigquery,
    ingest_players_from_rosters,
    ingest_players_from_stats,
    ingest_players_parallel,
)
from .rosters import (
    fetch_team_roster,
    get_unique_player_ids_from_rosters,
    ingest_mlb_rosters_bigquery,
)
from .schedule import (
    ingest_mlb_schedule_bigquery,
)
from .seasons import (
    fetch_mlb_reference_data,
    fetch_mlb_season_data,
    ingest_mlb_multi_season_bigquery,
    ingest_mlb_season_bigquery,
)
from .standings import (
    ingest_standings_bulk_historical,
    ingest_standings_historical,
    ingest_standings_historical_parallel,
    ingest_standings_snapshot,
)
from .statcast import (
    fetch_mlb_statcast_data,
    ingest_mlb_statcast_data_bigquery,
)
from .venues import (
    ingest_mlb_venues_bigquery,
)

__all__ = [
    # seasons
    "fetch_mlb_season_data",
    "fetch_mlb_reference_data",
    "ingest_mlb_season_bigquery",
    "ingest_mlb_multi_season_bigquery",
    # schedule
    "ingest_mlb_schedule_bigquery",
    # venues
    "ingest_mlb_venues_bigquery",
    # rosters
    "fetch_team_roster",
    "get_unique_player_ids_from_rosters",
    "ingest_mlb_rosters_bigquery",
    # player_stats
    "fetch_game_player_stats",
    "ingest_player_stats_parallel",
    "ingest_player_stats_sequential",
    # players
    "fetch_player_info",
    "get_unique_player_ids_from_bigquery",
    "ingest_players_from_rosters",
    "ingest_players_from_stats",
    "ingest_players_parallel",
    # standings
    "ingest_standings_snapshot",
    "ingest_standings_historical",
    "ingest_standings_historical_parallel",
    "ingest_standings_bulk_historical",
    # statcast
    "fetch_mlb_statcast_data",
    "ingest_mlb_statcast_data_bigquery",
]
