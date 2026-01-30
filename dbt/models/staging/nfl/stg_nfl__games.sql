{{ config(tags=["stg", "nfl"]) }}

select
  cast(null as varchar) as game_id,
  cast(null as date) as game_date,
  cast(null as varchar) as home_team_id,
  cast(null as varchar) as away_team_id
from {{ source('raw', 'nfl_games') }}
where 1 = 0
