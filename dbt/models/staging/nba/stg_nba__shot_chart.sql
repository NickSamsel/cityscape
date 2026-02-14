{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'game_event_id'],
    on_schema_change='sync_all_columns',
    tags=["stg", "nba", "shot_chart", "shot_data"]
  )
-}}

with source_data as (
  select
    {{ cast_string('game_id') }} as game_id,
    {{ cast_integer('game_event_id') }} as game_event_id,
    {{ cast_string('player_id') }} as player_id,
    {{ cast_string('player_name') }} as player_name,
    {{ cast_string('team_id') }} as team_id,
    {{ cast_string('team_name') }} as team_name,
    {{ cast_integer('period') }} as period,
    {{ cast_integer('minutes_remaining') }} as minutes_remaining,
    {{ cast_integer('seconds_remaining') }} as seconds_remaining,
    {{ cast_string('event_type') }} as event_type,
    {{ cast_string('action_type') }} as action_type,
    {{ cast_string('shot_type') }} as shot_type,
    {{ cast_string('shot_zone_basic') }} as shot_zone_basic,
    {{ cast_string('shot_zone_area') }} as shot_zone_area,
    {{ cast_string('shot_zone_range') }} as shot_zone_range,
    {{ cast_integer('shot_distance') }} as shot_distance,
    {{ cast_integer('loc_x') }} as loc_x,
    {{ cast_integer('loc_y') }} as loc_y,
    {{ cast_integer('shot_attempted_flag') }} as shot_attempted_flag,
    {{ cast_integer('shot_made_flag') }} as shot_made_flag,
    {{ cast_string('game_date') }} as game_date,
    {{ cast_string('htm') }} as htm,
    {{ cast_string('vtm') }} as vtm,
    loaded_at
  from {{ source('raw', 'nba_shot_chart') }}

  {% if is_incremental() %}
  where loaded_at > (select max(loaded_at) from {{ this }})
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by game_id, game_event_id
      order by loaded_at desc
    ) as row_num
  from source_data
)

select
  game_id,
  game_event_id,
  player_id,
  player_name,
  team_id,
  team_name,
  period,
  minutes_remaining,
  seconds_remaining,
  event_type,
  action_type,
  shot_type,
  shot_zone_basic,
  shot_zone_area,
  shot_zone_range,
  shot_distance,
  loc_x,
  loc_y,
  shot_attempted_flag,
  shot_made_flag,
  game_date,
  htm,
  vtm
from deduplicated
where row_num = 1
