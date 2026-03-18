{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "fact", "player_stats"]
  )
-}}

-- Mart fact table for MLB player batting statistics
-- Analytics-ready view built from core model
-- Each row represents a batter's performance in a single game

select *
from {{ ref('int_mlb__player_batting_stats_enriched') }}
