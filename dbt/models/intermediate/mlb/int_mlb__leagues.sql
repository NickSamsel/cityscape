{{ config(
    tags=["int", "mlb"],
    materialized='table'
) }}

-- Intermediate model for MLB leagues
-- No additional enrichment needed at intermediate layer for reference data

select
    league_id,
    league_name,
    league_abbr
from {{ ref('stg_mlb__leagues') }}
