{{ config(
    tags=["mart", "mlb", "dimension"],
    materialized='table'
) }}

-- Dimension table for MLB teams
-- This is a slowly changing dimension (Type 2) with season as the effective date

select
    team_id,
    season,
    team_name,
    team_abbr,
    league_id,
    division_id
from {{ ref('stg_mlb__teams') }}
