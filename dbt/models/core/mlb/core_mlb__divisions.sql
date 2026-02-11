{{ config(
  tags=["core", "mlb"],
  materialized='view'
) }}

-- Core model for MLB divisions
-- Includes enriched league information

select
  division_id,
  division_name,
  division_abbr,
  league_id,
  league_name,
  league_abbr_name
from {{ ref('int_mlb__divisions_enriched') }}
