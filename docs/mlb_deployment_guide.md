# MLB Data Pipeline - Deployment Guide

## Two-Phase Approach

The MLB data pipeline is designed with two distinct phases:

### Phase 1: Historical Backfill (One-Time)
Load all historical data from 2000 to current year.

### Phase 2: Daily Incremental Updates (Automated)
GitHub Actions automatically fetches last 3 days of data every morning.

---

## Phase 1: Historical Backfill

### Purpose
- Load complete historical data (2000-2026)
- Set up the foundation for your data warehouse
- Run ONCE when setting up a new environment

### How to Run

**Option A: All-In-One Script (RECOMMENDED)**

```bash
# Without Statcast (faster - 20-30 minutes for 26 years)
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast

# With Statcast for recent years only (more efficient)
# First load everything without Statcast
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast

# Then add Statcast for 2015+ only
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2015 \
  --end-year 2026 \
  --skip-rosters \
  --skip-teams-games \
  --skip-standings \
  --skip-schedule \
  --skip-players \
  --skip-venues
```

**What Gets Loaded:**
1. ✅ Rosters (30 API calls per season - very fast!)
2. ✅ Teams & Games (all game data)
3. ✅ Standings (weekly snapshots)
4. ✅ Schedule (future games)
5. ✅ Statcast (2015+ only, optional)
6. ✅ Player Dimension Data (from rosters)
7. ✅ Venues (static data)

**Performance:**
- Without Statcast: ~20-30 minutes for 26 years (2000-2026)
- With Statcast: ~60-90 minutes (Statcast only available 2015+)

**After Historical Load:**

```bash
# Run dbt to transform all the data
cd dbt
uv run dbt run
```

---

## Phase 2: Daily Incremental Updates

### Purpose
- Keep data fresh with nightly updates
- Catch stat corrections (MLB fixes errors 1-3 days after games)
- Automatically update rosters weekly during season
- Run DAILY via GitHub Actions

### How It Works

**Automated via GitHub Actions:**
- Runs every morning at 6 AM ET (10 AM UTC)
- Fetches last 3 days of data (catches stat corrections)
- Updates rosters automatically on Mondays
- Only runs during season (March-October, skips November-February)

**File:** `.github/workflows/mlb-daily-ingest.yml`

**What Gets Updated:**
1. ✅ Rosters (Mondays only - weekly refresh)
2. ✅ Teams & Games (last 3 days)
3. ✅ Player Stats (last 3 days)
4. ✅ Standings (current)
5. ✅ Schedule (upcoming games)
6. ✅ Statcast (last 3 days, optional)
7. ✅ Player Dimension (from updated rosters)

**Manual Trigger:**

You can manually trigger the workflow from GitHub:
1. Go to Actions tab → "MLB Daily Ingest"
2. Click "Run workflow"
3. Optional inputs:
   - Season year (default: current year)
   - Lookback days (default: 3)
   - Skip Statcast (faster)
   - Force roster update

**Local Testing:**

```bash
# Test the daily ingestion locally
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --update-rosters-weekly

# Or skip rosters if you just updated them
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --skip-rosters

# Skip Statcast for faster runs
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --skip-statcast --update-rosters-weekly
```

---

## Required Setup

### GitHub Secrets

For GitHub Actions to work, configure these secrets in your repository:

1. **`GCP_PROJECT_ID`**
   - Your Google Cloud project ID
   - Example: `my-project-12345`

2. **`GCP_SERVICE_ACCOUNT_KEY`**
   - Base64-encoded service account JSON key
   - Must have BigQuery permissions:
     - `bigquery.datasets.get`
     - `bigquery.tables.create`
     - `bigquery.tables.updateData`
     - `bigquery.tables.get`

**To create the service account key:**

```bash
# Create service account
gcloud iam service-accounts create cityscape-github \
  --display-name="Cityscape GitHub Actions"

# Grant BigQuery permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:cityscape-github@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=cityscape-github@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Base64 encode for GitHub Secret
base64 -i key.json | pbcopy  # macOS
base64 -w 0 key.json         # Linux

# Delete local key file (sensitive!)
rm key.json
```

---

## Deployment Checklist

### Initial Setup (One-Time)

- [ ] **Set up GCP Service Account**
  - Create service account with BigQuery permissions
  - Generate JSON key
  - Base64 encode the key

- [ ] **Configure GitHub Secrets**
  - Add `GCP_PROJECT_ID`
  - Add `GCP_SERVICE_ACCOUNT_KEY`

- [ ] **Create BigQuery Dataset**
  ```bash
  # Create the 'raw' dataset if it doesn't exist
  bq mk --dataset --location=US YOUR_PROJECT_ID:raw
  ```

- [ ] **Run Historical Backfill**
  ```bash
  # Load all historical data (2000-2026)
  uv run python scripts/mlb/ingest_historical_backfill.py \
    --start-year 2000 \
    --end-year 2026 \
    --skip-statcast  # Optional: skip for faster initial load
  ```

- [ ] **Run dbt Transformation**
  ```bash
  cd dbt
  uv run dbt deps
  uv run dbt run
  ```

- [ ] **Verify Data**
  ```bash
  # Check row counts in BigQuery
  bq query --nouse_legacy_sql \
    'SELECT COUNT(*) FROM `YOUR_PROJECT_ID.raw.mlb_games`'
  ```

### Ongoing Operations (Automated)

- [ ] **Enable GitHub Actions**
  - Workflow runs automatically every day at 6 AM ET
  - Check Actions tab for run history

- [ ] **Monitor for Failures**
  - GitHub sends email notifications on workflow failures
  - Check workflow logs in Actions tab if issues occur

- [ ] **Weekly dbt Runs (Optional)**
  - Consider running dbt weekly to refresh marts
  - Can add separate GitHub Action for this

---

## Optimization Strategy

### Why 3-Day Lookback?

MLB occasionally corrects stats 1-2 days after games:
- Scoring decisions (earned runs, errors)
- Pitch classifications
- Player substitutions

A 3-day lookback ensures we catch all corrections while minimizing API calls.

### Why Weekly Roster Updates?

Rosters change infrequently:
- Trades (deadline: July 31)
- Promotions/demotions (weekly)
- Injured list moves (as needed)

Weekly updates during season are sufficient and save API calls.

### API Call Efficiency

**Old Approach (Deprecated):**
- ~4,860 API calls per season for player discovery
- ~6,000+ total calls per season
- Historical load: 8-12 hours for 5 years

**New Approach (Optimized):**
- 30 API calls per season for rosters
- ~1,200 total calls per season
- **99.4% fewer discovery calls**
- Historical load: 20-30 minutes for 26 years

---

## Troubleshooting

### Historical Backfill Failed

**Symptom:** Script exits with error during historical load

**Solutions:**
1. Use `--dry-run` to see execution plan
2. Use skip flags to run steps separately:
   ```bash
   # Load rosters only
   for year in {2000..2026}; do
     uv run python scripts/mlb/ingest_rosters.py --season $year
   done
   
   # Then skip rosters in backfill
   uv run python scripts/mlb/ingest_historical_backfill.py \
     --start-year 2000 --end-year 2026 \
     --skip-rosters --skip-statcast
   ```
3. Check BigQuery quotas and permissions

### GitHub Actions Not Running

**Symptom:** Workflow doesn't trigger at scheduled time

**Solutions:**
1. Check if workflow is enabled (Actions tab → workflow → "Enable workflow")
2. Verify it's not off-season (Nov-Feb skipped automatically)
3. Check GitHub Actions status page for outages
4. Manually trigger once to verify secrets are configured

### Missing Data

**Symptom:** Recent games not showing up

**Solutions:**
1. Check MLB Stats API status (api.mlb.com may have delays)
2. Increase lookback days temporarily:
   ```bash
   # Manual run with longer lookback
   uv run python scripts/mlb/daily_ingest.py --lookback-days 7
   ```
3. Check workflow logs for API errors
4. Verify game status isn't "Postponed" or "Cancelled"

### BigQuery Permissions Error

**Symptom:** "Access Denied" or "Permission denied" errors

**Solutions:**
1. Verify service account has `bigquery.dataEditor` role
2. Check dataset location matches (US region recommended)
3. Ensure service account has dataset-level access
4. Re-generate service account key if rotated

---

## Cost Estimation

### BigQuery Storage
- **Rosters:** ~5 MB per season × 26 years = ~130 MB
- **Games:** ~50 MB per season × 26 years = ~1.3 GB
- **Player Stats:** ~200 MB per season × 26 years = ~5.2 GB
- **Statcast:** ~2 GB per season × 12 years (2015+) = ~24 GB

**Total:** ~30-35 GB (within free tier: 10 GB storage, then $0.02/GB/month)

### GitHub Actions
- **Daily runs:** ~5-10 minutes per day × 30 days = 150-300 min/month
- **Free tier:** 2,000 minutes/month for public repos, 500 for private
- **Cost if over:** $0.008/minute for Linux runners

**Expected cost:** $0/month (within free tier)

### MLB Stats API
- **Free tier:** Unlimited (no authentication required)
- **Rate limits:** Generous, rarely hit with optimized workflow

---

## Next Steps

After successful deployment:

1. **Set up monitoring** (optional)
   - Create BigQuery views for data quality checks
   - Set up alerts for missing dates

2. **Optimize dbt runs** (optional)
   - Schedule dbt runs via separate GitHub Action
   - Use incremental models for faster refreshes

3. **Add visualization** (optional)
   - Connect to Looker, Tableau, or similar
   - Build dashboards on dbt marts

4. **Expand to other sports** (if desired)
   - NBA pipeline follows similar pattern
   - NFL/NHL pipelines planned

---

## Support

- **Documentation:** See [docs/](../docs/) for detailed guides
- **Scripts:** See [scripts/README.md](../scripts/README.md) for all available scripts
- **Optimization Guide:** See [docs/mlb_roster_optimization.md](mlb_roster_optimization.md)
- **Issues:** Report problems via GitHub Issues
