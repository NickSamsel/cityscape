{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['player_id', 'game_id'],
    partition_by={"field": "game_date",
      "data_type": "date",
      "granularity": "month"},
    cluster_by=["player_id"],
    on_schema_change='sync_all_columns',
    tags=["modeling", "mlb"]
  )
-}}

SELECT
  player_id,
  game_id,
  game_date,
  team_id,

  -- Last 7 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as hits_L7,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as avg_L7,
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as games_with_hit_L7,

  -- Last 15 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as hits_L15,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as avg_L15,

  -- Last 30 days
  AVG(hits) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as hits_L30,
  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as avg_L30,
  AVG(SAFE_CAST(obp AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as obp_L30,
  AVG(SAFE_CAST(slg AS FLOAT64)) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) as slg_L30,

  -- Plate discipline (last 15 days)
  AVG(strikeout_rate) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as k_rate_L15,
  AVG(walk_rate) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as bb_rate_L15,

  -- Recent form indicators
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 4 PRECEDING AND CURRENT ROW) as games_with_hit_L5,
  SUM(hits) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) as total_hits_L3,

  -- Statcast metrics (last 15 days)
  AVG(avg_exit_velocity) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as exit_velo_L15,
  AVG(hard_hit_rate) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as hard_hit_rate_L15,
  AVG(barrel_rate) OVER (PARTITION BY player_id ORDER BY game_date, game_id ROWS BETWEEN 14 PRECEDING AND CURRENT ROW) as barrel_rate_L15

FROM {{ ref('fct_mlb__player_batting_stats') }}
WHERE game_date >= '2020-01-01'  -- Process all training data from 2020 onwards
{% if is_incremental() %}
  AND game_date >= DATE_SUB((SELECT MAX(game_date) FROM {{ this }}), INTERVAL 365 DAY)
{% endif %}