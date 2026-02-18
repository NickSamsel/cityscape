# Beat the Streak — DB Repo Plan

> Put this file at the root of your **DB / data platform repo**.

## Goal
Provide a reliable, daily-updated datastore for Beat the Streak recommendations, outcomes, and model performance so the webapp can render:
- “Today’s picks” (ranked hitters) with confidence + rationale features
- Progress to 57 hits (and other counters)
- Model accuracy over time and by segment
- Historical recommendations + actual results

## Assumptions
- BigQuery is the primary warehouse (this webapp already calls a `bigqueryService`).
- A scheduled job runs daily (and optionally intraday refresh) to generate the “today” slate.
- The warehouse is the source of truth; webapp only reads.

## Data Contract (Tables)
Create datasets/tables that are stable and versioned by `model_version`.

## Feature Table
### Build out a table with the following features for the ML model to pull from, must refresh daily with most up to date data
### Need both a training table with got hit case flag and a testing/prediction tabel for upcoming games
- Games with hit L5
- form matchup
- career average vs pitcher
- rolling batting average
- slg l30
- exit velo l15
- hard hit rate l15
- hot hitter weak pitcher

### Logic for tables

-- Create Pitcher vs Batter Matchup History Table
-- This table contains historical performance of batters against specific pitchers

CREATE OR REPLACE TABLE `${GCP_PROJECT_ID}.mlb.fct_mlb__pitcher_batter_matchups` AS
WITH matchup_data AS (
  SELECT
    b.player_id as batter_id,
    p.player_id as pitcher_id,
    b.game_id,
    b.game_date,
    b.season,
    b.hits,
    b.at_bats,
    b.home_runs,
    b.strikeouts
  FROM `${GCP_PROJECT_ID}.mlb.fct_mlb__player_batting_stats` b
  INNER JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__player_pitching_stats` p
    ON b.game_id = p.game_id
    AND b.team_id != p.team_id  -- Opposing teams
)
SELECT
  batter_id,
  pitcher_id,
  COUNT(*) as total_matchups,
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) as games_with_hit,
  SUM(hits) as total_hits,
  SUM(at_bats) as total_at_bats,
  SUM(home_runs) as total_home_runs,
  SUM(strikeouts) as total_strikeouts,
  SAFE_DIVIDE(SUM(hits), SUM(at_bats)) as career_avg_vs_pitcher,

  -- Recent matchup performance (last 3 years)
  SUM(CASE WHEN season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 3 THEN hits ELSE 0 END) as recent_hits,
  SUM(CASE WHEN season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 3 THEN at_bats ELSE 0 END) as recent_at_bats,

  -- Last matchup details
  MAX(game_date) as last_matchup_date,
  (ARRAY_AGG(hits ORDER BY game_date DESC LIMIT 1))[OFFSET(0)] as last_matchup_hits

FROM matchup_data
GROUP BY batter_id, pitcher_id
HAVING total_at_bats >= 5;  -- Minimum sample size

-- Create Rolling Batting Stats Table
-- This table contains rolling window statistics for player performance
CREATE OR REPLACE TABLE `${GCP_PROJECT_ID}.mlb.fct_mlb__player_rolling_batting_stats` AS
SELECT
  player_id,
  game_date,
  team_id,

  -- Last 7 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as hits_L7,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as avg_L7,
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as games_with_hit_L7,

  -- Last 15 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as hits_L15,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as avg_L15,

  -- Last 30 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hits_L30,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as avg_L30,
  AVG(SAFE_CAST(obp AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as obp_L30,
  AVG(SAFE_CAST(slg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as slg_L30,

  -- Plate discipline (last 15 days)
  AVG(strikeout_rate) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as k_rate_L15,
  AVG(walk_rate) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as bb_rate_L15,

  -- Recent form indicators
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as games_with_hit_L5,
  SUM(hits) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as total_hits_L3,

  -- Statcast metrics (last 15 days)
  AVG(avg_exit_velocity) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as exit_velo_L15,
  AVG(hard_hit_rate) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as hard_hit_rate_L15,
  AVG(barrel_rate) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as barrel_rate_L15

FROM `${GCP_PROJECT_ID}.mlb.fct_mlb__player_batting_stats`
WHERE game_date >= '2020-01-01';  -- Process all training data from 2020 onwards

-- Create Rolling Pitching Stats Table
-- This table contains rolling window statistics for pitcher performance

CREATE OR REPLACE TABLE `${GCP_PROJECT_ID}.mlb.fct_mlb__pitcher_rolling_stats` AS
SELECT
  player_id as pitcher_id,
  game_date,
  team_id,

  -- Last 5 starts
  AVG(SAFE_CAST(era AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as era_L5,
  AVG(whip) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as whip_L5,
  AVG(k_per_nine) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as k9_L5,
  AVG(bb_per_nine) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as bb9_L5,

  -- Last 15 days
  AVG(fip) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as fip_L15,
  AVG(avg_pitch_velocity) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as velo_L15,

  -- Quality starts (BOOLEAN needs CAST to INT or IF)
  SUM(CASE WHEN is_quality_start = TRUE THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as quality_starts_L5,

  -- Additional metrics
  AVG(k_percentage) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as k_pct_L5,
  AVG(zone_rate) OVER (PARTITION BY player_id ORDER BY game_date ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as zone_rate_L5

FROM `${GCP_PROJECT_ID}.mlb.fct_mlb__player_pitching_stats`
WHERE game_date >= '2020-01-01';  -- Process all training data from 2020 onwards

### The tables above can simply be created following table needs predcition/training versions

-- Main Feature Extraction Query
-- This query combines all feature sources for model training and prediction

CREATE OR REPLACE TABLE `${GCP_PROJECT_ID}.mlb.fct_mlb__beat_the_streak_features` AS
WITH pitcher_matchups AS (
  -- Identify the opposing pitcher for each batter's game
  SELECT
    b.player_id as batter_id,
    b.game_id,
    b.game_date,
    p.player_id as pitcher_id
  FROM `${GCP_PROJECT_ID}.mlb.fct_mlb__player_batting_stats` b
  INNER JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__player_pitching_stats` p
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

  -- Zone matchup feature (NEW!)
  z.zone_matchup_score,
  z.normalized_zone_score,
  z.max_zone_advantage,

  -- Regional zone features (V4)
  zr.high_zone_matchup,
  zr.middle_zone_matchup,
  zr.low_zone_matchup,
  zr.inside_zone_matchup,
  zr.outside_zone_matchup,
  zr.heart_zone_matchup,
  zr.overall_zone_matchup,
  zr.hitter_high_success,
  zr.hitter_low_success,
  zr.hitter_inside_success,
  zr.hitter_outside_success,
  zr.pitcher_high_freq,
  zr.pitcher_low_freq,
  zr.pitcher_inside_freq,
  zr.pitcher_outside_freq,
  zr.favorable_high,
  zr.favorable_outside,

  -- Pitcher features
  p.era_L5 as pitcher_era_L5,
  p.whip_L5 as pitcher_whip_L5,
  p.fip_L15 as pitcher_fip_L15,

  -- Context features
  CASE WHEN b.team_id = g.home_team_id THEN 1 ELSE 0 END as home_vs_away

FROM `${GCP_PROJECT_ID}.mlb.fct_mlb__player_batting_stats` b
LEFT JOIN pitcher_matchups pm
  ON b.player_id = pm.batter_id AND b.game_id = pm.game_id
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__player_rolling_batting_stats` r
  ON b.player_id = r.player_id AND b.game_date = r.game_date
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__daily_game_context` g
  ON b.game_id = g.game_id
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__pitcher_rolling_stats` p
  ON pm.pitcher_id = p.pitcher_id AND b.game_date = p.game_date
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__pitcher_batter_matchups` m
  ON b.player_id = m.batter_id AND pm.pitcher_id = m.pitcher_id
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__zone_matchup_scores` z
  ON b.player_id = z.player_id
  AND pm.pitcher_id = z.pitcher_id
  AND EXTRACT(YEAR FROM b.game_date) = z.season
LEFT JOIN `${GCP_PROJECT_ID}.mlb.fct_mlb__zone_regions_matchup` zr
  ON b.player_id = zr.player_id
  AND pm.pitcher_id = zr.pitcher_id
  AND EXTRACT(YEAR FROM b.game_date) = zr.season
WHERE b.game_date >= '2020-01-01';