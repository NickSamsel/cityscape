{{ config(
  tags=["core", "mlb"],
  materialized='table'
) }}

-- Core fact table for MLB games
-- Single source of truth for game-level data
-- Each row represents a single MLB game

select *
from {{ ref('int_mlb__games_enriched') }}
