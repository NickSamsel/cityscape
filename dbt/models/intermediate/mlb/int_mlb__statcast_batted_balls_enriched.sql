{{-
  config(
    materialized='incremental',
    unique_key='play_id',
    on_schema_change='sync_all_columns',
    tags=["intermediate", "mlb", "statcast"]
  )
-}}

-- Intermediate enriched batted ball data
-- Joins batted ball metrics with game, player, and team context

with batted_balls as (

    select * from {{ ref('stg_mlb__statcast_batted_balls') }}
    {% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}

),

games as (

    select * from {{ ref('stg_mlb__games') }}

),

batters as (

    select * from {{ ref('stg_mlb__players') }}

),

pitchers as (

    select * from {{ ref('stg_mlb__players') }}

),

teams_home as (

    select * from {{ ref('stg_mlb__teams') }}

),

teams_away as (

    select * from {{ ref('stg_mlb__teams') }}

),

enriched as (

    select
        -- Primary keys
        bb.play_id,
        bb.game_id,
        bb.at_bat_index,

        -- Game context
        g.season,
        g.game_date,
        g.game_type,
        g.status as game_status,
        g.home_team_id,
        th.team_name as home_team_name,
        th.team_abbr as home_team_abbr,
        g.away_team_id,
        ta.team_name as away_team_name,
        ta.team_abbr as away_team_abbr,
        g.home_score,
        g.away_score,

        -- Batter details
        bb.batter_id,
        batter.full_name as batter_name,
        batter.primary_position_code as batter_position,
        batter.bat_side_code as batter_hand,
        batter.bat_side_description as batter_hand_desc,
        date_diff(g.game_date, batter.birth_date, year) as batter_age,
        date_diff(g.game_date, batter.mlb_debut_date, year) as batter_experience_years,

        -- Pitcher details
        bb.pitcher_id,
        pitcher.full_name as pitcher_name,
        pitcher.primary_position_code as pitcher_position,
        pitcher.pitch_hand_code as pitcher_hand,
        pitcher.pitch_hand_description as pitcher_hand_desc,
        date_diff(g.game_date, pitcher.birth_date, year) as pitcher_age,
        date_diff(g.game_date, pitcher.mlb_debut_date, year) as pitcher_experience_years,
        
        -- Matchup context
        case
            when pitcher.pitch_hand_code = batter.bat_side_code then 'Same'
            when pitcher.pitch_hand_code is null or batter.bat_side_code is null then 'Unknown'
            else 'Opposite'
        end as pitcher_batter_handedness,
        
        -- Batted ball metrics
        bb.launch_speed, -- exit velocity
        bb.launch_angle,
        bb.launch_distance,
        bb.hit_location,
        bb.hit_trajectory,
        bb.hit_result,
        bb.sprint_speed,
        bb.is_barrel,
        bb.is_hard_hit,
        
        -- Derived metrics
        case
            when bb.launch_speed >= 110 then 'Elite (110+)'
            when bb.launch_speed >= 100 then 'Great (100-109)'
            when bb.launch_speed >= 95 then 'Good (95-99)'
            when bb.launch_speed >= 90 then 'Average (90-94)'
            when bb.launch_speed >= 80 then 'Below Average (80-89)'
            else 'Weak (< 80)'
        end as exit_velo_tier,
        
        case
            when bb.launch_angle >= 50 then 'Pop Up (50+)'
            when bb.launch_angle >= 25 then 'Fly Ball (25-49)'
            when bb.launch_angle >= 10 then 'Line Drive (10-24)'
            when bb.launch_angle >= -10 then 'Ground Ball (-10 to 9)'
            else 'Topped (< -10)'
        end as trajectory_bucket,
        
        case
            when bb.is_barrel then 'Barrel'
            when bb.is_hard_hit then 'Hard Hit (Non-Barrel)'
            else 'Not Hard Hit'
        end as quality_contact_tier,
        
        case
            when bb.launch_distance >= 400 then '400+ ft'
            when bb.launch_distance >= 350 then '350-399 ft'
            when bb.launch_distance >= 300 then '300-349 ft'
            when bb.launch_distance >= 250 then '250-299 ft'
            else 'Under 250 ft'
        end as distance_bucket,
        
        -- Result flags
        case
            when bb.hit_result in ('Home Run', 'homeRun') then true
            else false
        end as is_home_run,
        
        case
            when bb.hit_result in ('Single', 'Double', 'Triple', 'Home Run', 'homeRun') then true
            else false
        end as is_hit,
        
        -- Metadata
        bb.loaded_at

    from batted_balls as bb
    left join games as g
        on bb.game_id = g.game_id
    left join batters as batter
        on bb.batter_id = batter.player_id
    left join pitchers as pitcher
        on bb.pitcher_id = pitcher.player_id
    left join teams_home as th
        on g.home_team_id = th.team_id
        and g.season = th.season
    left join teams_away as ta
        on g.away_team_id = ta.team_id
        and g.season = ta.season

)

select * from enriched
