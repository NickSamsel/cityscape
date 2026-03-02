{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['pitcher_id', 'game_id'],
    partition_by={"field": "game_date",
      "data_type": "date",
      "granularity": "month"},
    cluster_by=["pitcher_id"],
    on_schema_change='sync_all_columns',
    tags=["modeling", "mlb"]
  )
-}}

SELECT
  player_id AS pitcher_id,
  game_id,
  game_date,
  team_id,

  -- ERA (last 5 starts): (earned_runs * 9) / innings_pitched
  -- Must aggregate components first — averaging season ERAs or per-game rates is meaningless
  SAFE_DIVIDE(
    SUM(earned_runs) OVER w5 * 9.0,
    SUM(innings_pitched_decimal) OVER w5
  ) AS era_L5,

  -- WHIP (last 5 starts): (walks + hits) / innings_pitched
  SAFE_DIVIDE(
    SUM(COALESCE(walks, 0) + COALESCE(hits, 0)) OVER w5,
    SUM(innings_pitched_decimal) OVER w5
  ) AS whip_L5,

  -- K/9 (last 5 starts): (strikeouts * 9) / innings_pitched
  SAFE_DIVIDE(
    SUM(COALESCE(strikeouts, 0)) OVER w5 * 9.0,
    SUM(innings_pitched_decimal) OVER w5
  ) AS k9_L5,

  -- BB/9 (last 5 starts): (walks * 9) / innings_pitched
  SAFE_DIVIDE(
    SUM(COALESCE(walks, 0)) OVER w5 * 9.0,
    SUM(innings_pitched_decimal) OVER w5
  ) AS bb9_L5,

  -- FIP (last 15 appearances): ((13*HR) + (3*BB) - (2*K)) / IP + 3.2
  SAFE_DIVIDE(
    (13.0 * SUM(COALESCE(home_runs, 0)) OVER w15)
      + (3.0 * SUM(COALESCE(walks, 0)) OVER w15)
      - (2.0 * SUM(COALESCE(strikeouts, 0)) OVER w15),
    SUM(innings_pitched_decimal) OVER w15
  ) + 3.2 AS fip_L15,

  -- Velocity (last 15 appearances): averaging is appropriate for this metric
  AVG(avg_pitch_velocity) OVER w15 AS velo_L15,

  -- Opponent batting average (last 15 appearances): hits / estimated_batters_faced
  -- Estimated BF = outs (ip * 3) + hits + walks
  SAFE_DIVIDE(
    SUM(COALESCE(hits, 0)) OVER w15,
    SUM(innings_pitched_decimal) OVER w15 * 3
      + SUM(COALESCE(hits, 0)) OVER w15
      + SUM(COALESCE(walks, 0)) OVER w15
  ) AS opp_avg_L15,

  -- Quality starts (last 5 starts)
  SUM(CASE WHEN is_quality_start = TRUE THEN 1 ELSE 0 END) OVER w5 AS quality_starts_L5,

  -- K% (last 5 starts): strikeouts / estimated_batters_faced
  SAFE_DIVIDE(
    SUM(COALESCE(strikeouts, 0)) OVER w5 * 100.0,
    SUM(innings_pitched_decimal) OVER w5 * 3
      + SUM(COALESCE(hits, 0)) OVER w5
      + SUM(COALESCE(walks, 0)) OVER w5
  ) AS k_pct_L5,

  -- Zone rate (last 5 starts): averaging a per-pitch rate is appropriate
  AVG(zone_rate) OVER w5 AS zone_rate_L5

FROM {{ ref('fct_mlb__player_pitching_stats') }}
WHERE game_date >= '2020-01-01'
  AND game_type = 'R'  -- Regular season only: exclude spring training (S) and all-star (A) appearances
{% if is_incremental() %}
  AND game_date >= DATE_SUB((SELECT MAX(game_date) FROM {{ this }}), INTERVAL 365 DAY)
{% endif %}

WINDOW
  w5  AS (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW),
  w15 AS (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW)
