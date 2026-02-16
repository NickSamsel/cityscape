{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["core", "mlb", "venues"]
  )
-}}

-- Core model for MLB venues (ballparks)
-- Normalized reference data derived from stg_mlb__venues

select *
from {{ ref('stg_mlb__venues') }}
