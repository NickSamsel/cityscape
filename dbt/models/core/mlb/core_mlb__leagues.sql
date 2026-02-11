{{ config(
  tags=["core", "mlb"],
  materialized='view'
) }}

-- Core model for MLB leagues
-- Simple pass-through from intermediate layer for reference data

select
  league_id,
  league_name,
  league_abbr
from {{ ref('int_mlb__leagues') }}
