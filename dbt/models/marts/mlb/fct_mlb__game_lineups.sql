{{-
  config(
        materialized='view',
    tags=["mart", "mlb", "fact", "schedule"]
  )
-}}

-- Mart fact table for MLB starting lineups
-- Each row represents a player's slot in the starting batting order
-- Enriched with game context and player position details

with lineups as (

    select * from {{ ref('stg_mlb__game_lineups') }}

),

schedule as (

    select
        game_id,
        season,
        game_date,
        home_team_id,
        away_team_id,
        venue_name,
        status
    from {{ ref('stg_mlb__schedule') }}

),

players as (

    select
        player_id,
        primary_position_name,
        bat_side_code,
        pitch_hand_code
    from {{ ref('stg_mlb__players') }}

)

select
    l.game_id,
    s.season,
    s.game_date,
    l.team_side,
    case
        when l.team_side = 'home' then s.home_team_id
        else s.away_team_id
    end as team_id,
    l.player_id,
    l.full_name,
    l.position_abbreviation,
    l.batting_order,
    p.bat_side_code,
    p.pitch_hand_code,
    s.venue_name,
    s.status as game_status
from lineups as l
left join schedule as s
    on l.game_id = s.game_id
left join players as p
    on l.player_id = p.player_id
