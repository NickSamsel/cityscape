{{-
  config(
    materialized='incremental',
    unique_key='player_id',
    on_schema_change='sync_all_columns',
    tags=["core", "mlb"]
  )
-}}

-- Core dimension table for MLB players
-- Single source of truth for player reference data

select *
from {{ ref('int_mlb__players') }}