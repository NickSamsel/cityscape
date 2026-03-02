{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='play_id',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "pitcher_id", "batter_id"],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "statcast"]
  )
-}}

-- Mart fact table for MLB Statcast pitch-level data
-- Analytics-ready view of every pitch with complete context
-- Each row represents a single pitch with pitcher, batter, and game details

select *
from {{ ref('int_mlb__statcast_pitches_enriched') }}
