{{ config(
    tags=["mart", "mlb", "fact", "player_stats"],
    materialized='table'
) }}

-- Fact table for MLB player batting statistics
-- Each row represents a player's batting performance in a single game

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
    batting_order,
    position,
    
    -- Raw counting stats
    at_bats,
    runs,
    hits,
    singles,
    doubles,
    triples,
    home_runs,
    rbi,
    stolen_bases,
    walks,
    strikeouts,
    left_on_base,
    
    -- Calculated stats
    total_bases,
    plate_appearances,
    extra_base_hits,
    
    -- Advanced metrics
    batting_avg_game,
    slugging_pct_game,
    iso,
    babip,
    walk_rate,
    strikeout_rate,
    bb_k_ratio,
    power_factor,
    
    -- Season rate stats from API
    avg,
    obp,
    slg,
    ops
    
from {{ ref('int_mlb__player_batting_stats_enriched') }}
