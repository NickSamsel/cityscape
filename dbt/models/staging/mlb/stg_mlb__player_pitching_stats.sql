{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id', 'team_id'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb", "player_stats"]
  )
-}}

with source as (
  select
    cast(game_id as string) as game_id,
    cast(player_id as string) as player_id,
    cast(team_id as string) as team_id,
    cast(player_name as string) as player_name,
    cast(innings_pitched as string) as innings_pitched,
    cast(hits as int64) as hits,
    cast(runs as int64) as runs,
    cast(earned_runs as int64) as earned_runs,
    cast(walks as int64) as walks,
    cast(strikeouts as int64) as strikeouts,
    cast(home_runs as int64) as home_runs,
    cast(pitches as int64) as pitches,
    cast(strikes as int64) as strikes,
    cast(era as string) as era,
    row_number() over (
      partition by cast(game_id as string), cast(player_id as string), cast(team_id as string)
      order by safe_cast(nullif(cast(innings_pitched as string), '-.--') as float64) desc nulls last
    ) as row_num
  from {{ source('raw', 'mlb_player_pitching_stats') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = cast(game_id as string)
      and existing.player_id = cast(player_id as string)
      and existing.team_id = cast(team_id as string)
  )
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
