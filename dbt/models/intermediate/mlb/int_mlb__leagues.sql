{{-
  config(
    materialized='incremental',
    unique_key='league_id',
    on_schema_change='sync_all_columns',
    tags=["int", "mlb"]
  )
-}}

-- Intermediate model for MLB leagues
-- No additional enrichment needed at intermediate layer for reference data

select
    league_id,
    league_name,
    league_abbr
from {{ ref('stg_mlb__leagues') }}

{% if is_incremental() %}
  where league_id not in (select league_id from {{ this }})
{% endif %}
