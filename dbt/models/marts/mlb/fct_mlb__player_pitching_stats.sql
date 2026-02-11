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
    league_name,
    league_abbr_name,
    division_id,
    division_name,
    division_abbr_name,
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
    k_bb_ratio,
    hr_per_nine,
    h_per_nine,
    fip,
    pitches_per_inning,
    k_percentage,
    is_quality_start,
    
    -- Season ERA from API
    era
    
from {{ ref('int_mlb__player_pitching_stats_enriched') }}
