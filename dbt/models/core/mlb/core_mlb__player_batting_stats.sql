{{ config(
  tags=["core", "mlb", "player_stats"],
  materialized='table'
) }}

-- Core fact table for MLB player batting statistics
-- Single source of truth for batter game-level performance
-- Each row represents a batter's performance in a single game

select *
from {{ ref('int_mlb__player_batting_stats_enriched') }}
