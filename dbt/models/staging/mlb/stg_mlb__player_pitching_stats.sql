{{ config(tags=["stg", "mlb", "player_stats"]) }}

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
  cast(era as string) as era
from {{ source('raw', 'mlb_player_pitching_stats') }}
