{{-
  config(
    materialized='incremental',
    unique_key='league_id',
    on_schema_change='sync_all_columns',
    tags=["core", "mlb"]
  )
-}}

-- Core dimension table for MLB leagues
-- Single source of truth for league reference data

select *
from {{ ref('int_mlb__leagues') }}
