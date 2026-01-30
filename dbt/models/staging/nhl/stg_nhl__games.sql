{{ config(tags=["stg", "nhl"]) }}

select
  cast(null as varchar) as game_id,
  cast(null as date) as game_date,
  cast(null as varchar) as home_team_id,
  cast(null as varchar) as away_team_id
from {{ source('raw', 'nhl_games') }}
where 1 = 0
