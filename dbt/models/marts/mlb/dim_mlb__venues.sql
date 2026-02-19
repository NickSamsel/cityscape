{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "dimension", "venues"]
  )
-}}

-- Mart dimension table for MLB venues
-- Analytics-ready view built from core model
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('int_mlb__venues_enriched') }}
