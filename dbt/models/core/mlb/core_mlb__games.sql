{{ config(tags=["core", "mlb"]) }}

select
  game_id,
  game_date,
  home_team_id,
  home_team_name,
  away_team_id,
  away_team_name
from {{ ref('int_mlb__games_enriched') }}
