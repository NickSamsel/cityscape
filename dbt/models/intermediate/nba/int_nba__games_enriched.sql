{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["intermediate", "nba", "games"]
  )
-}}

-- Enrich games with team information

games as (
  select *
  from {{ ref('stg_nba__games') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = stg_nba__games.game_id
  )
  {% endif %}
),

teams as (
  select
    team_id,
    team_name,
    team_abbr,
    team_city,
    conference_id,
    division_id
  from {{ ref('stg_nba__teams') }}
),

enriched as (
  select
    g.game_id,
    g.season,
    g.season_type,
    g.game_date,
    g.status,
    g.home_team_id,
    ht.team_name as home_team_name,
    ht.team_abbr as home_team_abbr,
    ht.team_city as home_team_city,
    ht.conference_id as home_conference_id,
    ht.division_id as home_division_id,
    g.away_team_id,
    at.team_name as away_team_name,
    at.team_abbr as away_team_abbr,
    at.team_city as away_team_city,
    at.conference_id as away_conference_id,
    at.division_id as away_division_id,
    g.home_score,
    g.away_score,
    {{ calculate_winning_team('g.home_team_id', 'g.away_team_id', 'g.home_score', 'g.away_score') }} as winning_team_id,
    {{ calculate_losing_team('g.home_team_id', 'g.away_team_id', 'g.home_score', 'g.away_score') }} as losing_team_id,
    abs(g.home_score - g.away_score) as score_differential,
    g.arena,
    g.attendance
  from games g
  left join teams ht on g.home_team_id = ht.team_id
  left join teams at on g.away_team_id = at.team_id
)

select * from enriched
