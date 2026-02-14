{{-
  config(
    materialized='table',
    tags=["int", "nba", "shot_data"]
  )
-}}

-- Enriched shot chart data with game and team context
-- Similar to MLB Statcast, provides individual shot-level analytics

with shots as (
  select
    game_id,
    game_event_id,
    player_id,
    player_name,
    team_id,
    team_name,
    period,
    minutes_remaining,
    seconds_remaining,
    event_type,
    action_type,
    shot_type,
    shot_zone_basic,
    shot_zone_area,
    shot_zone_range,
    shot_distance,
    loc_x,
    loc_y,
    shot_attempted_flag,
    shot_made_flag,
    game_date,
    htm,
    vtm
  from {{ ref('stg_nba__shot_chart') }}
),

games as (
  select
    game_id,
    season,
    season_type,
    game_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    winning_team_id,
    losing_team_id
  from {{ ref('int_nba__games_enriched') }}
),

teams as (
  select
    team_id,
    team_name,
    team_abbr
  from {{ ref('int_nba__teams') }}
),

final as (
  select
    s.game_id,
    s.game_event_id,
    s.player_id,
    s.player_name,
    s.team_id,
    t.team_abbr as team_abbr,
    g.season,
    g.season_type,
    g.game_date,

    -- Shot details
    s.period,
    s.minutes_remaining,
    s.seconds_remaining,
    s.event_type,
    s.action_type,
    s.shot_type,
    s.shot_zone_basic,
    s.shot_zone_area,
    s.shot_zone_range,
    s.shot_distance,
    s.loc_x,
    s.loc_y,
    s.shot_attempted_flag,
    s.shot_made_flag,

    -- Computed fields
    case when s.shot_made_flag = 1 then true else false end as shot_made,
    case when s.shot_type = '3PT Field Goal' then 3 else 2 end as shot_value,
    case
      when s.shot_made_flag = 1 and s.shot_type = '3PT Field Goal' then 3
      when s.shot_made_flag = 1 and s.shot_type = '2PT Field Goal' then 2
      else 0
    end as points_scored,

    -- Game context
    case when s.team_id = g.home_team_id then 'home' else 'away' end as home_away,
    case when s.team_id = g.winning_team_id then true else false end as team_won_game,

    -- Time remaining in game (approximate)
    ((4 - s.period) * 12 * 60) + (s.minutes_remaining * 60) + s.seconds_remaining as seconds_remaining_in_game

  from shots s
  left join games g on s.game_id = g.game_id
  left join teams t on s.team_id = t.team_id
)

select * from final
