{{ config(tags=["stg", "mlb"]) }}

select
  cast(game_id as varchar) as game_id,
  cast(season as integer) as season,
  cast(game_date as date) as game_date,
  cast(game_type as varchar) as game_type,
  cast(status as varchar) as status,
  cast(home_team_id as varchar) as home_team_id,
  cast(away_team_id as varchar) as away_team_id,
  cast(home_score as integer) as home_score,
  cast(away_score as integer) as away_score
from {{ source('raw', 'mlb_games') }}
