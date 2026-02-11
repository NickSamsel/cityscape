{{ config(
  tags=["core", "mlb"],
  materialized='table'
) }}

-- Core dimension table for MLB teams
-- Single source of truth for team reference data
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('int_mlb__teams') }}
