{{ config(
  tags=["core", "mlb"],
  materialized='table'
) }}

-- Core dimension table for MLB divisions
-- Single source of truth for division reference data
-- Includes enriched league information

select *
from {{ ref('int_mlb__divisions_enriched') }}
