{{ config(
    tags=["mart", "mlb", "dimension"],
    materialized='table'
) }}

-- Mart dimension table for MLB players
-- Analytics-ready view built from core model

select *
from {{ ref('core_mlb__players') }}