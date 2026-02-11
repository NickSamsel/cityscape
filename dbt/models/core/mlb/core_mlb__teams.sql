{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["core", "mlb"]
  )
-}}

-- Core dimension table for MLB teams
-- Single source of truth for team reference data
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('int_mlb__teams') }}
