{{ config(tags=["int", "nba"]) }}

select
  g.game_id,
  g.game_date,
  g.home_team_id,
  ht.team_name as home_team_name,
  g.away_team_id,
  at.team_name as away_team_name
from {{ ref('stg_nba__games') }} as g
left join {{ ref('stg_nba__teams') }} as ht
  on g.home_team_id = ht.team_id
left join {{ ref('stg_nba__teams') }} as at
  on g.away_team_id = at.team_id
