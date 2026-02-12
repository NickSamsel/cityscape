{{-
  config(
    materialized='incremental',
    unique_key=['player_id', 'player_type', 'season', 'zone'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "statcast", "pitch_tracking"]
  )
-}}

-- Mart fact table for pitch zone outcome aggregations
-- Pre-aggregated data for pitch tracking charts
-- Provides counts and rates by zone for both pitchers and batters

with pitches as (

    select * from {{ ref('fct_mlb__statcast_pitches') }}
    {% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}

),

-- Aggregate pitches by pitcher and zone
pitcher_zone_outcomes as (

    select
        pitcher_id as player_id,
        'pitcher' as player_type,
        season,
        zone,
        in_strike_zone,

        -- Total pitches by zone
        count(*) as total_pitches,

        -- Pitch outcomes
        countif(pitch_result = 'S') as called_strikes,
        countif(pitch_result = 'W') as swinging_strikes,
        countif(pitch_result = 'B') as balls,
        countif(pitch_result = 'F') as fouls,
        countif(pitch_result = 'X') as in_play,

        -- Pitch result categories for visualization
        countif(pitch_result_category = 'Called Strike') as called_strike_count,
        countif(pitch_result_category = 'Swinging Strike') as swinging_strike_count,
        countif(pitch_result_category = 'Ball') as ball_count,
        countif(pitch_result_category = 'Foul') as foul_count,
        countif(pitch_result_category = 'In Play') as in_play_count,

        -- Success metrics for pitchers
        countif(pitch_result in ('S', 'W', 'F')) as strikes_total,

        -- Location metrics
        avg(plate_x) as avg_plate_x,
        avg(plate_z) as avg_plate_z,

        -- Velocity and spin
        avg(release_speed) as avg_velocity,
        avg(release_spin_rate) as avg_spin_rate,

        -- Most common pitch type in this zone
        approx_top_count(pitch_type, 1)[offset(0)].value as primary_pitch_type,
        approx_top_count(pitch_type_description, 1)[offset(0)].value as primary_pitch_description

    from pitches
    where pitcher_id is not null
        and zone is not null
        and season is not null
    group by 1, 2, 3, 4, 5

),

-- Aggregate pitches by batter and zone
batter_zone_outcomes as (

    select
        batter_id as player_id,
        'batter' as player_type,
        season,
        zone,
        in_strike_zone,

        -- Total pitches by zone
        count(*) as total_pitches,

        -- Pitch outcomes
        countif(pitch_result = 'S') as called_strikes,
        countif(pitch_result = 'W') as swinging_strikes,
        countif(pitch_result = 'B') as balls,
        countif(pitch_result = 'F') as fouls,
        countif(pitch_result = 'X') as in_play,

        -- Pitch result categories for visualization
        countif(pitch_result_category = 'Called Strike') as called_strike_count,
        countif(pitch_result_category = 'Swinging Strike') as swinging_strike_count,
        countif(pitch_result_category = 'Ball') as ball_count,
        countif(pitch_result_category = 'Foul') as foul_count,
        countif(pitch_result_category = 'In Play') as in_play_count,

        -- Success metrics for batters (opposite of pitchers)
        countif(pitch_result in ('B', 'X')) as favorable_outcomes,

        -- Location metrics
        avg(plate_x) as avg_plate_x,
        avg(plate_z) as avg_plate_z,

        -- Velocity and spin faced
        avg(release_speed) as avg_velocity_faced,
        avg(release_spin_rate) as avg_spin_rate_faced,

        -- Most common pitch type faced in this zone
        approx_top_count(pitch_type, 1)[offset(0)].value as primary_pitch_type_faced,
        approx_top_count(pitch_type_description, 1)[offset(0)].value as primary_pitch_description_faced

    from pitches
    where batter_id is not null
        and zone is not null
        and season is not null
    group by 1, 2, 3, 4, 5

),

-- Combine pitcher and batter aggregations
combined as (

    select
        player_id,
        player_type,
        season,
        zone,
        in_strike_zone,
        total_pitches,
        called_strikes,
        swinging_strikes,
        balls,
        fouls,
        in_play,
        called_strike_count,
        swinging_strike_count,
        ball_count,
        foul_count,
        in_play_count,
        strikes_total as success_count,
        avg_plate_x,
        avg_plate_z,
        avg_velocity,
        avg_spin_rate,
        primary_pitch_type,
        primary_pitch_description

    from pitcher_zone_outcomes

    union all

    select
        player_id,
        player_type,
        season,
        zone,
        in_strike_zone,
        total_pitches,
        called_strikes,
        swinging_strikes,
        balls,
        fouls,
        in_play,
        called_strike_count,
        swinging_strike_count,
        ball_count,
        foul_count,
        in_play_count,
        favorable_outcomes as success_count,
        avg_plate_x,
        avg_plate_z,
        avg_velocity_faced as avg_velocity,
        avg_spin_rate_faced as avg_spin_rate,
        primary_pitch_type_faced as primary_pitch_type,
        primary_pitch_description_faced as primary_pitch_description

    from batter_zone_outcomes

),

-- Calculate rates and percentages
final as (

    select
        player_id,
        player_type,
        season,
        zone,
        in_strike_zone,

        -- Counts
        total_pitches,
        called_strikes,
        swinging_strikes,
        balls,
        fouls,
        in_play,
        success_count,

        -- Rates (for color coding in visualization)
        safe_divide(called_strikes, total_pitches) * 100 as called_strike_rate,
        safe_divide(swinging_strikes, total_pitches) * 100 as swinging_strike_rate,
        safe_divide(balls, total_pitches) * 100 as ball_rate,
        safe_divide(fouls, total_pitches) * 100 as foul_rate,
        safe_divide(in_play, total_pitches) * 100 as in_play_rate,
        safe_divide(success_count, total_pitches) * 100 as success_rate,

        -- Total strike rate (called + swinging + foul)
        safe_divide(called_strikes + swinging_strikes + fouls, total_pitches) * 100 as strike_rate,

        -- Location
        avg_plate_x,
        avg_plate_z,

        -- Pitch characteristics
        avg_velocity,
        avg_spin_rate,
        primary_pitch_type,
        primary_pitch_description,

        -- Metadata
        current_timestamp() as loaded_at

    from combined

)

select * from final
