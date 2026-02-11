{{ config(
  tags=["core", "mlb", "player_stats"],
  materialized='table'
) }}

-- Core fact table for MLB player pitching statistics
-- Single source of truth for pitcher game-level performance
-- Each row represents a pitcher's performance in a single game

select *
from {{ ref('int_mlb__player_pitching_stats_enriched') }}
