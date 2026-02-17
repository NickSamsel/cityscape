{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "dimension", "venues"]
  )
-}}

-- Dimension table for MLB venues (ballparks)
-- One row per venue_id using the latest available season
{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "dimension"]
  )
-}}

-- Mart dimension table for MLB venues
-- Analytics-ready view built from core model
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('core_mlb__venues') }}
