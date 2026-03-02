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
    tags=["int", "mlb", "schedule"]
  )
-}}

with schedule as (
    select * from {{ ref('stg_mlb__schedule') }}
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

home_players as (
    select * from {{ ref('stg_mlb__players') }}
),

away_players as (
    select * from {{ ref('stg_mlb__players') }}
),

final as (
    select
        s.game_id,
        s.season,
        s.game_date,
        s.game_datetime,
        s.game_type,
        s.status,
        s.day_night,

        -- Venue
        s.venue_id,
        s.venue_name,

        -- Home team context
        s.home_team_id,
        home_t.team_name as home_team_name,
        home_t.team_abbr as home_team_abbr,
        home_t.league_id as home_league_id,
        home_lg.league_name as home_league_name,
        home_t.division_id as home_division_id,
        home_div.division_name as home_division_name,

        -- Away team context
        s.away_team_id,
        away_t.team_name as away_team_name,
        away_t.team_abbr as away_team_abbr,
        away_t.league_id as away_league_id,
        away_lg.league_name as away_league_name,
        away_t.division_id as away_division_id,
        away_div.division_name as away_division_name,

        -- Home probable pitcher
        s.home_probable_pitcher_id,
        s.home_probable_pitcher_name,
        home_p.primary_position_abbr as home_probable_pitcher_position,
        home_p.pitch_hand_code as home_probable_pitcher_throws,

        -- Away probable pitcher
        s.away_probable_pitcher_id,
        s.away_probable_pitcher_name,
        away_p.primary_position_abbr as away_probable_pitcher_position,
        away_p.pitch_hand_code as away_probable_pitcher_throws,

        -- Matchup flags
        case
            when s.home_probable_pitcher_id is not null
             and s.away_probable_pitcher_id is not null
            then true
            else false
        end as has_probable_pitchers,

        case
            when home_t.league_id != away_t.league_id then true
            else false
        end as is_interleague,

        -- Schedule metadata
        s.scheduled_innings,
        s.series_description

    from schedule as s
    join home_teams as home_t
        on s.home_team_id = home_t.team_id
        and s.season = home_t.season
    join away_teams as away_t
        on s.away_team_id = away_t.team_id
        and s.season = away_t.season
    join leagues as home_lg
        on home_t.league_id = home_lg.league_id
    join leagues as away_lg
        on away_t.league_id = away_lg.league_id
    join divisions as home_div
        on home_t.division_id = home_div.division_id
    join divisions as away_div
        on away_t.division_id = away_div.division_id
    left join home_players as home_p
        on s.home_probable_pitcher_id = home_p.player_id
    left join away_players as away_p
        on s.away_probable_pitcher_id = away_p.player_id

    {% if is_incremental() %}
    where not exists (
        select 1
        from {{ this }} as existing
        where existing.game_id = s.game_id
    )
    {% endif %}
)

select * from final
