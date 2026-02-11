{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["core", "mlb"]
  )
-}}

-- Core fact table for MLB games
-- Single source of truth for game-level data
-- Each row represents a single MLB game

select *
from {{ ref('int_mlb__games_enriched') }}
