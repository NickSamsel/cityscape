{{ config(
    tags=["mart", "mlb", "dimension"],
    materialized='table'
) }}

-- Mart dimension table for MLB teams
-- Analytics-ready view built from core model
-- This is a slowly changing dimension (Type 2) with season as the effective date

select *
from {{ ref('core_mlb__teams') }}
