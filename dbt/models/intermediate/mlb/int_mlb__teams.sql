{{ config(
    tags=["int", "mlb"],
    materialized='table'
) }}

-- Intermediate model for MLB teams
-- No additional enrichment needed at intermediate layer for reference data

select
    team_id,
    season,
    team_name,
    team_abbr,
    league_id,
    division_id
from {{ ref('stg_mlb__teams') }}
