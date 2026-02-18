{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb", "player_season"]
  )
-}}

-- Intermediate enriched player season statistics
-- Combines Statcast metrics with traditional batting stats and team context
-- Adds percentile rankings for MLB Savant-style analytics

with statcast_metrics as (

    select * from {{ ref('int_mlb__player_season_statcast_metrics') }}

),

batting_stats as (

    select * from {{ ref('int_mlb__player_batting_stats_enriched') }}

),

games as (

    select * from {{ ref('int_mlb__games_enriched') }}

),

-- Get player-team-season combinations from batting stats
player_team_seasons as (

    select
        bs.player_id,
        bs.team_id,
        g.season,
        count(distinct bs.game_id) as games_played,
        sum(bs.at_bats) as at_bats,
        sum(bs.hits) as hits,
        sum(bs.doubles) as doubles,
        sum(bs.triples) as triples,
        sum(bs.home_runs) as home_runs_traditional,
        sum(bs.rbi) as rbi,
        sum(bs.runs) as runs,
        sum(bs.walks) as walks,
        sum(bs.strikeouts) as strikeouts,
        sum(bs.stolen_bases) as stolen_bases
    from batting_stats as bs
    inner join games as g
        on bs.game_id = g.game_id
    where g.season is not null
    group by 1, 2, 3

),

-- For players who changed teams, get their primary team (most games played)
player_primary_team_season as (

    select
        player_id,
        season,
        team_id as primary_team_id,
        games_played as primary_team_games,
        at_bats,
        hits,
        doubles,
        triples,
        home_runs_traditional,
        rbi,
        runs,
        walks,
        strikeouts,
        stolen_bases,
        row_number() over (
            partition by player_id, season 
            order by games_played desc, at_bats desc
        ) as team_rank
    from player_team_seasons

),

-- Combine statcast metrics with team and batting metrics
combined_metrics as (

    select
        sc.player_id,
        pts.primary_team_id as team_id,
        sc.season,
        
        -- Game counts
        pts.primary_team_games as games_played,
        sc.games_with_batted_balls,
        
        -- Traditional batting stats
        pts.at_bats,
        pts.hits,
        pts.doubles,
        pts.triples,
        pts.home_runs_traditional,
        pts.rbi,
        pts.runs,
        pts.walks,
        pts.strikeouts,
        pts.stolen_bases,
        
        -- Statcast batted ball metrics
        sc.total_batted_balls,
        sc.max_exit_velocity,
        sc.avg_exit_velocity,
        sc.p90_exit_velocity,
        sc.stddev_exit_velocity,
        sc.avg_launch_angle,
        sc.stddev_launch_angle,
        sc.avg_launch_distance,
        sc.max_launch_distance,
        
        -- Quality metrics
        sc.total_barrels,
        sc.total_hard_hits,
        sc.total_home_runs as home_runs_statcast,
        sc.total_hits as hits_statcast,
        sc.barrel_rate,
        sc.hard_hit_rate,
        sc.home_run_rate,
        
        -- Trajectory
        sc.fly_balls,
        sc.line_drives,
        sc.ground_balls,
        sc.popups,
        
        -- Sprint speed
        sc.avg_sprint_speed,
        sc.max_sprint_speed,
        
        -- Derived metrics
        safe_divide(pts.hits, pts.at_bats) as batting_average,
        safe_divide(pts.hits + pts.walks, pts.at_bats + pts.walks) as on_base_percentage,
        safe_divide(
            pts.hits - pts.doubles - pts.triples - pts.home_runs_traditional +
            (pts.doubles * 2) + (pts.triples * 3) + (pts.home_runs_traditional * 4),
            pts.at_bats
        ) as slugging_percentage,

        -- Additional advanced metrics
        -- OPS = On-Base Percentage + Slugging Percentage
        safe_divide(pts.hits + pts.walks, pts.at_bats + pts.walks) +
        safe_divide(
            pts.hits - pts.doubles - pts.triples - pts.home_runs_traditional +
            (pts.doubles * 2) + (pts.triples * 3) + (pts.home_runs_traditional * 4),
            pts.at_bats
        ) as ops,

        -- ISO = Slugging - Batting Average (measures raw power)
        safe_divide(
            pts.hits - pts.doubles - pts.triples - pts.home_runs_traditional +
            (pts.doubles * 2) + (pts.triples * 3) + (pts.home_runs_traditional * 4),
            pts.at_bats
        ) - safe_divide(pts.hits, pts.at_bats) as isolated_power,

        -- Singles (for wOBA calculation)
        pts.hits - pts.doubles - pts.triples - pts.home_runs_traditional as singles,

        -- Plate appearances (AB + BB) - simplified without HBP, SF, SH
        pts.at_bats + pts.walks as plate_appearances,

        -- wOBA = (0.69*BB + 0.72*HBP + 0.88*1B + 1.24*2B + 1.56*3B + 1.95*HR) / (AB + BB + SF + HBP)
        -- Simplified without HBP, SF (using 2023 weights)
        safe_divide(
            (0.69 * pts.walks) +
            (0.88 * (pts.hits - pts.doubles - pts.triples - pts.home_runs_traditional)) +
            (1.24 * pts.doubles) +
            (1.56 * pts.triples) +
            (1.95 * pts.home_runs_traditional),
            pts.at_bats + pts.walks
        ) as woba,

        -- K% = Strikeouts / Plate Appearances
        safe_divide(pts.strikeouts, pts.at_bats + pts.walks) * 100 as k_percentage,

        -- BB% = Walks / Plate Appearances
        safe_divide(pts.walks, pts.at_bats + pts.walks) * 100 as bb_percentage

    from statcast_metrics as sc
    left join player_primary_team_season as pts
        on sc.player_id = pts.player_id
        and sc.season = pts.season
        and pts.team_rank = 1  -- Only join primary team

),

-- Calculate league averages for WAR calculation
league_averages as (

    select
        season,
        avg(woba) as league_avg_woba,
        avg(ops) as league_avg_ops
    from combined_metrics
    where plate_appearances >= 100  -- Minimum PA threshold
    group by season

),

-- Add WAR calculations
with_war as (

    select
        cm.*,
        la.league_avg_woba,

        -- Simplified offensive WAR calculation
        -- WAR ≈ ((wOBA - league_avg_wOBA) / 1.15) * (PA / 10)
        -- This is a very simplified version without positional adjustments or defense
        safe_divide(
            (cm.woba - la.league_avg_woba) * cm.plate_appearances,
            115
        ) as simplified_offensive_war

    from combined_metrics as cm
    left join league_averages as la
        on cm.season = la.season

),

-- Add percentile rankings
enriched as (

    select
        *,
        
        -- Percentile rankings (0-100 scale like MLB Savant)
        percent_rank() over (
            partition by season 
            order by max_exit_velocity
        ) * 100 as exit_velo_percentile,
        
        percent_rank() over (
            partition by season 
            order by avg_exit_velocity
        ) * 100 as avg_exit_velo_percentile,
        
        percent_rank() over (
            partition by season 
            order by home_runs_traditional
        ) * 100 as home_run_percentile,
        
        percent_rank() over (
            partition by season 
            order by barrel_rate
        ) * 100 as barrel_rate_percentile,
        
        percent_rank() over (
            partition by season 
            order by hard_hit_rate
        ) * 100 as hard_hit_rate_percentile,
        
        percent_rank() over (
            partition by season 
            order by max_launch_distance
        ) * 100 as max_distance_percentile,
        
        percent_rank() over (
            partition by season
            order by avg_sprint_speed
        ) * 100 as sprint_speed_percentile,

        -- Percentiles for new advanced metrics
        percent_rank() over (
            partition by season
            order by ops
        ) * 100 as ops_percentile,

        percent_rank() over (
            partition by season
            order by isolated_power
        ) * 100 as iso_percentile,

        percent_rank() over (
            partition by season
            order by woba
        ) * 100 as woba_percentile,

        percent_rank() over (
            partition by season
            order by batting_average
        ) * 100 as batting_avg_percentile,

        percent_rank() over (
            partition by season
            order by on_base_percentage
        ) * 100 as obp_percentile,

        percent_rank() over (
            partition by season
            order by slugging_percentage
        ) * 100 as slg_percentile,

        -- Lower K% is better, higher BB% is better
        (100 - percent_rank() over (
            partition by season
            order by k_percentage
        ) * 100) as k_percentage_percentile,

        percent_rank() over (
            partition by season
            order by bb_percentage
        ) * 100 as bb_percentage_percentile,

        -- WAR percentile
        percent_rank() over (
            partition by season
            order by simplified_offensive_war
        ) * 100 as war_percentile

    from with_war
    where team_id is not null  -- Filter out players without team assignments

)

select * from enriched
