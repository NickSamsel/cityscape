{{-
  config(
    materialized='table',
    tags=["mart", "nba", "fact", "team_season"]
  )
-}}

-- Mart fact table for NBA team season statistics
-- Aggregates team performance by season from game results

with games as (
  select
    season,
    season_type,
    game_id,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    winning_team_id,
    losing_team_id
  from {{ ref('int_nba__games_enriched') }}
  where status = 'Final'  -- Only completed games
),

home_stats as (
  select
    home_team_id as team_id,
    season,
    season_type,
    count(*) as home_games,
    sum(case when winning_team_id = home_team_id then 1 else 0 end) as home_wins,
    sum(case when losing_team_id = home_team_id then 1 else 0 end) as home_losses,
    sum(home_score) as home_points_scored,
    sum(away_score) as home_points_allowed
  from games
  group by home_team_id, season, season_type
),

away_stats as (
  select
    away_team_id as team_id,
    season,
    season_type,
    count(*) as away_games,
    sum(case when winning_team_id = away_team_id then 1 else 0 end) as away_wins,
    sum(case when losing_team_id = away_team_id then 1 else 0 end) as away_losses,
    sum(away_score) as away_points_scored,
    sum(home_score) as away_points_allowed
  from games
  group by away_team_id, season, season_type
),

combined as (
  select
    coalesce(h.team_id, a.team_id) as team_id,
    coalesce(h.season, a.season) as season,
    coalesce(h.season_type, a.season_type) as season_type,
    coalesce(h.home_games, 0) + coalesce(a.away_games, 0) as games_played,
    coalesce(h.home_wins, 0) + coalesce(a.away_wins, 0) as total_wins,
    coalesce(h.home_losses, 0) + coalesce(a.away_losses, 0) as total_losses,
    coalesce(h.home_wins, 0) as home_wins,
    coalesce(h.home_losses, 0) as home_losses,
    coalesce(a.away_wins, 0) as away_wins,
    coalesce(a.away_losses, 0) as away_losses,
    coalesce(h.home_points_scored, 0) + coalesce(a.away_points_scored, 0) as total_points_scored,
    coalesce(h.home_points_allowed, 0) + coalesce(a.away_points_allowed, 0) as total_points_allowed
  from home_stats h
  full outer join away_stats a
    on h.team_id = a.team_id
    and h.season = a.season
    and h.season_type = a.season_type
),

teams as (
  select
    team_id,
    team_name,
    team_abbr,
    conference_id,
    division_id
  from {{ ref('int_nba__teams') }}
),

final as (
  select
    c.team_id,
    t.team_name,
    t.team_abbr,
    c.season,
    c.season_type,
    t.conference_id,
    t.division_id,
    c.games_played,
    c.total_wins,
    c.total_losses,
    safe_divide(c.total_wins, c.games_played) as win_percentage,
    c.home_wins,
    c.home_losses,
    safe_divide(c.home_wins, c.home_wins + c.home_losses) as home_win_percentage,
    c.away_wins,
    c.away_losses,
    safe_divide(c.away_wins, c.away_wins + c.away_losses) as away_win_percentage,
    c.total_points_scored,
    c.total_points_allowed,
    c.total_points_scored - c.total_points_allowed as point_differential,
    safe_divide(c.total_points_scored, c.games_played) as points_per_game,
    safe_divide(c.total_points_allowed, c.games_played) as points_allowed_per_game,
    safe_divide(c.total_points_scored - c.total_points_allowed, c.games_played) as point_diff_per_game
  from combined c
  left join teams t on c.team_id = t.team_id
)

select * from final
