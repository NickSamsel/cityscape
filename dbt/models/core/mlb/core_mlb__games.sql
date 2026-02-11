{{ config(
  tags=["core", "mlb", "deprecated"],
  materialized='view'
) }}

/*
 * DEPRECATED: This model has been replaced by fct_mlb__games in marts/mlb/
 * Please use {{ ref('fct_mlb__games') }} instead.
 * This model will be removed in a future version.
 */

select
  game_id,
  game_date,
  home_team_id,
  home_team_name,
  away_team_id,
  away_team_name
from {{ ref('int_mlb__games_enriched') }}
