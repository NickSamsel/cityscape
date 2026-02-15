{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "schedule"]
  )
-}}

-- Mart fact table for MLB schedule
-- Analytics-ready view with full team context, venue, and probable pitcher information
-- Each row represents a scheduled or completed game

select * from {{ ref('int_mlb__schedule_enriched') }}

{% if is_incremental() %}
where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = int_mlb__schedule_enriched.game_id
)
{% endif %}
