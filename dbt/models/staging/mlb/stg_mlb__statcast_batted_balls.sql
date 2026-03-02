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
    cluster_by=["game_id", "batter_id", "pitcher_id"],
    on_schema_change='sync_all_columns',
    tags=["staging", "mlb", "statcast"]
  )
-}}

-- Staging table for MLB Statcast batted ball data
-- Contains exit velocity, launch angle, and other batted ball metrics

with source as (

    select * from {{ source('raw', 'mlb_statcast_batted_balls') }}
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
        cast(batter_id as string) as batter_id,
        cast(pitcher_id as string) as pitcher_id,

        -- Batted ball metrics
        launch_speed, -- mph (exit velocity)
        launch_angle, -- degrees
        launch_distance, -- feet (projected)
        hit_location,
        hit_trajectory,
        hit_result,

        -- Runner metrics
        sprint_speed, -- ft/sec

        -- Quality flags
        is_barrel,
        is_hard_hit, -- 95+ mph exit velo

        -- Metadata
        loaded_at

    from source

)

select * from renamed
