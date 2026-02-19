{{
  config(
    materialized='table',
    tags=["mart", "mlb", "player_team"]
  )
}}

-- Player-Team-Season assignments combining rosters with performance data
-- This provides a complete view of player affiliations with both official roster info
-- and actual game performance stats (handles mid-season trades)

with rosters as (

    select * from {{ ref('int_mlb__rosters_enriched') }}

),

batting_season_stats as (

    -- Aggregate batting stats per player-team-season
    select
        bs.player_id,
        bs.team_id,
        g.season,
        count(distinct bs.game_id) as games_batted,
        sum(bs.at_bats) as at_bats,
        sum(bs.hits) as hits,
        sum(bs.home_runs) as home_runs,
        sum(bs.rbi) as rbi,
        safe_divide(sum(bs.hits), sum(bs.at_bats)) as batting_avg
    from {{ ref('stg_mlb__player_batting_stats') }} as bs
    inner join {{ ref('stg_mlb__games') }} as g
        on bs.game_id = g.game_id
    group by 1, 2, 3

),

pitching_season_stats as (

    -- Aggregate pitching stats per player-team-season
    select
        ps.player_id,
        ps.team_id,
        g.season,
        count(distinct ps.game_id) as games_pitched,
        sum(ps.innings_pitched_decimal) as innings_pitched,
        sum(ps.strikeouts) as strikeouts,
        safe_divide(sum(ps.earned_runs), sum(ps.innings_pitched_decimal)) * 9 as era
    from {{ ref('int_mlb__player_pitching_stats_enriched') }} as ps
    inner join {{ ref('stg_mlb__games') }} as g
        on ps.game_id = g.game_id
    group by 1, 2, 3

),

combined as (

    select
        -- Keys
        r.player_id,
        r.team_id,
        r.season,
        
        -- From roster (official team assignment)
        r.team_name,
        r.team_abbr,
        r.league_name,
        r.division_name,
        r.full_name,
        r.position_code as roster_position_code,
        r.position_name as roster_position_name,
        r.position_group,
        r.is_pitcher as roster_is_pitcher,
        r.is_position_player as roster_is_position_player,
        
        -- From player dimension
        r.birth_date,
        r.current_age,
        r.mlb_debut_date,
        r.seasons_since_debut,
        r.bat_side_code,
        r.pitch_hand_code,
        
        -- From actual game performance
        coalesce(bs.games_batted, 0) as games_batted,
        coalesce(bs.at_bats, 0) as at_bats,
        coalesce(bs.hits, 0) as hits,
        coalesce(bs.home_runs, 0) as home_runs,
        coalesce(bs.rbi, 0) as rbi,
        bs.batting_avg,
        
        coalesce(ps.games_pitched, 0) as games_pitched,
        ps.innings_pitched,
        ps.strikeouts as pitching_strikeouts,
        ps.era,
        
        -- Derived flags
        case when bs.games_batted >= 10 then true else false end as has_significant_batting,
        case when ps.games_pitched >= 5 then true else false end as has_significant_pitching,
        case 
            when bs.games_batted >= 10 and ps.games_pitched >= 5 then true 
            else false 
        end as is_two_way_player_actual,
        
        -- Roster status flags
        case 
            when bs.games_batted > 0 or ps.games_pitched > 0 then true 
            else false 
        end as appeared_in_games,
        
        case
            when (bs.games_batted > 0 or ps.games_pitched > 0) and r.player_id is not null then 'Active - On Roster'
            when (bs.games_batted > 0 or ps.games_pitched > 0) and r.player_id is null then 'Active - Not on Current Roster (Traded/Released)'
            when r.player_id is not null then 'On Roster - No Games Played'
            else 'Unknown'
        end as player_status,
        
        r.loaded_at as roster_loaded_at

    from rosters as r
    left join batting_season_stats as bs
        on r.player_id = bs.player_id
        and r.team_id = bs.team_id
        and r.season = bs.season
    left join pitching_season_stats as ps
        on r.player_id = ps.player_id
        and r.team_id = ps.team_id
        and r.season = ps.season

),

-- Add rank for players who changed teams mid-season
with_team_rank as (

    select
        *,
        row_number() over (
            partition by player_id, season
            order by (games_batted + games_pitched) desc
        ) as team_rank,
        
        count(*) over (partition by player_id, season) as teams_played_for

    from combined

)

select * from with_team_rank
