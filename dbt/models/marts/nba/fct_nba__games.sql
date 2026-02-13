{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "nba", "fact", "games"]
  )
-}}

-- Mart fact table for NBA games
-- Analytics-ready game-level facts

select *
from {{ ref('int_nba__games_enriched') }}

{% if is_incremental() %}
where game_id not in (select game_id from {{ this }})
{% endif %}
