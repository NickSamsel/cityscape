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
    tags=["mart", "mlb", "fact"]
  )
-}}

-- Mart fact table for MLB games
-- Analytics-ready view built from core model
-- Each row represents a single game with full team and outcome information

select *
from {{ ref('int_mlb__games_enriched') }}
