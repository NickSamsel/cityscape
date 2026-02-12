{{-
  config(
    materialized='table',
    tags=["mart", "mlb", "fact", "player_season", "pitching"]
  )
-}}

-- Mart fact table for MLB player pitching season statistics
-- Analytics-ready view built from intermediate enriched model
-- Each row represents a pitcher's performance for their primary team in a season

select *
from {{ ref('int_mlb__player_pitching_season_stats_enriched') }}
