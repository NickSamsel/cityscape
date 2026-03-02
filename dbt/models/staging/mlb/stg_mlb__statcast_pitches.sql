{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='play_id',
    partition_by={
      "field": "loaded_at",
      "data_type": "timestamp",
      "granularity": "day"
    },
    cluster_by=["game_id", "pitcher_id", "batter_id"],
    on_schema_change='sync_all_columns',
    tags=["staging", "mlb", "statcast"]
  )
-}}

-- Staging table for MLB Statcast pitch-level data
-- Contains pitch velocity, spin rate, and pitch location metrics

with source as (

    select * from {{ source('raw', 'mlb_statcast_pitches') }}
    {% if is_incremental() %}
    -- Look back 3 days to catch any late-arriving or corrected data
    where loaded_at > timestamp_sub(
      (select max(loaded_at) from {{ this }}),
      interval 3 day
    )
    {% endif %}

),

renamed as (

    select
        -- IDs
        play_id,
        cast(game_id as string) as game_id,
        at_bat_index,
        cast(pitcher_id as string) as pitcher_id,
        cast(batter_id as string) as batter_id,
        cast(catcher_id as string) as catcher_id,
        cast(umpire_id as string) as umpire_id,

        -- Pitch details
        pitch_number,
        pitch_type,
        pitch_type_description,

        -- Release metrics
        release_speed, -- mph
        release_spin_rate, -- rpm
        release_extension, -- feet
        release_pos_x, -- feet
        release_pos_y, -- feet
        release_pos_z, -- feet

        -- Plate location
        zone,
        plate_x, -- feet from center
        plate_z, -- feet from ground

        -- Count context
        strikes,
        balls,
        outs,

        -- Outcome
        pitch_result,
        pitch_result_description,

        -- Metadata
        loaded_at

    from source

)

select * from renamed
