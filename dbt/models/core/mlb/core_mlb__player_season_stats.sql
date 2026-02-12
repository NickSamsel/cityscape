{{-
  config(
    materialized='table',
    tags=["core", "mlb", "player_season"]
  )
-}}

-- Core fact table for MLB player season statistics
-- Single source of truth for player season-level performance
-- Each row represents a player's performance for their primary team in a season

select *
from {{ ref('int_mlb__player_season_stats_enriched') }}
