{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='game_id',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "home_team_id", "away_team_id"],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "schedule"]
  )
-}}

-- Mart fact table for MLB schedule
-- Analytics-ready view with full team context, venue, and probable pitcher information
-- Each row represents a scheduled or completed game

select * from {{ ref('int_mlb__schedule_enriched') }}
