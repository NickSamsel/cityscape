{{ config(
    tags=["int", "mlb"],
    materialized='table'
) }}

with games as (
    select * from {{ ref('stg_mlb__games') }}
),

home_teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

away_teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

final as (
    select
        g.game_id,
        g.season,
        g.game_date,
        g.game_type,
        g.status,
        
        -- Home team information
        g.home_team_id,
        home_t.team_name as home_team_name,
        home_t.team_abbr as home_team_abbr,
        home_t.league_id as home_league_id,
        home_t.division_id as home_division_id,
        g.home_score,
        
        -- Away team information
        g.away_team_id,
        away_t.team_name as away_team_name,
        away_t.team_abbr as away_team_abbr,
        away_t.league_id as away_league_id,
        away_t.division_id as away_division_id,
        g.away_score,
        
        -- Game outcome calculations
        case
            when g.home_score > g.away_score then g.home_team_id
            when g.away_score > g.home_score then g.away_team_id
            else null
        end as winning_team_id,
        
        case
            when g.home_score > g.away_score then g.away_team_id
            when g.away_score > g.home_score then g.home_team_id
            else null
        end as losing_team_id,
        
        case
            when g.home_score > g.away_score then 'home'
            when g.away_score > g.home_score then 'away'
            else 'tie'
        end as winner,
        
        abs(g.home_score - g.away_score) as score_differential,
        g.home_score + g.away_score as total_runs
        
    from games as g
    left join home_teams as home_t
        on g.home_team_id = home_t.team_id
        and g.season = home_t.season
    left join away_teams as away_t
        on g.away_team_id = away_t.team_id
        and g.season = away_t.season
)

select * from final
