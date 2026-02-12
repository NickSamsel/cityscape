{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "team_stats", "statcast"]
  )
-}}

-- Mart fact table for team-level Statcast metrics by season
-- Granular Statcast aggregations from pitch-level and batted-ball-level data
-- Provides deeper Statcast detail than the season stats table
-- Each row represents a team's Statcast profile for a season

with batting_stats as (

    select * from {{ ref('fct_mlb__player_batting_stats') }}
    where season is not null
    {% if is_incremental() %}
    and season not in (select distinct season from {{ this }})
    {% endif %}

),

pitching_stats as (

    select * from {{ ref('fct_mlb__player_pitching_stats') }}
    where season is not null
    {% if is_incremental() %}
    and season not in (select distinct season from {{ this }})
    {% endif %}

),

batted_balls as (

    select * from {{ ref('fct_mlb__statcast_batted_balls') }}
    where season is not null

),

pitches as (

    select * from {{ ref('fct_mlb__statcast_pitches') }}
    where season is not null

),

-- Map batters to their team using batting stats (most games played = primary team)
batter_teams as (

    select
        player_id,
        season,
        team_id,
        team_name,
        team_abbr,
        league_id,
        league_name,
        division_id,
        division_name
    from (
        select
            player_id,
            season,
            team_id,
            team_name,
            team_abbr,
            league_id,
            league_name,
            division_id,
            division_name,
            row_number() over (partition by player_id, season order by count(*) desc) as rn
        from batting_stats
        group by 1, 2, 3, 4, 5, 6, 7, 8, 9
    )
    where rn = 1

),

-- Map pitchers to their team using pitching stats
pitcher_teams as (

    select
        player_id,
        season,
        team_id,
        team_name,
        team_abbr,
        league_id,
        league_name,
        division_id,
        division_name
    from (
        select
            player_id,
            season,
            team_id,
            team_name,
            team_abbr,
            league_id,
            league_name,
            division_id,
            division_name,
            row_number() over (partition by player_id, season order by count(*) desc) as rn
        from pitching_stats
        group by 1, 2, 3, 4, 5, 6, 7, 8, 9
    )
    where rn = 1

),

-- Team offensive Statcast from batted ball data
team_offense_statcast as (

    select
        bt.team_id,
        bt.team_name,
        bt.team_abbr,
        bt.league_id,
        bt.league_name,
        bt.division_id,
        bt.division_name,
        bb.season,

        -- Volume
        count(*) as total_batted_balls,
        count(distinct bb.batter_id) as batters_with_statcast,
        count(distinct bb.game_id) as games_with_batted_ball_data,

        -- Exit velocity
        avg(bb.launch_speed) as avg_exit_velocity,
        max(bb.launch_speed) as max_exit_velocity,
        approx_quantiles(bb.launch_speed, 100)[offset(90)] as p90_exit_velocity,
        stddev(bb.launch_speed) as stddev_exit_velocity,

        -- Launch angle
        avg(bb.launch_angle) as avg_launch_angle,
        stddev(bb.launch_angle) as stddev_launch_angle,

        -- Distance
        avg(bb.launch_distance) as avg_launch_distance,
        max(bb.launch_distance) as max_launch_distance,

        -- Quality of contact
        countif(bb.is_barrel) as total_barrels,
        countif(bb.is_hard_hit) as total_hard_hits,
        safe_divide(countif(bb.is_barrel), count(*)) as barrel_rate,
        safe_divide(countif(bb.is_hard_hit), count(*)) as hard_hit_rate,

        -- Batted ball distribution
        countif(bb.trajectory_bucket = 'Fly Ball (25-49)') as fly_balls,
        countif(bb.trajectory_bucket = 'Line Drive (10-24)') as line_drives,
        countif(bb.trajectory_bucket like 'Ground Ball%') as ground_balls,
        countif(bb.trajectory_bucket like 'Pop Up%') as popups,
        safe_divide(countif(bb.trajectory_bucket = 'Fly Ball (25-49)'), count(*)) as fly_ball_rate,
        safe_divide(countif(bb.trajectory_bucket = 'Line Drive (10-24)'), count(*)) as line_drive_rate,
        safe_divide(countif(bb.trajectory_bucket like 'Ground Ball%'), count(*)) as ground_ball_rate,

        -- Results on contact
        countif(bb.is_home_run) as home_runs_on_contact,
        countif(bb.is_hit) as hits_on_contact,
        safe_divide(countif(bb.is_hit), count(*)) as babip_statcast,

        -- Sprint speed
        avg(bb.sprint_speed) as avg_sprint_speed,
        max(bb.sprint_speed) as max_sprint_speed

    from batted_balls as bb
    inner join batter_teams as bt
        on bb.batter_id = bt.player_id
        and bb.season = bt.season
    group by 1, 2, 3, 4, 5, 6, 7, 8

),

-- Team pitching staff Statcast from pitch data
team_pitching_statcast as (

    select
        pt.team_id,
        p.season,

        -- Volume
        count(*) as total_pitches_tracked,
        count(distinct p.pitcher_id) as pitchers_with_statcast,
        count(distinct p.game_id) as games_with_pitch_data,

        -- Velocity
        avg(p.release_speed) as staff_avg_velocity,
        max(p.release_speed) as staff_max_velocity,
        approx_quantiles(p.release_speed, 100)[offset(90)] as staff_p90_velocity,
        stddev(p.release_speed) as staff_stddev_velocity,

        -- Spin rate
        avg(p.release_spin_rate) as staff_avg_spin_rate,
        max(p.release_spin_rate) as staff_max_spin_rate,
        approx_quantiles(p.release_spin_rate, 100)[offset(90)] as staff_p90_spin_rate,

        -- Zone control
        countif(p.zone between 1 and 9) as pitches_in_zone,
        safe_divide(countif(p.zone between 1 and 9), count(*)) as staff_zone_rate,

        -- Pitch results
        countif(p.pitch_result_category = 'Called Strike') as called_strikes,
        countif(p.pitch_result_category = 'Swinging Strike') as swinging_strikes,
        countif(p.pitch_result_category = 'Ball') as balls_thrown,
        countif(p.pitch_result_category = 'Foul') as fouls,
        countif(p.pitch_result_category = 'In Play') as in_play,

        safe_divide(
            countif(p.pitch_result_category in ('Called Strike', 'Swinging Strike', 'Foul')),
            count(*)
        ) as staff_strike_rate,
        safe_divide(countif(p.pitch_result_category = 'Swinging Strike'), count(*)) as staff_whiff_rate,

        -- Velocity tier distribution
        safe_divide(countif(p.velocity_tier = 'Elite Velocity (98+)'), count(*)) as elite_velocity_pct,
        safe_divide(countif(p.velocity_tier = 'Above Average (95-97)'), count(*)) as above_avg_velocity_pct,

        -- Pitch type diversity (count of distinct pitch types used)
        count(distinct p.pitch_type) as unique_pitch_types

    from pitches as p
    inner join pitcher_teams as pt
        on p.pitcher_id = pt.player_id
        and p.season = pt.season
    group by 1, 2

),

final as (

    select
        -- Team identity
        o.team_id,
        o.team_name,
        o.team_abbr,
        o.league_id,
        o.league_name,
        o.division_id,
        o.division_name,
        o.season,

        -- Offensive Statcast
        o.total_batted_balls,
        o.batters_with_statcast,
        o.games_with_batted_ball_data,
        round(o.avg_exit_velocity, 1) as avg_exit_velocity,
        round(o.max_exit_velocity, 1) as max_exit_velocity,
        round(o.p90_exit_velocity, 1) as p90_exit_velocity,
        round(o.avg_launch_angle, 1) as avg_launch_angle,
        round(o.avg_launch_distance, 0) as avg_launch_distance,
        round(o.max_launch_distance, 0) as max_launch_distance,
        o.total_barrels,
        o.total_hard_hits,
        round(o.barrel_rate, 3) as barrel_rate,
        round(o.hard_hit_rate, 3) as hard_hit_rate,
        o.fly_balls,
        o.line_drives,
        o.ground_balls,
        o.popups,
        round(o.fly_ball_rate, 3) as fly_ball_rate,
        round(o.line_drive_rate, 3) as line_drive_rate,
        round(o.ground_ball_rate, 3) as ground_ball_rate,
        round(o.babip_statcast, 3) as babip_statcast,
        round(o.avg_sprint_speed, 1) as avg_sprint_speed,
        round(o.max_sprint_speed, 1) as max_sprint_speed,

        -- Pitching staff Statcast
        tp.total_pitches_tracked,
        tp.pitchers_with_statcast,
        tp.games_with_pitch_data,
        round(tp.staff_avg_velocity, 1) as staff_avg_velocity,
        round(tp.staff_max_velocity, 1) as staff_max_velocity,
        round(tp.staff_p90_velocity, 1) as staff_p90_velocity,
        round(tp.staff_avg_spin_rate, 0) as staff_avg_spin_rate,
        round(tp.staff_max_spin_rate, 0) as staff_max_spin_rate,
        round(tp.staff_zone_rate, 3) as staff_zone_rate,
        round(tp.staff_strike_rate, 3) as staff_strike_rate,
        round(tp.staff_whiff_rate, 3) as staff_whiff_rate,
        round(tp.elite_velocity_pct, 3) as elite_velocity_pct,
        round(tp.above_avg_velocity_pct, 3) as above_avg_velocity_pct,
        tp.unique_pitch_types as staff_unique_pitch_types,

        -- Metadata
        current_timestamp() as loaded_at

    from team_offense_statcast as o
    left join team_pitching_statcast as tp
        on o.team_id = tp.team_id
        and o.season = tp.season

)

select * from final
