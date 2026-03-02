{{-
  config(
    materialized='incremental',
    unique_key='play_id',
    on_schema_change='sync_all_columns',
    tags=["intermediate", "mlb", "statcast"]
  )
-}}

-- Intermediate enriched pitch-level data
-- Joins pitch metrics with game, player, and team context

with pitches as (

    select * from {{ ref('stg_mlb__statcast_pitches') }}
    {% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}

),

games as (

    select * from {{ ref('stg_mlb__games') }}

),

pitchers as (

    select * from {{ ref('stg_mlb__players') }}

),

batters as (

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
        p.play_id,
        p.game_id,
        p.at_bat_index,
        p.pitch_number,

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

        -- Pitcher details
        p.pitcher_id,
        pitcher.full_name as pitcher_name,
        pitcher.primary_position_code as pitcher_position,
        pitcher.pitch_hand_code as pitcher_hand,
        pitcher.pitch_hand_description as pitcher_hand_desc,
        date_diff(g.game_date, pitcher.birth_date, year) as pitcher_age,
        date_diff(g.game_date, pitcher.mlb_debut_date, year) as pitcher_experience_years,

        -- Batter details
        p.batter_id,
        batter.full_name as batter_name,
        batter.primary_position_code as batter_position,
        batter.bat_side_code as batter_hand,
        batter.bat_side_description as batter_hand_desc,
        date_diff(g.game_date, batter.birth_date, year) as batter_age,
        date_diff(g.game_date, batter.mlb_debut_date, year) as batter_experience_years,

        -- Matchup context
        case
            when pitcher.pitch_hand_code = batter.bat_side_code then 'Same'
            when pitcher.pitch_hand_code is null or batter.bat_side_code is null then 'Unknown'
            else 'Opposite'
        end as pitcher_batter_handedness,

        -- Catcher and umpire
        p.catcher_id,
        p.umpire_id,
        
        -- Pitch characteristics
        p.pitch_type,
        p.pitch_type_description,
        p.release_speed,
        p.release_spin_rate,
        p.release_extension,
        p.release_pos_x,
        p.release_pos_y,
        p.release_pos_z,
        
        -- Location
        p.zone,
        case
            when p.zone between 1 and 9 then true
            else false
        end as in_strike_zone,
        p.plate_x,
        p.plate_z,
        
        -- Count context
        p.strikes,
        p.balls,
        p.outs,
        concat(cast(p.balls as string), '-', cast(p.strikes as string)) as count_description,
        
        -- Pitch outcome
        p.pitch_result,
        p.pitch_result_description,
        case
            when p.pitch_result = 'S' then 'Called Strike'
            when p.pitch_result = 'X' then 'In Play'
            when p.pitch_result = 'B' then 'Ball'
            when p.pitch_result = 'F' then 'Foul'
            when p.pitch_result = 'W' then 'Swinging Strike'
            else 'Other'
        end as pitch_result_category,
        
        -- Derived metrics
        case
            when p.release_speed >= 98 then 'Elite Velocity (98+)'
            when p.release_speed >= 95 then 'Above Average (95-97)'
            when p.release_speed >= 92 then 'Average (92-94)'
            when p.release_speed >= 88 then 'Below Average (88-91)'
            else 'Soft (< 88)'
        end as velocity_tier,
        
        case
            when p.release_spin_rate >= 2500 then 'High Spin (2500+)'
            when p.release_spin_rate >= 2200 then 'Average Spin (2200-2499)'
            else 'Low Spin (< 2200)'
        end as spin_tier,
        
        -- Metadata
        p.loaded_at

    from pitches as p
    left join games as g
        on p.game_id = g.game_id
    left join pitchers as pitcher
        on p.pitcher_id = pitcher.player_id
    left join batters as batter
        on p.batter_id = batter.player_id
    left join teams_home as th
        on g.home_team_id = th.team_id
        and g.season = th.season
    left join teams_away as ta
        on g.away_team_id = ta.team_id
        and g.season = ta.season

)

select * from enriched
