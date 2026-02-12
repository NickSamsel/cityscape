{{-
  config(
    materialized='incremental',
    unique_key='player_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact"]
  )
-}}

-- Comprehensive player fact table integrating dimensions, career stats, and Statcast metrics
-- This mart provides a complete view of each player's profile and performance

with players as (

    select * from {{ ref('dim_mlb__players') }}

),

career_batting as (

    select * from {{ ref('int_mlb__career_batting_stats') }}

),

career_pitching as (

    select * from {{ ref('int_mlb__career_pitching_stats') }}

),

batter_statcast as (

    select * from {{ ref('int_mlb__batter_statcast_metrics') }}

),

pitcher_statcast as (

    select * from {{ ref('int_mlb__pitcher_statcast_metrics') }}

),

player_enriched as (

    select
        p.player_id,
        
        -- Player dimension attributes
        p.full_name,
        p.first_name,
        p.last_name,
        p.primary_number,
        p.birth_date,
        p.current_age,
        p.birth_city,
        p.birth_state_province,
        p.birth_country,
        p.height,
        p.weight,
        p.primary_position_code,
        p.primary_position_name,
        p.primary_position_abbr,
        p.bat_side_code,
        p.bat_side_description,
        p.pitch_hand_code,
        p.pitch_hand_description,
        p.mlb_debut_date,
        p.active,
        
        -- Calculate MLB experience (years since debut)
        date_diff(current_date(), p.mlb_debut_date, year) as years_experience,
        
        -- Career batting stats
        cb.career_games_batted,
        cb.career_at_bats,
        cb.career_runs,
        cb.career_hits,
        cb.career_singles,
        cb.career_doubles,
        cb.career_triples,
        cb.career_home_runs,
        cb.career_rbi,
        cb.career_stolen_bases,
        cb.career_walks,
        cb.career_strikeouts,
        cb.career_total_bases,
        cb.career_batting_avg,
        cb.career_slugging_pct,
        cb.career_obp,
        cb.career_ops,
        cb.career_hr_rate,
        cb.career_k_rate,
        cb.career_bb_rate,
        cb.last_game_date as last_batting_game_date,
        
        -- Career pitching stats
        cp.career_games_pitched,
        cp.career_pitches,
        cp.career_strikes,
        cp.career_innings_pitched,
        cp.career_hits_allowed,
        cp.career_runs_allowed,
        cp.career_earned_runs,
        cp.career_walks_allowed,
        cp.career_strikeouts as career_pitching_strikeouts,
        cp.career_home_runs_allowed,
        cp.career_era,
        cp.career_whip,
        cp.career_k_per_9,
        cp.career_bb_per_9,
        cp.career_k_bb_ratio,
        cp.career_strike_pct,
        cp.last_game_date as last_pitching_game_date,
        
        -- Batter Statcast metrics
        bs.total_batted_balls,
        bs.games_with_batted_balls,
        bs.avg_exit_velocity,
        bs.max_exit_velocity,
        bs.p90_exit_velocity,
        bs.avg_launch_angle,
        bs.avg_launch_distance,
        bs.max_launch_distance,
        bs.barrels,
        bs.barrel_rate,
        bs.hard_hits,
        bs.hard_hit_rate,
        bs.fly_ball_rate,
        bs.line_drive_rate,
        bs.ground_ball_rate,
        bs.avg_sprint_speed,
        
        -- Pitcher Statcast metrics
        ps.total_pitches as statcast_pitches,
        ps.games_pitched as statcast_games_pitched,
        ps.avg_release_speed,
        ps.max_release_speed,
        ps.avg_spin_rate,
        ps.max_spin_rate,
        ps.avg_release_extension,
        ps.zone_percentage,
        ps.primary_pitch_type,
        ps.primary_pitch_description,
        ps.primary_pitch_avg_speed,
        ps.primary_pitch_avg_spin,
        
        -- Derived player type flags
        case
            when cb.career_games_batted >= 10 then true
            else false
        end as is_batter,
        
        case
            when cp.career_games_pitched >= 5 then true
            else false
        end as is_pitcher,
        
        case
            when cb.career_games_batted >= 10 and cp.career_games_pitched >= 5 then true
            else false
        end as is_two_way_player,
        
        -- Last activity date
        greatest(
            coalesce(cb.last_game_date, date('1900-01-01')),
            coalesce(cp.last_game_date, date('1900-01-01'))
        ) as last_game_date,
        
        -- Current timestamp for record keeping
        current_timestamp() as dbt_updated_at

    from players as p
    left join career_batting as cb
        on p.player_id = cb.player_id
    left join career_pitching as cp
        on p.player_id = cp.player_id
    left join batter_statcast as bs
        on p.player_id = bs.batter_id
    left join pitcher_statcast as ps
        on p.player_id = ps.pitcher_id

)

select * from player_enriched
{% if is_incremental() %}
where dbt_updated_at > (select max(dbt_updated_at) from {{ this }})
{% endif %}
