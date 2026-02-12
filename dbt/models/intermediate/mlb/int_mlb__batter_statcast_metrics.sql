{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb", "statcast"]
  )
-}}

-- Aggregate batted ball metrics by batter
-- Calculates average exit velocity, launch angle, barrel rate, and hard-hit rate

with batted_balls as (

    select * from {{ ref('stg_mlb__statcast_batted_balls') }}

),

batter_batted_ball_aggregates as (

    select
        cast(batter_id as string) as batter_id,
        
        -- Overall counts
        count(*) as total_batted_balls,
        count(distinct game_id) as games_with_batted_balls,
        
        -- Exit velocity metrics
        avg(launch_speed) as avg_exit_velocity,
        max(launch_speed) as max_exit_velocity,
        approx_quantiles(launch_speed, 100)[offset(90)] as p90_exit_velocity,
        stddev(launch_speed) as stddev_exit_velocity,
        
        -- Launch angle metrics
        avg(launch_angle) as avg_launch_angle,
        stddev(launch_angle) as stddev_launch_angle,
        
        -- Distance metrics
        avg(launch_distance) as avg_launch_distance,
        max(launch_distance) as max_launch_distance,
        
        -- Quality metrics
        countif(is_barrel) as barrels,
        countif(is_hard_hit) as hard_hits,
        
        -- Trajectory distribution
        countif(hit_trajectory = 'fly_ball') as fly_balls,
        countif(hit_trajectory = 'line_drive') as line_drives,
        countif(hit_trajectory = 'ground_ball') as ground_balls,
        countif(hit_trajectory = 'popup') as popups,
        
        -- Sprint speed
        avg(sprint_speed) as avg_sprint_speed,
        
        -- Last updated
        max(loaded_at) as last_updated

    from batted_balls
    where launch_speed is not null
    group by batter_id

),

-- Calculate rates
batter_statcast_metrics as (

    select
        batter_id,
        
        -- Counts
        total_batted_balls,
        games_with_batted_balls,
        
        -- Exit velocity
        avg_exit_velocity,
        max_exit_velocity,
        p90_exit_velocity,
        stddev_exit_velocity,
        
        -- Launch angle
        avg_launch_angle,
        stddev_launch_angle,
        
        -- Distance
        avg_launch_distance,
        max_launch_distance,
        
        -- Quality counts
        barrels,
        hard_hits,
        
        -- Quality rates
        safe_divide(barrels, total_batted_balls) as barrel_rate,
        safe_divide(hard_hits, total_batted_balls) as hard_hit_rate,
        
        -- Trajectory counts
        fly_balls,
        line_drives,
        ground_balls,
        popups,
        
        -- Trajectory rates
        safe_divide(fly_balls, total_batted_balls) as fly_ball_rate,
        safe_divide(line_drives, total_batted_balls) as line_drive_rate,
        safe_divide(ground_balls, total_batted_balls) as ground_ball_rate,
        
        -- Speed
        avg_sprint_speed,
        
        -- Metadata
        last_updated

    from batter_batted_ball_aggregates

)

select * from batter_statcast_metrics
