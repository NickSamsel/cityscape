{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'broadcast_name'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "schedule"]
  )
-}}

-- Mart fact table for MLB game broadcasts
-- Each row represents a single broadcast outlet for a game
-- Useful for analyzing broadcast coverage, national vs local, TV vs radio

with broadcasts as (

    select * from {{ ref('stg_mlb__game_broadcasts') }}
    {% if is_incremental() %}
    where not exists (
        select 1 from {{ this }} as existing
        where existing.game_id = stg_mlb__game_broadcasts.game_id
          and existing.broadcast_name = stg_mlb__game_broadcasts.broadcast_name
    )
    {% endif %}

),

schedule as (

    select
        game_id,
        season,
        game_date,
        home_team_id,
        away_team_id,
        venue_name
    from {{ ref('stg_mlb__schedule') }}

)

select
    b.game_id,
    s.season,
    s.game_date,
    s.home_team_id,
    s.away_team_id,
    s.venue_name,
    b.broadcast_name,
    b.broadcast_type,
    b.call_sign,
    b.is_national,
    b.home_away,
    b.language
from broadcasts as b
left join schedule as s
    on b.game_id = s.game_id
