{{ config(
  tags=["core", "mlb"],
  materialized='table'
) }}

-- Core dimension table for MLB players
-- Single source of truth for player reference data

select *
from {{ ref('int_mlb__players') }}