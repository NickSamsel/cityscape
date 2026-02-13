{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "nba", "games"]
  )
-}}

source_data as (
  select
    {{ cast_string('game_id') }} as game_id,
    {{ cast_integer('season') }} as season,
    {{ cast_string('season_type') }} as season_type,
    {{ cast_date('game_date') }} as game_date,
    {{ cast_string('status') }} as status,
    {{ cast_string('home_team_id') }} as home_team_id,
    {{ cast_string('away_team_id') }} as away_team_id,
    {{ cast_integer('home_score') }} as home_score,
    {{ cast_integer('away_score') }} as away_score,
    {{ cast_string('arena') }} as arena,
    {{ cast_integer('attendance') }} as attendance,
    loaded_at
  from {{ source('raw', 'nba_games') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = {{ cast_string('game_id') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by game_id
      order by loaded_at desc
    ) as row_num
  from source_data
)

select
  game_id,
  season,
  season_type,
  game_date,
  status,
  home_team_id,
  away_team_id,
  home_score,
  away_score,
  arena,
  attendance
from deduplicated
where row_num = 1
