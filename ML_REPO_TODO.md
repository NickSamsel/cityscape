# ML Repo Integration TODO

> ✅ **UPDATE 2026-02-27**: Cityscape integration is complete! See [ML_INTEGRATION_SETUP.md](ML_INTEGRATION_SETUP.md) for full details.
>
> This document tracks the original integration plan. The cityscape side is done.
> ML repo tasks are tracked in the beat-the-streak-ml repository's version of this checklist.

---

## Background / Architecture Goal

The target daily pipeline (all automated via GitHub Actions in cityscape):

```
[Morning — ~6 AM ET]
1. cityscape: ingest last night's game results (raw MLB API data)
2. cityscape: dbt incremental build — rolling stats, matchups, zone matchups refreshed
3. cityscape: dbt build ml_mlb__prediction_dataset — features for TODAY's games
4. this repo: read ml_mlb__prediction_dataset from BigQuery, run inference, write predictions
5. cityscape: load predictions from GCS (or BQ write from step 4) → ml_mlb__daily_predictions
6. cityscape: resolve YESTERDAY's predictions — join ml_mlb__daily_predictions with actual
             batting outcomes → got_hit flag appended
```

The cityscape repo owns steps 1–3, 5–6. This repo owns step 4.

---

## Feature Schema (what BigQuery will provide)

The model should read from `ml_mlb__prediction_dataset` in BigQuery.
Query by `game_date = CURRENT_DATE()` (or pass date as a parameter).

```
Identifiers:
  player_id                  INT64
  game_date                  DATE
  pitcher_id                 INT64
  game_id                    STRING

Batter form features:
  rolling_batting_avg_L7     FLOAT64
  rolling_batting_avg_L15    FLOAT64
  rolling_batting_avg_L30    FLOAT64
  games_with_hit_L5          INT64
  obp_L30                    FLOAT64
  slg_L30                    FLOAT64

Statcast features:
  exit_velo_L15              FLOAT64
  hard_hit_rate_L15          FLOAT64
  barrel_rate_L15            FLOAT64

Matchup features:
  career_avg_vs_pitcher      FLOAT64

Zone matchup features:
  zone_matchup_score         FLOAT64   (alias: overall_zone_matchup)
  normalized_zone_score      FLOAT64
  max_zone_advantage         FLOAT64
  high_zone_matchup          FLOAT64
  middle_zone_matchup        FLOAT64
  low_zone_matchup           FLOAT64
  inside_zone_matchup        FLOAT64
  outside_zone_matchup       FLOAT64
  heart_zone_matchup         FLOAT64
  overall_zone_matchup       FLOAT64
  hitter_high_success        FLOAT64
  hitter_low_success         FLOAT64
  hitter_inside_success      FLOAT64
  hitter_outside_success     FLOAT64
  pitcher_high_freq          FLOAT64
  pitcher_low_freq           FLOAT64
  pitcher_inside_freq        FLOAT64
  pitcher_outside_freq       FLOAT64
  favorable_high             INT64
  favorable_outside          INT64

Pitcher features:
  pitcher_era_L5             FLOAT64
  pitcher_whip_L5            FLOAT64
  pitcher_fip_L15            FLOAT64

Context:
  home_vs_away               INT64     (1 = home, 0 = away)
  batter_features_asof_date  DATE
  pitcher_features_asof_date DATE
```

---

## TODO

### 1. Standardize prediction output schema
- [ ] Define (or confirm) the exact schema your model writes to GCS/BigQuery:
  ```
  player_id        INT64      — matches input player_id
  game_date        DATE       — the game date being predicted
  pitcher_id       INT64      — matches input pitcher_id
  game_id          STRING     — matches input game_id
  hit_probability  FLOAT64    — model output (0.0–1.0)
  model_version    STRING     — e.g. "v1.2.0" or a git SHA
  predicted_at     TIMESTAMP  — UTC timestamp of when inference ran
  ```
- [ ] Make sure all four identifier columns (`player_id`, `game_date`, `pitcher_id`, `game_id`)
      are preserved from the input features — cityscape needs them to join outcomes later.

---

### 2. Update inference script to read features from BigQuery
- [ ] Replace any local feature-building logic with a BigQuery read of
      `ml_mlb__prediction_dataset` filtered to the target `game_date`.
- [ ] Accept `--date` (or `--prediction-date`) as a CLI argument (default: today).
- [ ] Use the GCP service account for auth (same credentials used by cityscape).
  ```python
  from google.cloud import bigquery
  client = bigquery.Client(project=PROJECT_ID)
  query = f"""
      SELECT * FROM `{PROJECT_ID}.modeling.ml_mlb__prediction_dataset`
      WHERE game_date = '{prediction_date}'
  """
  df = client.query(query).to_dataframe()
  ```
- [ ] Handle the case where `ml_mlb__prediction_dataset` is empty for the target date
      (no games scheduled, or probable pitchers not yet posted). Log and exit cleanly.

---

### 3. Establish GCS file naming convention
- [ ] Write predictions to GCS using this path pattern:
  ```
  gs://<BUCKET>/predictions/mlb/hits/YYYY-MM-DD/predictions.parquet
  ```
  The date in the path should be `game_date` (the date of the games being predicted),
  not `predicted_at`.
- [ ] Use Parquet format (preferred over CSV — handles types cleanly and loads faster
      into BigQuery).
- [ ] If the file already exists for a given date, overwrite it (idempotent re-runs).

---

### 4. (Optional but recommended) Write predictions directly to BigQuery
- [ ] In addition to GCS, write the prediction output directly to a BigQuery table:
  ```
  <PROJECT_ID>.modeling.ml_mlb__model_predictions_raw
  ```
  Partition by `game_date`, cluster by `player_id`, `pitcher_id`.
- [ ] Use `WRITE_APPEND` or `WRITE_TRUNCATE` for a given date partition (idempotent).
- [ ] This eliminates the GCS-load step that cityscape otherwise needs and simplifies
      the overall pipeline. If you do this, communicate the table name so cityscape
      can reference it as a dbt source.

---

### 5. Make inference triggerable from CI
- [ ] The inference script should be runnable as a single command with no interactive
      prompts:
  ```
  python scripts/predict.py --date 2026-04-15 --model-version v1.2.0
  ```
- [ ] Verify all required env vars are documented (GCP project, bucket name,
      service account credentials path).
- [ ] Confirm the script exits with a non-zero code on failure so GitHub Actions
      can detect it.

---

### 6. Confirm model version tracking
- [ ] Decide how `model_version` is set — options:
  - Git SHA of the model training commit
  - Semantic version tag (e.g., `v1.2.0`)
  - Timestamp of when the model artifact was saved to GCS
- [ ] Make sure the model artifact path in GCS is also documented so cityscape
      can reference it in a README or config if needed.

---

### 7. Document the GCS bucket name and path
- [ ] Add to this repo's README (or a `config/` file):
  - Bucket name: `<YOUR_GCS_BUCKET>`
  - Predictions path prefix: `predictions/mlb/hits/`
  - Model artifact path: `models/mlb/hits/<version>/model.pkl` (or equivalent)
- [ ] This is the bucket that cityscape will point its BigQuery external table or
      ingestion script at.

---

## What cityscape will do once this is set up

For reference, here is what the cityscape repo needs to implement on its side
(tracked separately in that repo):

1. **New dbt source** — BigQuery external table or raw table pointing to
   `ml_mlb__model_predictions_raw` (from step 4 above) or loaded from GCS.

2. **Rework `ml_mlb__daily_predictions`** — change from a `SELECT *` view of
   `ml_mlb__prediction_dataset` into an incremental table sourced from the
   model predictions. Will include `hit_probability`, `model_version`, `predicted_at`.

3. **New model `ml_mlb__prediction_outcomes`** — joins the prior day's
   `ml_mlb__daily_predictions` with `fct_mlb__player_batting_stats` to add
   `got_hit` (binary outcome). This becomes the running accuracy tracker.

4. **Updated GitHub Actions workflow** — adds a step to trigger this repo's
   inference script (or polls GCS for today's prediction file) after the dbt
   feature build completes.

---

## Open Questions to Resolve

- [ ] **GCS bucket name** — what bucket are predictions currently being written to?
      Does cityscape have read access via its service account?
- [ ] **Prediction timing** — does the inference script run before or after probable
      pitchers are posted? (cityscape's `ml_mlb__prediction_dataset` filters to games
      with `has_probable_pitchers = true`, so pitchers must be posted before inference.)
      Typical MLB probable pitcher posting time is the night before or morning of the game.
- [ ] **Direct BQ write vs. GCS load** — pick one as the primary path to simplify the
      handoff to cityscape.
- [ ] **Historical backfill** — do you want to backfill predictions for past games
      (where you have model artifacts) so `ml_mlb__prediction_outcomes` has historical
      accuracy data from day one?
