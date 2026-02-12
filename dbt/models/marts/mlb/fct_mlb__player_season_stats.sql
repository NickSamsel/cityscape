{{-
  config(
    materialized='table',
    tags=["mart", "mlb", "fact", "player_season"]
  )
-}}

-- Mart fact table for MLB player season statistics
-- Analytics-ready view built from core model
-- Each row represents a player's performance for their primary team in a season

select *
from {{ ref('core_mlb__player_season_stats') }}
