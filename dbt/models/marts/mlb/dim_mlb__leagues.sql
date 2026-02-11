{{ config(
    tags=["mart", "mlb", "dimension"],
    materialized='table'
) }}

-- Dimension table for MLB leagues

select
    league_id,
    league_name,
    league_abbr
from {{ ref('stg_mlb__leagues') }}
