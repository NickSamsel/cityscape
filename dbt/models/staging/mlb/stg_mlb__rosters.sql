{{
  config(
    materialized='view',
    tags=["staging", "mlb", "rosters"]
  )
}}

-- Staging model for MLB team rosters (team-player mappings)
-- This provides a clean view of which players are on which teams for each season

with source as (

    select * from {{ source('raw', 'mlb_rosters') }}

),

renamed as (

    select
        cast(team_id as int64) as team_id,
        cast(player_id as int64) as player_id,
        season,
        player_name,
        position_code,
        position_name,
        position_abbr,
        loaded_at

    from source

)

select * from renamed
