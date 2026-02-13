{{-
  config(
    materialized='table',
    tags=["mart", "nba", "fact", "player_season"]
  )
-}}

-- Mart fact table for NBA player season statistics
-- Analytics-ready view built from core model
-- Each row represents a player's performance for a team in a season

select *
from {{ ref('core_nba__player_season_stats') }}
