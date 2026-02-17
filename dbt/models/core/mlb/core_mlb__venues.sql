{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["core", "mlb", "venues"]
  )
-}}

-- Core model for MLB venues (ballparks)
-- Normalized reference data derived from int_mlb__venues_enriched
-- Each row represents a unique venue-season combination
-- Serves as a single source of truth for venue attributes and metadata

select *
from {{ ref('int_mlb__venues_enriched') }}
