{{ config(
    tags=["mart", "mlb", "fact", "player_stats"],
    materialized='table'
) }}

-- Fact table for MLB player pitching statistics
-- Each row represents a pitcher's performance in a single game

select
    game_id,
    player_id,
    player_name,
    team_id,
    team_name,
    team_abbr,
    league_id,
    division_id,
    game_date,
    season,
    game_type,
    game_status,
    
    -- Raw counting stats
    innings_pitched,
    innings_pitched_decimal,
    hits,
    runs,
    earned_runs,
    walks,
    strikeouts,
    home_runs,
    pitches,
    strikes,
    
    -- Calculated metrics
    strike_percentage,
    whip,
    k_per_nine,
    bb_per_nine,
    era
    
from {{ ref('int_mlb__player_pitching_stats_enriched') }}
