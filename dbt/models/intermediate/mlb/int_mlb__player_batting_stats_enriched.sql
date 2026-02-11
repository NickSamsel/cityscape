{{ config(tags=["int", "mlb", "player_stats"]) }}

select
  bs.game_id,
  bs.player_id,
  bs.player_name,
  bs.team_id,
  t.team_name,
  t.team_abbr,
  g.game_date,
  g.season,
  g.game_type,
  bs.batting_order,
  bs.position,
  bs.at_bats,
  bs.runs,
  bs.hits,
  bs.doubles,
  bs.triples,
  bs.home_runs,
  bs.rbi,
  bs.stolen_bases,
  bs.walks,
  bs.strikeouts,
  bs.left_on_base,
  bs.avg,
  bs.obp,
  bs.slg,
  bs.ops
from {{ ref('stg_mlb__player_batting_stats') }} as bs
left join {{ ref('stg_mlb__games') }} as g
  on bs.game_id = cast(g.game_id as string)
left join {{ ref('stg_mlb__teams') }} as t
  on bs.team_id = t.team_id and g.season = t.season
