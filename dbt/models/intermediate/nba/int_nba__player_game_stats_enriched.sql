{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id'],
    on_schema_change='sync_all_columns',
    tags=["intermediate", "nba", "player_stats"]
  )
-}}

-- Enrich player game stats with player and team information

with player_stats as (
  select *
  from {{ ref('stg_nba__player_game_stats') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = game_id
      and existing.player_id = player_id
  )
  {% endif %}
),

teams as (
  select
    team_id,
    team_name,
    team_abbr
  from {{ ref('stg_nba__teams') }}
),

games as (
  select
    game_id,
    season,
    season_type,
    game_date
  from {{ ref('stg_nba__games') }}
),

enriched as (
  select
    ps.game_id,
    g.season,
    g.season_type,
    g.game_date,
    ps.player_id,
    ps.player_name,
    ps.team_id,
    t.team_name,
    t.team_abbr,
    ps.starter,
    ps.minutes,
    ps.field_goals_made,
    ps.field_goals_attempted,
    ps.field_goal_pct,
    ps.three_pointers_made,
    ps.three_pointers_attempted,
    ps.three_point_pct,
    ps.free_throws_made,
    ps.free_throws_attempted,
    ps.free_throw_pct,
    ps.offensive_rebounds,
    ps.defensive_rebounds,
    ps.total_rebounds,
    ps.assists,
    ps.steals,
    ps.blocks,
    ps.turnovers,
    ps.personal_fouls,
    ps.points,
    ps.plus_minus
  from player_stats ps
  left join teams t on ps.team_id = t.team_id
  left join games g on ps.game_id = g.game_id
)

select * from enriched
