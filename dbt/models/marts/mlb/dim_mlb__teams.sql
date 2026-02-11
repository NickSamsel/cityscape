{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "dimension"]
  )
-}}

-- Mart dimension table for MLB teams
-- Analytics-ready view built from core model
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('core_mlb__teams') }}
