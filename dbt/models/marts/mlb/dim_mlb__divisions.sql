{{ config(
    tags=["mart", "mlb", "dimension"],
    materialized='table'
) }}

-- Dimension table for MLB divisions

select
    division_id,
    division_name,
    division_abbr,
    league_id
from {{ ref('stg_mlb__divisions') }}
