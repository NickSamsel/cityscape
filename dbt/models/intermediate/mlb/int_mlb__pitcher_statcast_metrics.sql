{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb", "statcast"]
  )
-}}

-- Aggregate pitch metrics by pitcher
-- Calculates average velocity, spin rate, and pitch type distribution

with pitches as (

    select * from {{ ref('stg_mlb__statcast_pitches') }}

),

pitcher_pitch_aggregates as (

    select
        cast(pitcher_id as string) as pitcher_id,
        
        -- Overall pitch counts
        count(*) as total_pitches,
        count(distinct game_id) as games_pitched,
        
        -- Release velocity metrics
        avg(release_speed) as avg_release_speed,
        max(release_speed) as max_release_speed,
        min(release_speed) as min_release_speed,
        stddev(release_speed) as stddev_release_speed,
        
        -- Spin rate metrics
        avg(release_spin_rate) as avg_spin_rate,
        max(release_spin_rate) as max_spin_rate,
        
        -- Extension metrics
        avg(release_extension) as avg_release_extension,
        
        -- Zone control
        countif(zone between 1 and 9) as pitches_in_zone,
        countif(zone > 9 or zone is null) as pitches_out_zone,
        
        -- Pitch results
        countif(pitch_result = 'S') as called_strikes,
        countif(pitch_result = 'X') as balls_in_play,
        countif(pitch_result = 'B') as balls,
        
        -- Last updated
        max(loaded_at) as last_updated

    from pitches
    where release_speed is not null
    group by pitcher_id

),

pitcher_pitch_types as (

    select
        cast(pitcher_id as string) as pitcher_id,
        pitch_type,
        pitch_type_description,
        count(*) as pitch_count,
        avg(release_speed) as avg_speed,
        avg(release_spin_rate) as avg_spin
        
    from pitches
    where pitch_type is not null
    group by pitcher_id, pitch_type, pitch_type_description

),

-- Get primary pitch type (most frequent)
pitcher_primary_pitch as (

    select
        pitcher_id,
        array_agg(
            struct(pitch_type, pitch_type_description, pitch_count, avg_speed, avg_spin)
            order by pitch_count desc
            limit 1
        )[safe_offset(0)] as primary_pitch

    from pitcher_pitch_types
    group by pitcher_id

)

select
    agg.pitcher_id,
    
    -- Overall metrics
    agg.total_pitches,
    agg.games_pitched,
    
    -- Velocity
    agg.avg_release_speed,
    agg.max_release_speed,
    agg.min_release_speed,
    agg.stddev_release_speed,
    
    -- Spin
    agg.avg_spin_rate,
    agg.max_spin_rate,
    
    -- Extension
    agg.avg_release_extension,
    
    -- Zone control
    agg.pitches_in_zone,
    agg.pitches_out_zone,
    safe_divide(agg.pitches_in_zone, agg.total_pitches) as zone_percentage,
    
    -- Results
    agg.called_strikes,
    agg.balls_in_play,
    agg.balls,
    
    -- Primary pitch
    pp.primary_pitch.pitch_type as primary_pitch_type,
    pp.primary_pitch.pitch_type_description as primary_pitch_description,
    pp.primary_pitch.pitch_count as primary_pitch_count,
    pp.primary_pitch.avg_speed as primary_pitch_avg_speed,
    pp.primary_pitch.avg_spin as primary_pitch_avg_spin,
    
    -- Metadata
    agg.last_updated

from pitcher_pitch_aggregates as agg
left join pitcher_primary_pitch as pp
    on agg.pitcher_id = pp.pitcher_id
