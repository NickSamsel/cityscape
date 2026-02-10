{{ config(tags=["stg", "mlb"]) }}

select
  cast(game_id as string) as game_id,
  cast(season as int64) as season,
  cast(game_date as date) as game_date,
  cast(game_type as string) as game_type,
  cast(status as string) as status,
  cast(home_team_id as string) as home_team_id,
  cast(away_team_id as string) as away_team_id,
  cast(home_score as int64) as home_score,
  cast(away_score as int64) as away_score
from {{ source('raw', 'mlb_games') }}
