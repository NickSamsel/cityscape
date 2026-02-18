{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['player_id', 'game_id'],
    partition_by={"field": "game_date", "data_type": "date"},
    cluster_by=["player_id", "pitcher_id"],
    on_schema_change='sync_all_columns',
    tags=["modeling", "mlb"]
  )
-}}
WITH pitcher_matchups AS (
  -- Identify the opposing pitcher for each batter's game
  SELECT
    b.player_id as batter_id,
    b.game_id,
    b.game_date,
    p.player_id as pitcher_id
  FROM {{ ref('fct_mlb__player_batting_stats') }} b
  INNER JOIN {{ ref('fct_mlb__player_pitching_stats') }} p
    ON b.game_id = p.game_id
    AND b.team_id != p.team_id  -- Opposing teams
)
SELECT
  -- Identifiers
  b.player_id,
  b.game_date,
  pm.pitcher_id,
  b.game_id,

  -- Target (for training only)
  CASE WHEN b.hits >= 1 THEN 1 ELSE 0 END as got_hit,

  -- Player form features
  r.avg_L7 as rolling_batting_avg_L7,
  r.avg_L15 as rolling_batting_avg_L15,
  r.avg_L30 as rolling_batting_avg_L30,
  r.games_with_hit_L5,
  r.obp_L30,
  r.slg_L30,

  -- Statcast features (from batting stats and rolling stats)
  r.exit_velo_L15,
  r.hard_hit_rate_L15,
  r.barrel_rate_L15,

  -- Matchup features
  m.career_avg_vs_pitcher,

  -- Zone matchup features
  zm.overall_zone_matchup as zone_matchup_score,
  zm.overall_zone_matchup as normalized_zone_score,
  GREATEST(
    zm.high_zone_matchup,
    zm.middle_zone_matchup,
    zm.low_zone_matchup,
    zm.inside_zone_matchup,
    zm.outside_zone_matchup,
    zm.heart_zone_matchup
  ) as max_zone_advantage,

  -- Regional zone features
  zm.high_zone_matchup,
  zm.middle_zone_matchup,
  zm.low_zone_matchup,
  zm.inside_zone_matchup,
  zm.outside_zone_matchup,
  zm.heart_zone_matchup,
  zm.overall_zone_matchup,
  zm.hitter_high_success,
  zm.hitter_low_success,
  zm.hitter_inside_success,
  zm.hitter_outside_success,
  zm.pitcher_high_freq,
  zm.pitcher_low_freq,
  zm.pitcher_inside_freq,
  zm.pitcher_outside_freq,
  zm.favorable_high,
  zm.favorable_outside,

  -- Pitcher features
  p.era_L5 as pitcher_era_L5,
  p.whip_L5 as pitcher_whip_L5,
  p.fip_L15 as pitcher_fip_L15,

  -- Context features
  CASE WHEN b.team_id = g.home_team_id THEN 1 ELSE 0 END as home_vs_away

FROM {{ ref('fct_mlb__player_batting_stats') }} b
LEFT JOIN pitcher_matchups pm
  ON b.player_id = pm.batter_id AND b.game_id = pm.game_id
LEFT JOIN {{ ref('ml_mlb__rolling_batter_stats') }} r
  ON b.player_id = r.player_id AND b.game_id = r.game_id
LEFT JOIN {{ ref('fct_mlb__games') }} g
  ON b.game_id = g.game_id
LEFT JOIN {{ ref('ml_mlb__rolling_pitcher_stats') }} p
  ON pm.pitcher_id = p.pitcher_id AND b.game_id = p.game_id
LEFT JOIN {{ ref('ml_mlb__matchups') }} m
  ON b.player_id = m.batter_id AND pm.pitcher_id = m.pitcher_id
LEFT JOIN {{ ref('ml_mlb__zone_matchup') }} zm
  ON b.player_id = zm.player_id
  AND pm.pitcher_id = zm.pitcher_id
  AND EXTRACT(YEAR FROM b.game_date) = zm.season
WHERE b.game_date >= '2020-01-01'
{% if is_incremental() %}
  AND b.game_date > (SELECT MAX(game_date) FROM {{ this }})
{% endif %}