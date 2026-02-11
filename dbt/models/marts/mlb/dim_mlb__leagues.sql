{{-
  config(
    materialized='incremental',
    unique_key='league_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "dimension"]
  )
-}}

-- Mart dimension table for MLB leagues
-- Analytics-ready view built from core model

select *
from {{ ref('core_mlb__leagues') }}
