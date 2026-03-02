{{
  config(
    materialized='table',
    tags=["intermediate", "mlb", "rosters"]
  )
}}

-- Enriched roster data with team and player context
-- Provides comprehensive team-player relationships for analysis

with rosters as (

    select * from {{ ref('stg_mlb__rosters') }}

),

teams as (

    select * from {{ ref('int_mlb__teams') }}

),

leagues as (

    select * from {{ ref('int_mlb__leagues') }}

),

divisions as (

    select * from {{ ref('int_mlb__divisions_enriched') }}

),

players as (

    select * from {{ ref('int_mlb__players') }}

),

enriched as (

    select
        -- Keys
        r.team_id,
        r.player_id,
        r.season,
        
        -- Team info
        t.team_name,
        t.team_abbr,
        l.league_id,
        l.league_name,
        l.league_abbr,
        d.division_id,
        d.division_name,
        d.division_abbr,
        
        -- Player info
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
        p.mlb_debut_date,
        p.active as player_active,
        
        -- Position info (from roster - can differ from player's primary position)
        r.position_code,
        r.position_name,
        r.position_abbr,
        
        -- Player's primary position (for comparison)
        p.primary_position_code,
        p.primary_position_name,
        p.primary_position_abbr,
        
        -- Batting/Pitching attributes
        p.bat_side_code,
        p.bat_side_description,
        p.pitch_hand_code,
        p.pitch_hand_description,
        
        -- Tenure calculations
        case
            when p.mlb_debut_date is not null 
            then r.season - extract(year from p.mlb_debut_date)
            else null
        end as seasons_since_debut,
        
        -- Position type flags
        case
            when r.position_code in ('P', '1') then 'Pitcher'
            when r.position_code in ('C', '2') then 'Catcher'
            when r.position_code in ('1B', '3') then 'First Base'
            when r.position_code in ('2B', '4') then 'Second Base'
            when r.position_code in ('3B', '5') then 'Third Base'
            when r.position_code in ('SS', '6') then 'Shortstop'
            when r.position_code in ('LF', '7') then 'Left Field'
            when r.position_code in ('CF', '8') then 'Center Field'
            when r.position_code in ('RF', '9') then 'Right Field'
            when r.position_code in ('DH', 'D') then 'Designated Hitter'
            when r.position_code in ('OF', 'O') then 'Outfield'
            else 'Other'
        end as position_group,
        
        case when r.position_code in ('P', '1') then true else false end as is_pitcher,
        case when r.position_code not in ('P', '1') then true else false end as is_position_player,
        
        r.loaded_at

    from rosters as r
    left join teams as t
        on r.team_id = t.team_id
        and r.season = t.season
    left join players as p
        on r.player_id = p.player_id
    left join leagues as l
        on t.league_id = l.league_id
    left join divisions as d
        on t.division_id = d.division_id

)

select * from enriched
