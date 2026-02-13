{{-
  config(
    materialized='table',
    tags=["core", "nba", "player_season"]
  )
-}}

-- Core fact table for NBA player season statistics
-- Aggregates enriched player game-by-game stats into season totals with advanced metrics

with player_game_stats as (
  select *
  from {{ ref('int_nba__player_game_stats_enriched') }}
),

players as (
  select
    player_id,
    full_name,
    position,
    draft_year
  from {{ ref('int_nba__players_enriched') }}
),

season_aggregates as (
  select
    player_id,
    team_id,
    team_name,
    team_abbr,
    season,
    sum(coalesce(field_goals_made, 0)) as total_field_goals_made,
    sum(coalesce(field_goals_attempted, 0)) as total_field_goals_attempted,
    sum(coalesce(three_pointers_made, 0)) as total_three_pointers_made,
    sum(coalesce(three_pointers_attempted, 0)) as total_three_pointers_attempted,
    sum(coalesce(free_throws_made, 0)) as total_free_throws_made,
    sum(coalesce(free_throws_attempted, 0)) as total_free_throws_attempted,
    sum(coalesce(offensive_rebounds, 0)) as total_offensive_rebounds,
    sum(coalesce(defensive_rebounds, 0)) as total_defensive_rebounds,
    sum(coalesce(total_rebounds, 0)) as total_rebounds,
    sum(coalesce(assists, 0)) as total_assists,
    sum(coalesce(steals, 0)) as total_steals,
    sum(coalesce(blocks, 0)) as total_blocks,
    sum(coalesce(turnovers, 0)) as total_turnovers,
    sum(coalesce(personal_fouls, 0)) as total_personal_fouls,
    sum(coalesce(points, 0)) as total_points,
    count(*) as games_played,
    count(case when starter then 1 end) as games_started
  from player_game_stats
  group by player_id, team_id, team_name, team_abbr, season
),

stats_with_metrics as (
  select
    s.player_id,
    p.full_name as player_name,
    p.position,
    s.team_id,
    s.team_name,
    s.team_abbr,
    s.season,
    s.games_played,
    s.games_started,
    s.total_field_goals_made,
    s.total_field_goals_attempted,
    s.total_three_pointers_made,
    s.total_three_pointers_attempted,
    s.total_free_throws_made,
    s.total_free_throws_attempted,
    s.total_offensive_rebounds,
    s.total_defensive_rebounds,
    s.total_rebounds,
    s.total_assists,
    s.total_steals,
    s.total_blocks,
    s.total_turnovers,
    s.total_personal_fouls,
    s.total_points,
    -- Per game averages
    {{ safe_divide('s.total_points', 's.games_played', none) }} as points_per_game,
    {{ safe_divide('s.total_rebounds', 's.games_played', none) }} as rebounds_per_game,
    {{ safe_divide('s.total_assists', 's.games_played', none) }} as assists_per_game,
    {{ safe_divide('s.total_steals', 's.games_played', none) }} as steals_per_game,
    {{ safe_divide('s.total_blocks', 's.games_played', none) }} as blocks_per_game,
    {{ safe_divide('s.total_turnovers', 's.games_played', none) }} as turnovers_per_game,
    -- Shooting percentages
    {{ safe_divide('s.total_field_goals_made', 's.total_field_goals_attempted', none) }} as field_goal_percentage,
    {{ safe_divide('s.total_three_pointers_made', 's.total_three_pointers_attempted', none) }} as three_point_percentage,
    {{ safe_divide('s.total_free_throws_made', 's.total_free_throws_attempted', none) }} as free_throw_percentage,
    -- Advanced metrics
    {{ calculate_assist_to_turnover_ratio('s.total_assists', 's.total_turnovers') }} as assist_to_turnover_ratio,
    {{ safe_divide('s.total_steals + s.total_blocks', 's.games_played', none) }} as defensive_plays_per_game,
    -- True shooting percentage: TS% = Points / (2 * (FGA + 0.44 * FTA))
    {{ calculate_true_shooting_pct('s.total_points', 's.total_field_goals_attempted', 's.total_free_throws_attempted') }} as true_shooting_percentage,
    -- Effective field goal percentage: eFG% = (FGM + 0.5 * 3PM) / FGA
    {{ calculate_effective_fg_pct('s.total_field_goals_made', 's.total_three_pointers_made', 's.total_field_goals_attempted') }} as effective_field_goal_percentage,
    -- Usage indicators
    {{ safe_divide('s.games_started', 's.games_played', none) }} as starter_percentage,
    -- Career context
    case
      when p.draft_year is not null then s.season - p.draft_year
      else null
    end as years_since_draft,
    p.draft_year
  from season_aggregates s
  left join players p on s.player_id = p.player_id
)

select * from stats_with_metrics
