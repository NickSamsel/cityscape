{{ config(
    tags=["mart", "mlb", "fact"],
    materialized='table'
) }}

-- Fact table for MLB games
-- Each row represents a single game with full team and outcome information

select
    game_id,
    season,
    game_date,
    game_type,
    status,
    
    -- Home team
    home_team_id,
    home_team_name,
    home_team_abbr,
    home_league_id,
    home_division_id,
    home_score,
    
    -- Away team
    away_team_id,
    away_team_name,
    away_team_abbr,
    away_league_id,
    away_division_id,
    away_score,
    
    -- Game outcomes
    winning_team_id,
    losing_team_id,
    winner,
    score_differential,
    total_runs
    
from {{ ref('int_mlb__games_enriched') }}
