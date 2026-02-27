# ML Repo Integration Setup Guide

This guide documents the integration between the cityscape dbt pipeline and the beat-the-streak-ml repository for production feature engineering and prediction workflows.

## ✅ Completed Integration Tasks

### 1. BigQuery Table Schema

Created DDL for the raw predictions landing table:
- **File**: [sql/modeling/ml_mlb__model_predictions_raw.sql](sql/modeling/ml_mlb__model_predictions_raw.sql)
- **Table**: `mlb_modeling.ml_mlb__model_predictions_raw`
- **Schema**:
  - `player_id` (INT64) - Player identifier
  - `game_date` (DATE) - Date of game being predicted
  - `pitcher_id` (INT64) - Opposing pitcher identifier
  - `game_id` (STRING) - Game identifier
  - `hit_probability` (FLOAT64) - Model prediction (0.0-1.0)
  - `model_version` (STRING) - Model version (e.g., "v3.0.0")
  - `predicted_at` (TIMESTAMP) - UTC timestamp when prediction was generated
- **Partitioning**: By `game_date`
- **Clustering**: By `player_id`, `pitcher_id`

**To create the table**, run:
```bash
# Replace {{ project_id }} with your actual GCP project ID
bq query --use_legacy_sql=false < sql/modeling/ml_mlb__model_predictions_raw.sql
```

### 2. dbt Source Definition

Added source definition for the raw predictions table:
- **File**: [dbt/models/staging/sources.yml](dbt/models/staging/sources.yml)
- **Source**: `mlb_modeling.ml_mlb__model_predictions_raw`
- **Tests**: Added `not_null` tests for all required columns

### 3. Refactored `ml_mlb__daily_predictions`

Converted from a view to an incremental table:
- **File**: [dbt/models/modeling/mlb/ml_mlb__daily_predictions.sql](dbt/models/modeling/mlb/ml_mlb__daily_predictions.sql)
- **Previous**: Simple view selecting from `ml_mlb__prediction_dataset`
- **Current**: Incremental table sourcing from `ml_mlb__model_predictions_raw`
- **Enrichments**:
  - Player names and batting handedness
  - Team context (player's team, opponent team)
  - Game metadata (datetime, status, home/away)
- **Incremental strategy**: Merge on composite key `[player_id, game_date, pitcher_id, game_id]`
- **Partitioning**: By `game_date`
- **Clustering**: By `player_id`, `pitcher_id`

### 4. Created `ml_mlb__prediction_outcomes`

New model for tracking prediction accuracy:
- **File**: [dbt/models/modeling/mlb/ml_mlb__prediction_outcomes.sql](dbt/models/modeling/mlb/ml_mlb__prediction_outcomes.sql)
- **Purpose**: Join predictions with actual batting outcomes
- **Key features**:
  - Only includes completed games (status: Final, Completed, Game Over)
  - Calculates `got_hit` boolean (whether player got at least one hit)
  - Includes actual stats (`actual_hits`, `actual_at_bats`, `actual_plate_appearances`)
  - Calculates `prediction_correct` using 0.50 threshold
  - Timestamps resolution with `resolved_at`
- **Incremental strategy**: Merge on composite key
- **Look-back**: 7 days to catch recently completed games

### 5. Updated Schema Documentation

Enhanced documentation in [dbt/models/modeling/mlb/_mlb__modeling.yml](dbt/models/modeling/mlb/_mlb__modeling.yml):
- Added comprehensive column descriptions for `ml_mlb__daily_predictions`
- Added schema and tests for `ml_mlb__prediction_outcomes`
- Documented data lineage and purpose

### 6. Updated GitHub Actions Workflow

Modified [.github/workflows/mlb-daily-ingest.yml](.github/workflows/mlb-daily-ingest.yml):
- **New steps**:
  1. **Build prediction dataset**: Runs `ml_mlb__prediction_dataset` to prepare features
  2. **Trigger ML inference**: Placeholder for triggering beat-the-streak-ml workflow (needs configuration)
  3. **Wait for predictions**: Polls BigQuery for predictions (10 min timeout)
  4. **Build prediction models**: Runs `ml_mlb__daily_predictions` and `ml_mlb__prediction_outcomes`

---

## 🔧 Required Setup Steps

### Step 1: Create BigQuery Table

Run the DDL to create the raw predictions table:

```bash
# Set your project ID
export GCP_PROJECT_ID="your-project-id"

# Create the table (replace {{ project_id }} in the SQL file first)
sed "s/{{ project_id }}/$GCP_PROJECT_ID/g" sql/modeling/ml_mlb__model_predictions_raw.sql | \
  bq query --use_legacy_sql=false
```

### Step 2: Configure GitHub Secrets

Add the following secrets to the cityscape repository:

1. **`ML_REPO_DISPATCH_TOKEN`**: GitHub Personal Access Token with `repo` scope
   - Create at: https://github.com/settings/tokens
   - Required scopes: `repo` (for triggering workflows in beat-the-streak-ml)

2. **`ML_REPO_OWNER`**: GitHub username/org that owns beat-the-streak-ml repo
   - Example: `your-username` or `your-org`

3. Verify existing secrets are set:
   - `GCP_PROJECT_ID`
   - `GCP_SERVICE_ACCOUNT_KEY`

### Step 3: Update ML Repo Workflow

In the beat-the-streak-ml repository, update `.github/workflows/daily-predictions.yml` to accept `repository_dispatch` events:

```yaml
on:
  schedule:
    - cron: "0 13 * * *"  # 9 AM ET (1 PM UTC)
  workflow_dispatch:
    inputs:
      date:
        description: "Date to run predictions for (YYYY-MM-DD)"
        required: false
        type: string
  repository_dispatch:  # Add this
    types: [run_predictions]
```

Then update the job to use the dispatched date:

```yaml
jobs:
  predict:
    runs-on: ubuntu-latest
    steps:
      # ... existing steps ...

      - name: Run predictions
        run: |
          # Use date from dispatch payload, workflow input, or default to today
          PREDICTION_DATE="${{ github.event.client_payload.date || inputs.date || '' }}"

          if [ -z "$PREDICTION_DATE" ]; then
            PREDICTION_DATE=$(date +%Y-%m-%d)
          fi

          echo "Running predictions for: $PREDICTION_DATE"
          python scripts/predict.py --date "$PREDICTION_DATE" --model-version v3.0.0
```

### Step 4: Verify Service Account Permissions

Ensure the service accounts have proper permissions:

#### cityscape service account:
- ✅ Read from `modeling.ml_mlb__prediction_dataset` (for ML repo)
- ✅ Read from `mlb_modeling.ml_mlb__model_predictions_raw` (for dbt models)

#### ML repo service account:
- ✅ Read from `modeling.ml_mlb__prediction_dataset`
- ✅ Write to `mlb_modeling.ml_mlb__model_predictions_raw`

Grant permissions if needed:
```bash
# Grant ML repo service account write access
bq show --format=prettyjson mlb_modeling.ml_mlb__model_predictions_raw | \
  jq --arg sa "ml-service-account@project.iam.gserviceaccount.com" \
     '.access += [{"role": "WRITER", "userByEmail": $sa}]' | \
  bq update --source /dev/stdin mlb_modeling.ml_mlb__model_predictions_raw
```

### Step 5: Enable Workflow Trigger (Uncomment in Workflow)

Once secrets are configured, uncomment the API call in [.github/workflows/mlb-daily-ingest.yml](.github/workflows/mlb-daily-ingest.yml):

Find this section around line 160:
```yaml
# Option 1: Using repository_dispatch (recommended)
# Uncomment and configure the following once ML repo workflow_dispatch is set up:
# curl -X POST \
#   -H "Authorization: token ${{ secrets.ML_REPO_DISPATCH_TOKEN }}" \
```

Remove the `#` to activate the trigger.

### Step 6: Test End-to-End

Run a manual test:

```bash
# 1. Build the prediction dataset
cd dbt
uv run dbt run --select ml_mlb__prediction_dataset --vars '{prediction_date: 2026-04-15}'

# 2. Manually trigger ML inference (or wait for automatic trigger)
# Via GitHub UI: Actions → Daily Predictions → Run workflow → Enter date

# 3. Verify predictions appear in BigQuery
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) as cnt, MIN(predicted_at) as first_prediction
   FROM \`$GCP_PROJECT_ID.mlb_modeling.ml_mlb__model_predictions_raw\`
   WHERE game_date = '2026-04-15'"

# 4. Build downstream models
uv run dbt run --select ml_mlb__daily_predictions ml_mlb__prediction_outcomes

# 5. Verify data in final tables
bq query --use_legacy_sql=false \
  "SELECT player_name, hit_probability, model_version
   FROM \`$GCP_PROJECT_ID.modeling.ml_mlb__daily_predictions\`
   WHERE game_date = '2026-04-15'
   ORDER BY hit_probability DESC
   LIMIT 10"
```

---

## 📊 Daily Pipeline Flow

Once fully configured, the automated daily pipeline will:

```
[Morning — ~6 AM ET]
1. cityscape: Ingest last night's game results (raw MLB API data)
2. cityscape: dbt incremental build → rolling stats, matchups, zone matchups refreshed
3. cityscape: dbt build ml_mlb__prediction_dataset → features for TODAY's games
4. cityscape: Trigger beat-the-streak-ml workflow via GitHub API
5. ML REPO: Read ml_mlb__prediction_dataset, run inference, write to ml_mlb__model_predictions_raw
6. cityscape: Wait for predictions (poll BigQuery, 10 min timeout)
7. cityscape: Build ml_mlb__daily_predictions (enrich with player/game context)
8. cityscape: Build ml_mlb__prediction_outcomes (resolve YESTERDAY's predictions with actual outcomes)
```

---

## 📈 Monitoring and Metrics

### Key Queries for Monitoring

**Daily prediction count:**
```sql
SELECT
  game_date,
  COUNT(*) as prediction_count,
  COUNT(DISTINCT player_id) as unique_players,
  AVG(hit_probability) as avg_probability
FROM `modeling.ml_mlb__daily_predictions`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY game_date
ORDER BY game_date DESC
```

**Model accuracy (last 30 days):**
```sql
SELECT
  model_version,
  COUNT(*) as total_predictions,
  SUM(CASE WHEN got_hit THEN 1 ELSE 0 END) as actual_hits,
  SUM(CASE WHEN prediction_correct THEN 1 ELSE 0 END) as correct_predictions,
  ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END), 3) as accuracy,
  ROUND(AVG(hit_probability), 3) as avg_predicted_prob,
  ROUND(AVG(CASE WHEN got_hit THEN 1.0 ELSE 0.0 END), 3) as actual_hit_rate
FROM `modeling.ml_mlb__prediction_outcomes`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY model_version
ORDER BY model_version DESC
```

**Top predictions vs actual outcomes:**
```sql
SELECT
  player_name,
  game_date,
  hit_probability,
  got_hit,
  actual_hits,
  actual_at_bats,
  prediction_correct
FROM `modeling.ml_mlb__prediction_outcomes`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
ORDER BY hit_probability DESC
LIMIT 20
```

### Alerts to Set Up

1. **No predictions for today** (by 10 AM ET):
   ```sql
   SELECT COUNT(*) FROM `mlb_modeling.ml_mlb__model_predictions_raw`
   WHERE game_date = CURRENT_DATE()
   ```
   Alert if count = 0

2. **Prediction accuracy drops below threshold**:
   ```sql
   SELECT AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END) as accuracy
   FROM `modeling.ml_mlb__prediction_outcomes`
   WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
   ```
   Alert if accuracy < 0.55 (adjust based on baseline)

3. **Workflow failures**: Monitor GitHub Actions status

---

## 🔍 Troubleshooting

### Issue: Predictions not appearing in BigQuery

**Diagnosis:**
```bash
# Check ML workflow status
gh run list --repo your-org/beat-the-streak-ml --limit 5

# Check BigQuery table
bq query --use_legacy_sql=false \
  "SELECT MAX(game_date) as latest_prediction_date
   FROM \`mlb_modeling.ml_mlb__model_predictions_raw\`"
```

**Solutions:**
- Verify ML workflow was triggered (check GitHub Actions)
- Check ML repo service account has write permissions
- Verify `ml_mlb__prediction_dataset` has data for the date
- Review ML workflow logs for errors

### Issue: dbt models failing

**Common causes:**
- Missing predictions data (check source table)
- Schema changes in source tables
- Incremental strategy issues

**Solutions:**
```bash
# Full refresh if needed
uv run dbt run --select ml_mlb__daily_predictions --full-refresh

# Check for schema drift
uv run dbt test --select source:mlb_modeling.ml_mlb__model_predictions_raw
```

### Issue: Prediction outcomes not resolving

**Diagnosis:**
```sql
-- Check games without outcomes
SELECT
  p.game_date,
  p.game_id,
  s.status,
  COUNT(*) as pending_predictions
FROM `modeling.ml_mlb__daily_predictions` p
LEFT JOIN `modeling.ml_mlb__prediction_outcomes` o
  ON p.player_id = o.player_id
  AND p.game_date = o.game_date
  AND p.game_id = o.game_id
LEFT JOIN `modeling.fct_mlb__schedule` s
  ON p.game_id = s.game_id
WHERE o.player_id IS NULL
  AND p.game_date < CURRENT_DATE()
GROUP BY p.game_date, p.game_id, s.status
ORDER BY p.game_date DESC
```

**Solutions:**
- Games may be postponed/cancelled (status check)
- Batting stats may be delayed (check `fct_mlb__player_batting_stats`)
- Run dbt again after stats are ingested

---

## 📝 Next Steps / Future Enhancements

### Optional Improvements

1. **Historical Backfill**: Run inference for past 30-90 days to establish accuracy baseline
   ```bash
   # Example backfill script
   for date in $(seq -f "2026-04-%02g" 1 30); do
     gh workflow run daily-predictions.yml \
       --repo your-org/beat-the-streak-ml \
       --field date=$date
   done
   ```

2. **Calibration Curve Tracking**: Monitor if predicted probabilities match actual outcomes
   ```sql
   SELECT
     ROUND(hit_probability, 1) as prob_bucket,
     COUNT(*) as n,
     AVG(CASE WHEN got_hit THEN 1.0 ELSE 0.0 END) as actual_rate
   FROM `modeling.ml_mlb__prediction_outcomes`
   WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
   GROUP BY prob_bucket
   ORDER BY prob_bucket
   ```

3. **Dynamic Threshold Optimization**: Adjust `prediction_correct` threshold based on calibration

4. **Prediction Confidence Intervals**: Add uncertainty estimates to predictions

5. **Feature Drift Detection**: Monitor if input feature distributions change over time

---

## 📚 References

- **ML Repo**: `beat-the-streak-ml` repository (private)
- **Feature Schema**: See `ML_REPO_TODO.md` for full feature list
- **dbt Docs**: Run `uv run dbt docs generate && uv run dbt docs serve`
- **BigQuery Console**: https://console.cloud.google.com/bigquery

---

**Last Updated**: 2026-02-27
**Status**: ✅ Ready for deployment (pending secret configuration)
