{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='game_id',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "home_team_id", "away_team_id"],
    on_schema_change='sync_all_columns',
    tags=["int", "mlb"]
  )
-}}

with games as (
    select * from {{ ref('stg_mlb__games') }}
),

home_teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

away_teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

leagues as (
    select * from {{ ref('stg_mlb__leagues') }}
),

divisions as (
    select * from {{ ref('stg_mlb__divisions') }}
),

final as (
    select
        g.game_id,
        g.season,
        g.game_date,
        g.game_type,
        g.status,
        g.venue_id,
        
        -- Home team information
        g.home_team_id,
        home_t.team_name as home_team_name,
        home_t.team_abbr as home_team_abbr,
        home_t.league_id as home_league_id,
        home_lg.league_name as home_league_name,
        home_lg.league_abbr as home_league_abbr,
        home_t.division_id as home_division_id,
        home_div.division_name as home_division_name,
        home_div.division_abbr as home_division_abbr,
        g.home_score,
        
        -- Away team information
        g.away_team_id,
        away_t.team_name as away_team_name,
        away_t.team_abbr as away_team_abbr,
        away_t.league_id as away_league_id,
        away_lg.league_name as away_league_name,
        away_lg.league_abbr as away_league_abbr,
        away_t.division_id as away_division_id,
        away_div.division_name as away_division_name,
        away_div.division_abbr as away_division_abbr,
        g.away_score,
        
        -- Game outcome calculations
        {{ calculate_winning_team('g.home_team_id', 'g.away_team_id', 'g.home_score', 'g.away_score') }} as winning_team_id,
        {{ calculate_losing_team('g.home_team_id', 'g.away_team_id', 'g.home_score', 'g.away_score') }} as losing_team_id,
        {{ calculate_winner_type('g.home_score', 'g.away_score') }} as winner,
        
        abs(g.home_score - g.away_score) as score_differential,
        g.home_score + g.away_score as total_runs
        
    from games as g
    left join home_teams as home_t
        on g.home_team_id = home_t.team_id
        and g.season = home_t.season
    left join away_teams as away_t
        on g.away_team_id = away_t.team_id
        and g.season = away_t.season
    left join leagues as home_lg
        on home_t.league_id = home_lg.league_id
    left join leagues as away_lg
        on away_t.league_id = away_lg.league_id
    left join divisions as home_div
        on home_t.division_id = home_div.division_id
    left join divisions as away_div
        on away_t.division_id = away_div.division_id

    {% if is_incremental() %}
    where g.game_date >= date_sub(
        (select max(game_date) from {{ this }}),
        interval 3 day
    )
    {% endif %}
)

select * from final
