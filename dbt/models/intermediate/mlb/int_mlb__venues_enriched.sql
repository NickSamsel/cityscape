{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["int", "mlb"]
  )
-}}

-- Intermediate model for MLB teams
-- No additional enrichment needed at intermediate layer for reference data

select 

from {{ ref('stg_mlb__venues') }}

{% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.team_id = team_id
      and existing.season = season
  )
{% endif %}
