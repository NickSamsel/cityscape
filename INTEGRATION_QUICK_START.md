# ML Integration Quick Start

Quick reference for the cityscape ↔ beat-the-streak-ml integration.

## 🚀 One-Time Setup (5 Steps)

### 1. Create BigQuery Table
```bash
export GCP_PROJECT_ID="your-project-id"
sed "s/{{ project_id }}/$GCP_PROJECT_ID/g" sql/modeling/ml_mlb__model_predictions_raw.sql | \
  bq query --use_legacy_sql=false
```

### 2. Add GitHub Secrets
In cityscape repo settings → Secrets → Actions:
- `ML_REPO_DISPATCH_TOKEN` - GitHub PAT with `repo` scope
- `ML_REPO_OWNER` - GitHub username/org (e.g., `your-username`)

### 3. Update ML Repo Workflow
In beat-the-streak-ml `.github/workflows/daily-predictions.yml`:
```yaml
on:
  repository_dispatch:
    types: [run_predictions]
```

### 4. Verify Service Account Permissions
```bash
# ML repo SA needs WRITE to mlb_modeling.ml_mlb__model_predictions_raw
# cityscape SA needs READ from mlb_modeling.ml_mlb__model_predictions_raw
```

### 5. Enable Trigger in Workflow
Uncomment lines 160-164 in `.github/workflows/mlb-daily-ingest.yml`

---

## 📊 New dbt Models

| Model | Type | Purpose |
|-------|------|---------|
| `ml_mlb__daily_predictions` | Incremental table | Predictions with player/game context |
| `ml_mlb__prediction_outcomes` | Incremental table | Predictions joined with actual outcomes |

**Source:**
- `mlb_modeling.ml_mlb__model_predictions_raw` - Landing table for ML predictions

---

## 🔄 Daily Pipeline Flow

```
6:00 AM ET - Ingest last night's games
           ↓
         dbt build (incremental stats refresh)
           ↓
         Build ml_mlb__prediction_dataset
           ↓
         Trigger ML inference workflow
           ↓
      [ML repo writes predictions to BigQuery]
           ↓
         Wait for predictions (10 min timeout)
           ↓
         Build ml_mlb__daily_predictions
           ↓
         Build ml_mlb__prediction_outcomes
```

---

## 🧪 Testing Commands

```bash
# 1. Build feature dataset for specific date
cd dbt
uv run dbt run --select ml_mlb__prediction_dataset \
  --vars '{prediction_date: 2026-04-15}'

# 2. Check predictions in BigQuery
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) FROM \`$GCP_PROJECT_ID.mlb_modeling.ml_mlb__model_predictions_raw\`
   WHERE game_date = '2026-04-15'"

# 3. Build prediction models
uv run dbt run --select ml_mlb__daily_predictions ml_mlb__prediction_outcomes

# 4. View top predictions
bq query --use_legacy_sql=false \
  "SELECT player_name, hit_probability, model_version
   FROM \`$GCP_PROJECT_ID.modeling.ml_mlb__daily_predictions\`
   WHERE game_date = '2026-04-15'
   ORDER BY hit_probability DESC
   LIMIT 10"
```

---

## 📈 Key Queries

**Daily prediction count:**
```sql
SELECT game_date, COUNT(*) as predictions
FROM `modeling.ml_mlb__daily_predictions`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY game_date
ORDER BY game_date DESC
```

**Model accuracy (last 30 days):**
```sql
SELECT
  model_version,
  ROUND(AVG(CASE WHEN prediction_correct THEN 1.0 ELSE 0.0 END), 3) as accuracy,
  COUNT(*) as total_predictions
FROM `modeling.ml_mlb__prediction_outcomes`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY model_version
```

**Calibration check:**
```sql
SELECT
  ROUND(hit_probability, 1) as prob_bucket,
  COUNT(*) as n,
  ROUND(AVG(CASE WHEN got_hit THEN 1.0 ELSE 0.0 END), 3) as actual_rate
FROM `modeling.ml_mlb__prediction_outcomes`
WHERE game_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY prob_bucket
ORDER BY prob_bucket
```

---

## 🔍 Troubleshooting

| Issue | Quick Fix |
|-------|-----------|
| No predictions today | Check ML workflow logs, verify trigger fired |
| dbt models failing | Run `--full-refresh`, check source data exists |
| Outcomes not resolving | Verify games completed, batting stats ingested |

**Detailed troubleshooting**: See [ML_INTEGRATION_SETUP.md](ML_INTEGRATION_SETUP.md#-troubleshooting)

---

## 📁 Files Modified/Created

### Created:
- `sql/modeling/ml_mlb__model_predictions_raw.sql` - BigQuery table DDL
- `dbt/models/modeling/mlb/ml_mlb__prediction_outcomes.sql` - Outcomes model
- `ML_INTEGRATION_SETUP.md` - Comprehensive setup guide
- `INTEGRATION_QUICK_START.md` - This file

### Modified:
- `dbt/models/staging/sources.yml` - Added modeling source
- `dbt/models/modeling/mlb/ml_mlb__daily_predictions.sql` - Refactored to incremental table
- `dbt/models/modeling/mlb/_mlb__modeling.yml` - Updated schema docs
- `.github/workflows/mlb-daily-ingest.yml` - Added ML integration steps
- `ML_REPO_TODO.md` - Marked cityscape tasks complete

---

**See [ML_INTEGRATION_SETUP.md](ML_INTEGRATION_SETUP.md) for detailed documentation**
