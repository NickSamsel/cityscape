{{ config(
  tags=["core", "mlb"],
  materialized='table'
) }}

-- Core dimension table for MLB leagues
-- Single source of truth for league reference data

select *
from {{ ref('int_mlb__leagues') }}
