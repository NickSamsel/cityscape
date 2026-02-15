{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id', 'team_side'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb", "schedule"]
  )
-}}

with source as (
  select
    {{ cast_string('game_id') }} as game_id,
    {{ cast_string('player_id') }} as player_id,
    {{ cast_string('team_side') }} as team_side,
    {{ cast_string('full_name') }} as full_name,
    {{ cast_string('position_abbreviation') }} as position_abbreviation,
    {{ cast_integer('batting_order') }} as batting_order,
    row_number() over (
      partition by {{ cast_string('game_id') }}, {{ cast_string('player_id') }}, {{ cast_string('team_side') }}
      order by loaded_at desc
    ) as row_num
  from {{ source('raw', 'mlb_game_lineups') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = {{ cast_string('game_id') }}
      and existing.player_id = {{ cast_string('player_id') }}
      and existing.team_side = {{ cast_string('team_side') }}
  )
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
