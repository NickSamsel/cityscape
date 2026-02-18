{{-
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={"field": "season", "data_type": "int64", "range": {"start": 2010, "end": 2035, "interval": 1}},
    cluster_by=["player_id", "pitcher_id"],
    on_schema_change='sync_all_columns',
    tags=["modeling", "mlb"]
  )
-}}

WITH zone_mapping AS (
  -- Map zones to regions (standard MLB strike zone is 13 zones)
  -- Zones 1-4: High, 5-9: Middle, 11-13: Low
  -- Zones 1,4,7,11: Inside, 2,5,8,12: Middle, 3,6,9,13: Outside
  SELECT zone,
    CASE
      WHEN zone IN (1,2,3,4) THEN 'high'
      WHEN zone IN (5,6,8,9) THEN 'middle'
      WHEN zone IN (11,12,13,14) THEN 'low'
      ELSE 'unknown'
    END as vertical_region,
    CASE
      WHEN zone IN (1,4,5,11) THEN 'inside'
      WHEN zone IN (2,8,12) THEN 'middle'
      WHEN zone IN (3,6,9,13) THEN 'outside'
      WHEN zone = 14 THEN 'chase'  -- Out of zone
      ELSE 'unknown'
    END as horizontal_region,
    CASE
      WHEN zone IN (1,2,3,4,5,6,8,9) THEN TRUE  -- Heart of zone
      ELSE FALSE
    END as in_heart
  FROM UNNEST(GENERATE_ARRAY(1, 14)) AS zone
),

hitter_region_success AS (
  -- Aggregate hitter success by region
  SELECT
    h.player_id as batter_id,
    h.season,
    zm.vertical_region,
    zm.horizontal_region,
    zm.in_heart,

    -- Success metrics
    AVG(h.success_rate) as avg_success_rate,
    SUM(h.total_pitches) as total_pitches,
    STDDEV(h.success_rate) as success_consistency

  FROM {{ ref('fct_mlb__pitch_zone_outcomes') }} h
  JOIN zone_mapping zm ON h.zone = zm.zone
  WHERE h.player_type = 'batter'
    AND h.season >= 2020
    AND h.total_pitches >= 5
    {% if is_incremental() %}
    AND h.season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 1
    {% endif %}
  GROUP BY batter_id, season, vertical_region, horizontal_region, in_heart
),

pitcher_region_frequency AS (
  -- Aggregate pitcher tendencies by region
  SELECT
    p.player_id as pitcher_id,
    p.season,
    zm.vertical_region,
    zm.horizontal_region,
    zm.in_heart,

    -- Frequency metrics
    SUM(p.total_pitches) as total_pitches,
    SUM(p.total_pitches) / SUM(SUM(p.total_pitches)) OVER (PARTITION BY p.player_id, p.season) as region_frequency

  FROM {{ ref('fct_mlb__pitch_zone_outcomes') }} p
  JOIN zone_mapping zm ON p.zone = zm.zone
  WHERE p.player_type = 'pitcher'
    AND p.season >= 2020
    AND p.total_pitches >= 5
    {% if is_incremental() %}
    AND p.season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 1
    {% endif %}
  GROUP BY pitcher_id, season, vertical_region, horizontal_region, in_heart
),

regional_matchups AS (
  -- Calculate matchup scores for each region combination
  SELECT
    h.batter_id,
    p.pitcher_id,
    h.season,

    -- Vertical matchups (pitcher throws high, hitter good at high?)
    MAX(CASE WHEN h.vertical_region = 'high' AND p.vertical_region = 'high'
         THEN h.avg_success_rate * p.region_frequency END) as high_zone_matchup,

    MAX(CASE WHEN h.vertical_region = 'middle' AND p.vertical_region = 'middle'
         THEN h.avg_success_rate * p.region_frequency END) as middle_zone_matchup,

    MAX(CASE WHEN h.vertical_region = 'low' AND p.vertical_region = 'low'
         THEN h.avg_success_rate * p.region_frequency END) as low_zone_matchup,

    -- Horizontal matchups
    MAX(CASE WHEN h.horizontal_region = 'inside' AND p.horizontal_region = 'inside'
         THEN h.avg_success_rate * p.region_frequency END) as inside_zone_matchup,

    MAX(CASE WHEN h.horizontal_region = 'outside' AND p.horizontal_region = 'outside'
         THEN h.avg_success_rate * p.region_frequency END) as outside_zone_matchup,

    -- Heart of zone
    MAX(CASE WHEN h.in_heart = TRUE AND p.in_heart = TRUE
         THEN h.avg_success_rate * p.region_frequency END) as heart_zone_matchup,

    -- Overall weighted average
    SUM(h.avg_success_rate * p.region_frequency * p.total_pitches) /
      NULLIF(SUM(p.total_pitches), 0) as weighted_avg_matchup

  FROM hitter_region_success h
  CROSS JOIN pitcher_region_frequency p
  WHERE h.season = p.season
    AND h.vertical_region = p.vertical_region
    AND h.horizontal_region = p.horizontal_region
  GROUP BY batter_id, pitcher_id, season
),

hitter_strengths AS (
  -- Identify hitter's best/worst zones
  SELECT
    batter_id,
    season,
    MAX(CASE WHEN vertical_region = 'high' THEN avg_success_rate END) as high_zone_success,
    MAX(CASE WHEN vertical_region = 'middle' THEN avg_success_rate END) as middle_zone_success,
    MAX(CASE WHEN vertical_region = 'low' THEN avg_success_rate END) as low_zone_success,
    MAX(CASE WHEN horizontal_region = 'inside' THEN avg_success_rate END) as inside_zone_success,
    MAX(CASE WHEN horizontal_region = 'outside' THEN avg_success_rate END) as outside_zone_success
  FROM hitter_region_success
  GROUP BY batter_id, season
),

pitcher_tendencies AS (
  -- Identify pitcher's preferred zones
  SELECT
    pitcher_id,
    season,
    MAX(CASE WHEN vertical_region = 'high' THEN region_frequency END) as high_zone_freq,
    MAX(CASE WHEN vertical_region = 'middle' THEN region_frequency END) as middle_zone_freq,
    MAX(CASE WHEN vertical_region = 'low' THEN region_frequency END) as low_zone_freq,
    MAX(CASE WHEN horizontal_region = 'inside' THEN region_frequency END) as inside_zone_freq,
    MAX(CASE WHEN horizontal_region = 'outside' THEN region_frequency END) as outside_zone_freq
  FROM pitcher_region_frequency
  GROUP BY pitcher_id, season
)

-- Final feature table with regional matchup features
SELECT
  rm.batter_id as player_id,
  rm.pitcher_id,
  rm.season,

  -- Regional matchup scores (higher = more favorable for hitter)
  COALESCE(rm.high_zone_matchup, 0) as high_zone_matchup,
  COALESCE(rm.middle_zone_matchup, 0) as middle_zone_matchup,
  COALESCE(rm.low_zone_matchup, 0) as low_zone_matchup,
  COALESCE(rm.inside_zone_matchup, 0) as inside_zone_matchup,
  COALESCE(rm.outside_zone_matchup, 0) as outside_zone_matchup,
  COALESCE(rm.heart_zone_matchup, 0) as heart_zone_matchup,
  COALESCE(rm.weighted_avg_matchup, 0) as overall_zone_matchup,

  -- Hitter strength profiles
  COALESCE(hs.high_zone_success, 0) as hitter_high_success,
  COALESCE(hs.low_zone_success, 0) as hitter_low_success,
  COALESCE(hs.inside_zone_success, 0) as hitter_inside_success,
  COALESCE(hs.outside_zone_success, 0) as hitter_outside_success,

  -- Pitcher tendency profiles
  COALESCE(pt.high_zone_freq, 0) as pitcher_high_freq,
  COALESCE(pt.low_zone_freq, 0) as pitcher_low_freq,
  COALESCE(pt.inside_zone_freq, 0) as pitcher_inside_freq,
  COALESCE(pt.outside_zone_freq, 0) as pitcher_outside_freq,

  -- Derived features
  CASE
    WHEN rm.high_zone_matchup > rm.low_zone_matchup AND pt.high_zone_freq > 0.3 THEN 1
    ELSE 0
  END as favorable_high,

  CASE
    WHEN rm.outside_zone_matchup > rm.inside_zone_matchup AND pt.outside_zone_freq > 0.3 THEN 1
    ELSE 0
  END as favorable_outside

FROM regional_matchups rm
LEFT JOIN hitter_strengths hs
  ON rm.batter_id = hs.batter_id AND rm.season = hs.season
LEFT JOIN pitcher_tendencies pt
  ON rm.pitcher_id = pt.pitcher_id AND rm.season = pt.season
WHERE rm.weighted_avg_matchup IS NOT NULL
