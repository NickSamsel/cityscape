{{-
  config(
    materialized='incremental',
    unique_key='play_id',
    on_schema_change='sync_all_columns',
    tags=["staging", "mlb", "statcast"]
  )
-}}

-- Staging table for MLB Statcast batted ball data
-- Contains exit velocity, launch angle, and other batted ball metrics

with source as (

    select * from {{ source('raw', 'mlb_statcast_batted_balls') }}
    {% if is_incremental() %}
    where loaded_at > (select max(loaded_at) from {{ this }})
    {% endif %}

),

renamed as (

    select
        -- IDs
        play_id,
        cast(game_id as int64) as game_id,
        at_bat_index,
        cast(batter_id as int64) as batter_id,
        cast(pitcher_id as int64) as pitcher_id,
        
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
