{{-
  config(
    materialized='incremental',
    unique_key='play_id',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["batter_id", "pitcher_id", "season"],
    on_schema_change='sync_all_columns',
    tags=["core", "mlb", "statcast"]
  )
-}}

-- Core fact table for MLB Statcast pitch-level data
-- Single source of truth for pitch metrics
-- Each row represents a single pitch in a game

select *
from {{ ref('int_mlb__statcast_pitches_enriched') }}
