{{ config(tags=["stg", "nba"]) }}

-- ANSI-friendly patterns:
-- - use CAST(x AS type) instead of Postgres ::type
-- - avoid SELECT * in curated layers

select
  cast(null as varchar) as game_id,
  cast(null as date) as game_date,
  cast(null as varchar) as home_team_id,
  cast(null as varchar) as away_team_id
from {{ source('raw', 'nba_games') }}
where 1 = 0
