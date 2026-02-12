{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb", "statcast", "player_season"]
  )
-}}

-- Intermediate model for player season-level statcast metrics
-- Aggregates batted ball data to player-season grain
-- Used downstream for player season stat rankings and analysis

with batted_balls as (

    select * from {{ ref('fct_mlb__statcast_batted_balls') }}

),

player_season_aggregates as (

    select
        batter_id as player_id,
        season,
        
        -- Batted ball counts
        count(*) as total_batted_balls,
        count(distinct game_id) as games_with_batted_balls,
        
        -- Exit velocity metrics
        max(launch_speed) as max_exit_velocity,
        avg(launch_speed) as avg_exit_velocity,
        approx_quantiles(launch_speed, 100)[offset(90)] as p90_exit_velocity,
        stddev(launch_speed) as stddev_exit_velocity,
        
        -- Launch angle metrics
        avg(launch_angle) as avg_launch_angle,
        stddev(launch_angle) as stddev_launch_angle,
        
        -- Distance metrics
        avg(launch_distance) as avg_launch_distance,
        max(launch_distance) as max_launch_distance,
        
        -- Quality metrics  
        countif(is_barrel) as total_barrels,
        countif(is_hard_hit) as total_hard_hits,
        countif(is_home_run) as total_home_runs,
        countif(is_hit) as total_hits,
        
        -- Rates
        safe_divide(countif(is_barrel), count(*)) as barrel_rate,
        safe_divide(countif(is_hard_hit), count(*)) as hard_hit_rate,
        safe_divide(countif(is_home_run), count(*)) as home_run_rate,
        
        -- Trajectory distribution
        countif(hit_trajectory = 'fly_ball') as fly_balls,
        countif(hit_trajectory = 'line_drive') as line_drives,
        countif(hit_trajectory = 'ground_ball') as ground_balls,
        countif(hit_trajectory = 'popup') as popups,
        
        -- Sprint speed
        avg(sprint_speed) as avg_sprint_speed,
        max(sprint_speed) as max_sprint_speed
        
    from batted_balls
    where batter_id is not null
        and season is not null
    group by 1, 2

)

select * from player_season_aggregates
