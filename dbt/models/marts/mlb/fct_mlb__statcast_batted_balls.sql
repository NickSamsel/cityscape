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
    tags=["mart", "mlb", "fact", "statcast"]
  )
-}}

-- Mart fact table for MLB Statcast batted ball data
-- Analytics-ready view of every batted ball with complete context
-- Each row represents a single batted ball with exit velocity, launch angle, and outcomes

select *
from {{ ref('int_mlb__statcast_batted_balls_enriched') }}
