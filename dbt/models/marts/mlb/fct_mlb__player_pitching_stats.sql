{{ config(
    tags=["mart", "mlb", "fact", "player_stats"],
    materialized='table'
) }}

-- Mart fact table for MLB player pitching statistics
-- Analytics-ready view built from core model
-- Each row represents a pitcher's performance in a single game

select *
from {{ ref('core_mlb__player_pitching_stats') }}
