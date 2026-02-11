{{ config(tags=["stg", "mlb", "player_stats"]) }}

select
  cast(game_id as string) as game_id,
  cast(player_id as string) as player_id,
  cast(team_id as string) as team_id,
  cast(player_name as string) as player_name,
  cast(batting_order as string) as batting_order,
  cast(position as string) as position,
  cast(at_bats as int64) as at_bats,
  cast(runs as int64) as runs,
  cast(hits as int64) as hits,
  cast(doubles as int64) as doubles,
  cast(triples as int64) as triples,
  cast(home_runs as int64) as home_runs,
  cast(rbi as int64) as rbi,
  cast(stolen_bases as int64) as stolen_bases,
  cast(walks as int64) as walks,
  cast(strikeouts as int64) as strikeouts,
  cast(left_on_base as int64) as left_on_base,
  cast(avg as string) as avg,
  cast(obp as string) as obp,
  cast(slg as string) as slg,
  cast(ops as string) as ops
from {{ source('raw', 'mlb_player_batting_stats') }}
