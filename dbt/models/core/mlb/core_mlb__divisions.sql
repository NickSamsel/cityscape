{{-
  config(
    materialized='incremental',
    unique_key='division_id',
    on_schema_change='sync_all_columns',
    tags=["core", "mlb"]
  )
-}}

-- Core dimension table for MLB divisions
-- Single source of truth for division reference data
-- Includes enriched league information

select *
from {{ ref('int_mlb__divisions_enriched') }}
