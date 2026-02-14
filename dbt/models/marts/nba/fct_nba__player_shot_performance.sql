{{-
  config(
    materialized='table',
    tags=["mart", "nba", "fact", "shot_analytics"]
  )
-}}

-- Player shooting performance aggregated by zone and shot type
-- Enables shot chart visualization and shooting efficiency analysis

with shots as (
  select
    season,
    season_type,
    player_id,
    player_name,
    team_id,
    team_abbr,
    shot_type,
    shot_zone_basic,
    shot_zone_area,
    shot_zone_range,
    shot_distance,
    shot_made,
    points_scored,
    home_away
  from {{ ref('int_nba__shots_enriched') }}
),

player_shot_stats as (
  select
    season,
    season_type,
    player_id,
    player_name,
    team_id,
    team_abbr,
    shot_zone_basic,
    shot_zone_area,
    shot_type,

    -- Shooting counts
    count(*) as shots_attempted,
    sum(case when shot_made then 1 else 0 end) as shots_made,
    sum(case when not shot_made then 1 else 0 end) as shots_missed,

    -- Shooting percentages
    safe_divide(
      sum(case when shot_made then 1 else 0 end),
      count(*)
    ) as field_goal_pct,

    -- Points
    sum(points_scored) as total_points,
    safe_divide(sum(points_scored), count(*)) as points_per_shot,

    -- Distance stats
    avg(shot_distance) as avg_shot_distance,
    min(shot_distance) as min_shot_distance,
    max(shot_distance) as max_shot_distance,

    -- Home/Away splits
    sum(case when home_away = 'home' then 1 else 0 end) as home_shots,
    sum(case when home_away = 'away' then 1 else 0 end) as away_shots,
    safe_divide(
      sum(case when home_away = 'home' and shot_made then 1 else 0 end),
      sum(case when home_away = 'home' then 1 else 0 end)
    ) as home_fg_pct,
    safe_divide(
      sum(case when home_away = 'away' and shot_made then 1 else 0 end),
      sum(case when home_away = 'away' then 1 else 0 end)
    ) as away_fg_pct

  from shots
  group by
    season,
    season_type,
    player_id,
    player_name,
    team_id,
    team_abbr,
    shot_zone_basic,
    shot_zone_area,
    shot_type
)

select * from player_shot_stats
where shots_attempted >= 5  -- Filter out very low volume zones
