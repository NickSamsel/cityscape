{{ config(tags=["int", "mlb", "player_stats"]) }}

select
  ps.game_id,
  ps.player_id,
  ps.player_name,
  ps.team_id,
  t.team_name,
  t.team_abbr,
  g.game_date,
  g.season,
  g.game_type,
  ps.innings_pitched,
  ps.hits,
  ps.runs,
  ps.earned_runs,
  ps.walks,
  ps.strikeouts,
  ps.home_runs,
  ps.pitches,
  ps.strikes,
  ps.era
from {{ ref('stg_mlb__player_pitching_stats') }} as ps
left join {{ ref('stg_mlb__games') }} as g
  on ps.game_id = cast(g.game_id as string)
left join {{ ref('stg_mlb__teams') }} as t
  on ps.team_id = t.team_id and g.season = t.season
