{{ config(
    tags=["mart", "mlb", "fact"],
    materialized='table'
) }}

-- Mart fact table for MLB games
-- Analytics-ready view built from core model
-- Each row represents a single game with full team and outcome information

select *
from {{ ref('core_mlb__games') }}
