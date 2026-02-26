# dbt Migration Guide - Beat the Streak ML Tables

This guide explains how to migrate the BigQuery tables from this repo to dbt models in your cityscape repo.

---

## Overview

Instead of managing these SQL files in this ML repo, you should create **dbt models** in your cityscape repo. This provides:
- ✅ Version control for schema changes
- ✅ Automatic dependency management
- ✅ Built-in testing and documentation
- ✅ Consistent deployment with your other data models
- ✅ Incremental builds for efficiency

---

## dbt Models to Create

You need to create **4 main dbt models** in your cityscape repo. These correspond to the SQL files in the `sql/` directory.

### Model Structure in cityscape

```
cityscape/
├── dbt_project.yml
└── models/
    └── mlb/                                    # New directory
        ├── schema.yml                          # Tests & docs
        ├── staging/
        │   ├── stg_mlb__player_rolling_stats.sql
        │   └── stg_mlb__pitcher_rolling_stats.sql
        └── marts/
            ├── fct_mlb__daily_game_context.sql
            └── fct_mlb__beat_the_streak_features.sql
```

---

## 1. Player Rolling Stats (Staging Model)

**File:** `models/mlb/staging/stg_mlb__player_rolling_stats.sql`

**Source SQL:** `sql/01_rolling_stats.sql`

```sql
{{
  config(
    materialized='table',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["player_id"]
  )
}}

-- Rolling batting stats for player performance
-- Calculates rolling window statistics (7, 15, 30 days)

SELECT
  player_id,
  game_date,
  team_id,

  -- Last 7 days
  AVG(hits) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) as hits_L7,

  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) as avg_L7,

  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
  ) as games_with_hit_L7,

  -- Last 15 days
  AVG(hits) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as hits_L15,

  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as avg_L15,

  -- Last 30 days
  AVG(hits) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ) as hits_L30,

  AVG(SAFE_CAST(avg AS FLOAT64)) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ) as avg_L30,

  AVG(SAFE_CAST(obp AS FLOAT64)) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ) as obp_L30,

  AVG(SAFE_CAST(slg AS FLOAT64)) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
  ) as slg_L30,

  -- Plate discipline (last 15 days)
  AVG(strikeout_rate) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as k_rate_L15,

  AVG(walk_rate) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as bb_rate_L15,

  -- Recent form indicators
  SUM(CASE WHEN hits > 0 THEN 1 ELSE 0 END) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
  ) as games_with_hit_L5,

  SUM(hits) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
  ) as total_hits_L3,

  -- Statcast metrics (last 15 days)
  AVG(avg_exit_velocity) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as exit_velo_L15,

  AVG(hard_hit_rate) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as hard_hit_rate_L15,

  AVG(barrel_rate) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as barrel_rate_L15

FROM {{ source('mlb', 'fct_mlb__player_batting_stats') }}
WHERE game_date >= '2020-01-01'
```

---

## 2. Pitcher Rolling Stats (Staging Model)

**File:** `models/mlb/staging/stg_mlb__pitcher_rolling_stats.sql`

**Source SQL:** `sql/02_pitcher_rolling.sql`

```sql
{{
  config(
    materialized='table',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["pitcher_id"]
  )
}}

-- Rolling pitching stats for pitcher performance
-- Calculates rolling window statistics (5, 15 days)

SELECT
  player_id as pitcher_id,
  game_date,
  team_id,

  -- Last 5 starts
  AVG(earned_runs) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
  ) as era_L5,

  AVG(whip) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
  ) as whip_L5,

  AVG(strikeouts_per_9) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 4 PRECEDING AND CURRENT ROW
  ) as k_per_9_L5,

  -- Last 15 days
  AVG(fip) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as fip_L15,

  AVG(opponent_batting_avg) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as opp_avg_L15,

  AVG(hard_hit_rate_allowed) OVER (
    PARTITION BY player_id
    ORDER BY game_date
    ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
  ) as hard_hit_allowed_L15

FROM {{ source('mlb', 'fct_mlb__player_pitching_stats') }}
WHERE game_date >= '2020-01-01'
```

---

## 3. Daily Game Context (Mart Model)

**File:** `models/mlb/marts/fct_mlb__daily_game_context.sql`

**Source SQL:** `sql/04_daily_context.sql`

```sql
{{
  config(
    materialized='table',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["game_id"]
  )
}}

-- Daily game context information
-- Contains venue, weather, and game-level features

SELECT
  game_id,
  game_date,
  home_team_id,
  away_team_id,
  home_score,
  away_score,
  venue_name,
  park_factor_hits,
  temperature,
  wind_speed,
  day_vs_night,
  game_time

FROM {{ source('mlb', 'stg_mlb__games') }}
WHERE game_date >= '2020-01-01'
```

---

## 4. Beat the Streak Features (Final Mart Model)

**File:** `models/mlb/marts/fct_mlb__beat_the_streak_features.sql`

**Source SQL:** `sql/05_feature_extraction.sql`

This is your **main feature table** that combines all upstream models.

```sql
{{
  config(
    materialized='table',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "day"
    },
    cluster_by=["player_id", "pitcher_id"]
  )
}}

-- Main feature extraction for Beat the Streak ML model
-- Combines player form, matchups, pitcher stats, and context

WITH pitcher_matchups AS (
  -- Identify the opposing pitcher for each batter's game
  SELECT
    b.player_id as batter_id,
    b.game_id,
    b.game_date,
    p.player_id as pitcher_id
  FROM {{ source('mlb', 'fct_mlb__player_batting_stats') }} b
  INNER JOIN {{ source('mlb', 'fct_mlb__player_pitching_stats') }} p
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

  -- Player form features (from rolling stats model)
  r.avg_L7 as rolling_batting_avg_L7,
  r.avg_L15 as rolling_batting_avg_L15,
  r.avg_L30 as rolling_batting_avg_L30,
  r.games_with_hit_L5,
  r.obp_L30,
  r.slg_L30,

  -- Statcast features
  r.exit_velo_L15,
  r.hard_hit_rate_L15,
  r.barrel_rate_L15,

  -- Matchup features
  m.career_avg_vs_pitcher,

  -- Zone matchup features (if available)
  z.zone_matchup_score,
  z.normalized_zone_score,
  z.max_zone_advantage,

  -- Regional zone features
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

FROM {{ source('mlb', 'fct_mlb__player_batting_stats') }} b

LEFT JOIN pitcher_matchups pm
  ON b.player_id = pm.batter_id
  AND b.game_id = pm.game_id

LEFT JOIN {{ ref('stg_mlb__player_rolling_stats') }} r
  ON b.player_id = r.player_id
  AND b.game_date = r.game_date

LEFT JOIN {{ ref('fct_mlb__daily_game_context') }} g
  ON b.game_id = g.game_id

LEFT JOIN {{ ref('stg_mlb__pitcher_rolling_stats') }} p
  ON pm.pitcher_id = p.pitcher_id
  AND b.game_date = p.game_date

LEFT JOIN {{ source('mlb', 'fct_mlb__pitcher_batter_matchups') }} m
  ON b.player_id = m.batter_id
  AND pm.pitcher_id = m.pitcher_id

LEFT JOIN {{ source('mlb', 'fct_mlb__zone_matchup_scores') }} z
  ON b.player_id = z.player_id
  AND pm.pitcher_id = z.pitcher_id
  AND EXTRACT(YEAR FROM b.game_date) = z.season

LEFT JOIN {{ source('mlb', 'fct_mlb__zone_regions_matchup') }} zr
  ON b.player_id = zr.player_id
  AND pm.pitcher_id = zr.pitcher_id
  AND EXTRACT(YEAR FROM b.game_date) = zr.season

WHERE b.game_date >= '2020-01-01'
```

**Key changes from SQL:**
- Uses `{{ ref('model_name') }}` for dbt dependencies
- Uses `{{ source('schema', 'table') }}` for raw tables
- Config block specifies partitioning and clustering

---

## 5. Schema Definition (Tests & Docs)

**File:** `models/mlb/schema.yml`

```yaml
version: 2

sources:
  - name: mlb
    database: project-7dd4e548-9904-449d-9b7
    schema: mlb
    tables:
      - name: fct_mlb__player_batting_stats
        description: Raw player batting statistics by game
      - name: fct_mlb__player_pitching_stats
        description: Raw pitcher statistics by game
      - name: stg_mlb__games
        description: Game-level information
      - name: fct_mlb__pitcher_batter_matchups
        description: Historical matchup data
      - name: fct_mlb__zone_matchup_scores
        description: Zone-level matchup scores
      - name: fct_mlb__zone_regions_matchup
        description: Regional zone matchup features

models:
  - name: stg_mlb__player_rolling_stats
    description: Rolling window statistics for player batting performance
    columns:
      - name: player_id
        description: Unique player identifier
        tests:
          - not_null
      - name: game_date
        description: Date of game
        tests:
          - not_null

  - name: stg_mlb__pitcher_rolling_stats
    description: Rolling window statistics for pitcher performance
    columns:
      - name: pitcher_id
        description: Unique pitcher identifier
        tests:
          - not_null
      - name: game_date
        description: Date of game
        tests:
          - not_null

  - name: fct_mlb__daily_game_context
    description: Daily game context and venue information
    columns:
      - name: game_id
        description: Unique game identifier
        tests:
          - unique
          - not_null

  - name: fct_mlb__beat_the_streak_features
    description: Final feature table for ML model training and prediction
    columns:
      - name: player_id
        description: Unique player identifier
        tests:
          - not_null
      - name: got_hit
        description: Target variable (1 if player got hit, 0 otherwise)
        tests:
          - accepted_values:
              values: [0, 1]
```

---

## Migration Steps

### Step 1: Create dbt Models in cityscape

```bash
cd ~/cityscape  # or wherever your cityscape repo is

# Create directory structure
mkdir -p models/mlb/staging
mkdir -p models/mlb/marts

# Create the 4 model files (copy SQL above)
# - models/mlb/staging/stg_mlb__player_rolling_stats.sql
# - models/mlb/staging/stg_mlb__pitcher_rolling_stats.sql
# - models/mlb/marts/fct_mlb__daily_game_context.sql
# - models/mlb/marts/fct_mlb__beat_the_streak_features.sql

# Create schema.yml (copy YAML above)
# - models/mlb/schema.yml
```

### Step 2: Run dbt

```bash
# Test model syntax
dbt parse

# Run specific models
dbt run --select stg_mlb__player_rolling_stats
dbt run --select stg_mlb__pitcher_rolling_stats
dbt run --select fct_mlb__daily_game_context
dbt run --select fct_mlb__beat_the_streak_features

# Or run all mlb models
dbt run --select mlb.*

# Run tests
dbt test --select mlb.*

# Generate docs
dbt docs generate
dbt docs serve
```

### Step 3: Update Python Code

Update your `src/data/bigquery_client.py` to reference the new dbt-managed table:

```python
# Old
table_ref = 'ml_mlb__final_features'

# New (after dbt migration)
table_ref = 'fct_mlb__beat_the_streak_features'
```

---

## Benefits of dbt Migration

| Benefit | Description |
|---------|-------------|
| **Dependency Management** | dbt automatically builds models in the correct order using `{{ ref() }}` |
| **Testing** | Built-in tests for data quality (not_null, unique, accepted_values) |
| **Documentation** | Auto-generated docs show lineage and column descriptions |
| **Version Control** | Schema changes tracked in git alongside dbt models |
| **CI/CD Integration** | Run `dbt test` in GitHub Actions before deploying |
| **Incremental Builds** | Only process new data, faster runs |
| **Consistency** | All data models follow same patterns and conventions |

---

## Summary

**Move your table definitions to dbt in cityscape for better data engineering practices, but keep the ML training/prediction code in this repo. This gives you the best of both worlds - robust data pipelines + clean ML code.**
