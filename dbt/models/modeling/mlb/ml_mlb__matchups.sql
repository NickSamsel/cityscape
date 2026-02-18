{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['batter_id', 'pitcher_id'],
    cluster_by=["batter_id", "pitcher_id"],
    on_schema_change='sync_all_columns',
    tags=["modeling", "mlb"]
  )
-}}

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
  FROM {{ ref('fct_mlb__player_batting_stats') }} b
  INNER JOIN {{ ref('fct_mlb__player_pitching_stats') }} p
    ON b.game_id = p.game_id
    AND b.team_id != p.team_id  -- Opposing teams
)

{% if is_incremental() %}

, last_processed AS (
    SELECT COALESCE(MAX(last_matchup_date), DATE '1900-01-01') AS max_last_matchup_date
    FROM {{ this }}
)

, new_matchup_data AS (
    SELECT *
    FROM matchup_data
    WHERE game_date > (SELECT max_last_matchup_date FROM last_processed)
)

, delta AS (
    SELECT
        batter_id,
        pitcher_id,

        COUNT(*) AS delta_total_matchups,
        SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) AS delta_games_with_hit,
        SUM(hits) AS delta_total_hits,
        SUM(at_bats) AS delta_total_at_bats,
        SUM(home_runs) AS delta_total_home_runs,
        SUM(strikeouts) AS delta_total_strikeouts,

        SUM(CASE WHEN season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 3 THEN hits ELSE 0 END) AS delta_recent_hits,
        SUM(CASE WHEN season >= EXTRACT(YEAR FROM CURRENT_DATE()) - 3 THEN at_bats ELSE 0 END) AS delta_recent_at_bats,

        MAX(game_date) AS delta_last_matchup_date,
        (ARRAY_AGG(STRUCT(game_date, hits) ORDER BY game_date DESC LIMIT 1))[OFFSET(0)].hits AS delta_last_matchup_hits

    FROM new_matchup_data
    GROUP BY 1, 2
)

, existing AS (
    SELECT *
    FROM {{ this }}
)

SELECT
    d.batter_id,
    d.pitcher_id,

    COALESCE(e.total_matchups, 0) + d.delta_total_matchups AS total_matchups,
    COALESCE(e.games_with_hit, 0) + d.delta_games_with_hit AS games_with_hit,
    COALESCE(e.total_hits, 0) + d.delta_total_hits AS total_hits,
    COALESCE(e.total_at_bats, 0) + d.delta_total_at_bats AS total_at_bats,
    COALESCE(e.total_home_runs, 0) + d.delta_total_home_runs AS total_home_runs,
    COALESCE(e.total_strikeouts, 0) + d.delta_total_strikeouts AS total_strikeouts,

    SAFE_DIVIDE(
        COALESCE(e.total_hits, 0) + d.delta_total_hits,
        NULLIF(COALESCE(e.total_at_bats, 0) + d.delta_total_at_bats, 0)
    ) AS career_avg_vs_pitcher,

    COALESCE(e.recent_hits, 0) + d.delta_recent_hits AS recent_hits,
    COALESCE(e.recent_at_bats, 0) + d.delta_recent_at_bats AS recent_at_bats,

    GREATEST(COALESCE(e.last_matchup_date, DATE '1900-01-01'), d.delta_last_matchup_date) AS last_matchup_date,
    CASE
        WHEN e.last_matchup_date IS NULL THEN d.delta_last_matchup_hits
        WHEN d.delta_last_matchup_date > e.last_matchup_date THEN d.delta_last_matchup_hits
        ELSE e.last_matchup_hits
    END AS last_matchup_hits,

    CURRENT_TIMESTAMP() AS loaded_at

FROM delta d
LEFT JOIN existing e
  USING (batter_id, pitcher_id)
WHERE (COALESCE(e.total_at_bats, 0) + d.delta_total_at_bats) >= 5  -- Minimum sample size

{% else %}

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
  (ARRAY_AGG(hits ORDER BY game_date DESC LIMIT 1))[OFFSET(0)] as last_matchup_hits,

  CURRENT_TIMESTAMP() AS loaded_at

FROM matchup_data
GROUP BY batter_id, pitcher_id
HAVING SUM(at_bats) >= 5  -- Minimum sample size

{% endif %}