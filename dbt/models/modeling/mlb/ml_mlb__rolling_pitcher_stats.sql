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
  player_id as pitcher_id,
  game_id,
  game_date,
  team_id,

  -- Last 5 starts
  AVG(SAFE_CAST(era AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as era_L5,
  AVG(whip) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as whip_L5,
  AVG(k_per_nine) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as k9_L5,
  AVG(bb_per_nine) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as bb9_L5,

  -- Last 15 days
  AVG(fip) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as fip_L15,
  AVG(avg_pitch_velocity) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as velo_L15,

  -- Opponent batting average (last 15 days)
  AVG(
    SAFE_DIVIDE(
      hits,
      (innings_pitched_decimal * 3) + hits + walks
    )
  ) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as opp_avg_L15,

  -- Quality starts (BOOLEAN needs CAST to INT or IF)
  SUM(CASE WHEN is_quality_start = TRUE THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as quality_starts_L5,

  -- Additional metrics
  AVG(k_percentage) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as k_pct_L5,
  AVG(zone_rate) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as zone_rate_L5

FROM {{ ref('fct_mlb__player_pitching_stats') }}
WHERE game_date >= '2020-01-01'  -- Process all training data from 2020 onwards
{% if is_incremental() %}
  AND game_date >= DATE_SUB((SELECT MAX(game_date) FROM {{ this }}), INTERVAL 365 DAY)
{% endif %}