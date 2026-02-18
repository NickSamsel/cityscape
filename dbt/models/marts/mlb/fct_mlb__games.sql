{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact"]
  )
-}}

-- Mart fact table for MLB games
-- Analytics-ready view built from core model
-- Each row represents a single game with full team and outcome information

select *
from {{ ref('int_mlb__games_enriched') }}
