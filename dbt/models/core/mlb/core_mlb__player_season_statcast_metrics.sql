{{-
  config(
    materialized='table',
    tags=["core", "mlb", "statcast", "player_season"]
  )
-}}

-- Core table for player season-level Statcast metrics
-- Single source of truth for aggregated batted ball data by player-season
-- Each row represents a player's Statcast metrics for a season

select *
from {{ ref('int_mlb__player_season_statcast_metrics') }}
