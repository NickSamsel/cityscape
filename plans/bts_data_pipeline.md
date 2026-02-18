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

### 1) `bts_recommendations_daily`
One row per player recommendation per date.

**Primary key**: (`recommendation_date`, `player_id`, `model_version`)

Columns (minimum):
- `recommendation_date` (DATE)
- `model_version` (STRING)
- `player_id` (INT64/STRING)
- `player_name` (STRING)
- `team_id` (INT64/STRING)
- `team_abbr` (STRING)
- `opponent_team_id` (INT64/STRING)
- `game_id` (STRING) — nullable if doubleheaders / TBD
- `game_start_ts` (TIMESTAMP) — nullable
- `rank` (INT64)
- `pick_probability_hit` (FLOAT64) — model probability of at least one hit
- `confidence` (FLOAT64) — optional calibrated confidence
- `expected_hits` (FLOAT64) — optional
- `features_json` (STRING/JSON) — optional explanation payload
- `created_at` (TIMESTAMP)

### 2) `bts_player_game_outcomes`
One row per player per game with outcome used to score the recommendation.

**Primary key**: (`game_date`, `game_id`, `player_id`)

Columns:
- `game_date` (DATE)
- `game_id` (STRING)
- `player_id` (INT64/STRING)
- `player_name` (STRING)
- `team_id` (INT64/STRING)
- `had_hit` (BOOL) — scored truth
- `hits` (INT64)
- `ab` (INT64)
- `pa` (INT64)
- `walks` (INT64)
- `hbp` (INT64)
- `updated_at` (TIMESTAMP)

### 3) `bts_reco_scoring_daily`
Daily scoring join between recommendations and outcomes.

**Primary key**: (`recommendation_date`, `player_id`, `model_version`)

Columns:
- `recommendation_date` (DATE)
- `model_version` (STRING)
- `player_id` (INT64/STRING)
- `rank` (INT64)
- `pick_probability_hit` (FLOAT64)
- `had_hit` (BOOL) — nullable until games complete
- `scored_at` (TIMESTAMP) — when it became final

### 4) `bts_model_metrics_daily`
Aggregated metrics for UI.

**Primary key**: (`metric_date`, `model_version`, `metric_name`, `segment`)

Columns:
- `metric_date` (DATE)
- `model_version` (STRING)
- `metric_name` (STRING) — e.g., `top1_accuracy`, `top3_any_hit_accuracy`, `brier`, `logloss`
- `segment` (STRING) — e.g., `overall`, `vs_rhp`, `home`, `away`
- `metric_value` (FLOAT64)
- `n` (INT64)

### 5) (Optional) `bts_user_picks`
If you want per-user streak tracking in the warehouse.

**Primary key**: (`user_id`, `pick_date`)

Columns:
- `user_id` (STRING)
- `pick_date` (DATE)
- `player_id` (INT64/STRING)
- `model_version` (STRING)
- `had_hit` (BOOL) — nullable until final
- `streak_after` (INT64) — computed in ETL or in app

If you don’t want auth yet, skip this table and keep streak in localStorage on the client.

## Pipelines / Jobs

### A) Daily recommendation build
- Input: current day expected lineups + starting pitchers + park + player form, etc.
- Output: write rows into `bts_recommendations_daily` for `recommendation_date = CURRENT_DATE()`.
- Run time: early morning + optional refresh at lineup lock.

### B) Outcome ingestion + scoring
- Load final game logs into `bts_player_game_outcomes`.
- Join to recommendations into `bts_reco_scoring_daily`.
- Compute `bts_model_metrics_daily`.

## API / Access Layer (if DB repo includes a service)
If this repo exposes an API (Node/Express, Cloud Run, etc), define minimal read endpoints:
- `GET /bts/recommendations?date=YYYY-MM-DD&modelVersion=...`
- `GET /bts/metrics?start=...&end=...&modelVersion=...`
- `GET /bts/history?playerId=...&start=...&end=...`

If you **don’t** want an API, ensure the webapp has a stable BigQuery view for each query.

## Views for the Webapp
Create views that the UI can query without complex joins:
- `vw_bts_today_recommendations`
- `vw_bts_metrics_30d`
- `vw_bts_reco_history`

## Milestones
1. Define schema + create tables/views in BigQuery.
2. Implement daily reco write job (idempotent upsert).
3. Implement scoring join + daily metrics.
4. Add monitoring: row counts, freshness checks, alerting.

## Definition of Done
- Today page can render in under ~1–2 seconds (view-level performance acceptable).
- Data freshness visible (`created_at` / `updated_at`).
- Metrics computed for last 30 days at minimum.
