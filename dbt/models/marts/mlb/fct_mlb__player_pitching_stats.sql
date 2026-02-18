{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id', 'team_id'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "player_stats"]
  )
-}}

-- Mart fact table for MLB player pitching statistics
-- Analytics-ready view built from core model
-- Each row represents a pitcher's performance in a single game

select *
from {{ ref('int_mlb__player_pitching_stats_enriched') }}
