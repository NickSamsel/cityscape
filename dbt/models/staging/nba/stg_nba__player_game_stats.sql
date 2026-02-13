{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id'],
    on_schema_change='sync_all_columns',
    tags=["stg", "nba", "player_stats"]
  )
-}}

source_data as (
  select
    {{ cast_string('game_id') }} as game_id,
    {{ cast_string('player_id') }} as player_id,
    {{ cast_string('team_id') }} as team_id,
    {{ cast_string('player_name') }} as player_name,
    cast(starter as bool) as starter,
    {{ cast_string('minutes') }} as minutes,
    {{ cast_integer('field_goals_made') }} as field_goals_made,
    {{ cast_integer('field_goals_attempted') }} as field_goals_attempted,
    cast(field_goal_pct as float64) as field_goal_pct,
    {{ cast_integer('three_pointers_made') }} as three_pointers_made,
    {{ cast_integer('three_pointers_attempted') }} as three_pointers_attempted,
    cast(three_point_pct as float64) as three_point_pct,
    {{ cast_integer('free_throws_made') }} as free_throws_made,
    {{ cast_integer('free_throws_attempted') }} as free_throws_attempted,
    cast(free_throw_pct as float64) as free_throw_pct,
    {{ cast_integer('offensive_rebounds') }} as offensive_rebounds,
    {{ cast_integer('defensive_rebounds') }} as defensive_rebounds,
    {{ cast_integer('total_rebounds') }} as total_rebounds,
    {{ cast_integer('assists') }} as assists,
    {{ cast_integer('steals') }} as steals,
    {{ cast_integer('blocks') }} as blocks,
    {{ cast_integer('turnovers') }} as turnovers,
    {{ cast_integer('personal_fouls') }} as personal_fouls,
    {{ cast_integer('points') }} as points,
    {{ cast_integer('plus_minus') }} as plus_minus,
    loaded_at
  from {{ source('raw', 'nba_player_game_stats') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = {{ cast_string('game_id') }}
      and existing.player_id = {{ cast_string('player_id') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by game_id, player_id
      order by loaded_at desc
    ) as row_num
  from source_data
)

select
  game_id,
  player_id,
  team_id,
  player_name,
  starter,
  minutes,
  field_goals_made,
  field_goals_attempted,
  field_goal_pct,
  three_pointers_made,
  three_pointers_attempted,
  three_point_pct,
  free_throws_made,
  free_throws_attempted,
  free_throw_pct,
  offensive_rebounds,
  defensive_rebounds,
  total_rebounds,
  assists,
  steals,
  blocks,
  turnovers,
  personal_fouls,
  points,
  plus_minus
from deduplicated
where row_num = 1
