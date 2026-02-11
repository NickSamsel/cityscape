{{ config(
    tags=["mart", "mlb", "fact", "player_stats"],
    materialized='table'
) }}

-- Mart fact table for MLB player batting statistics
-- Analytics-ready view built from core model
-- Each row represents a batter's performance in a single game

select *
from {{ ref('core_mlb__player_batting_stats') }}
