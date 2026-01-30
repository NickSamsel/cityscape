{{ config(tags=["core", "nhl"]) }}

select
  game_id,
  game_date,
  home_team_id,
  home_team_name,
  away_team_id,
  away_team_name
from {{ ref('int_nhl__games_enriched') }}
