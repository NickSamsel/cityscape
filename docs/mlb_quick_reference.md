# MLB Pipeline - Quick Reference

## Two Approaches: Historical vs Daily

| Aspect | Historical Backfill | Daily Updates |
|--------|---------------------|---------------|
| **Purpose** | Load all data 2000-2026 | Keep data fresh |
| **Frequency** | Once (initial setup) | Daily (automated) |
| **Script** | `ingest_historical_backfill.py` | `daily_ingest.py` |
| **Runs Where** | Manual / local dev container | GitHub Actions |
| **Time Window** | Full seasons | Last 3 days |
| **Rosters** | All seasons | Weekly (Mondays) |
| **Duration** | 20-30 min (26 years) | 5-10 min per run |
| **API Calls** | ~30K total | ~200 per day |

---

## Quick Commands

### Historical Backfill (One-Time)

```bash
# Complete historical load (2000-2026) without Statcast
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast

# With Statcast for recent years only (more efficient)
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast

uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2015 \
  --end-year 2026 \
  --skip-rosters --skip-teams-games --skip-standings \
  --skip-schedule --skip-players --skip-venues

# Dry run to preview
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 --end-year 2026 --dry-run
```

### Daily Updates (Local Testing)

```bash
# Standard daily update (3-day lookback, weekly rosters)
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --update-rosters-weekly

# Skip rosters (if manually updated recently)
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --skip-rosters

# Skip Statcast for faster runs
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --skip-statcast --update-rosters-weekly

# Force roster update
uv run python scripts/mlb/daily_ingest.py --lookback-days 3
```

### After Data Ingestion

```bash
# Transform all data with dbt
cd dbt
uv run dbt run

# Or just MLB models
uv run dbt run --select tag:mlb
```

---

## GitHub Actions Workflow

**File:** `.github/workflows/mlb-daily-ingest.yml`

**Schedule:** Daily at 6 AM ET (10 AM UTC)

**What it does:**
1. ✅ Checks if in-season (skips Nov-Feb)
2. ✅ Fetches last 3 days of data
3. ✅ Updates rosters on Mondays
4. ✅ Runs dbt transformations
5. ✅ Cleans up credentials

**Manual trigger:**
- Go to Actions tab → "MLB Daily Ingest" → "Run workflow"
- Optional: adjust lookback days, skip Statcast, force roster update

---

## Required Secrets (GitHub)

Set these in your repository settings → Secrets → Actions:

1. **`GCP_PROJECT_ID`**
   - Your Google Cloud project ID
   - Example: `my-project-12345`

2. **`GCP_SERVICE_ACCOUNT_KEY`**
   - Base64-encoded service account JSON key
   - Create with:
     ```bash
     gcloud iam service-accounts keys create key.json \
       --iam-account=SERVICE_ACCOUNT@PROJECT.iam.gserviceaccount.com
     
     # Encode for GitHub
     base64 -w 0 key.json  # Linux
     base64 -i key.json    # macOS
     ```

---

## Optimization Details

### API Calls Per Season

| Data Type | Old Method | New Method | Savings |
|-----------|------------|------------|---------|
| Rosters | N/A | 30 calls | N/A |
| Player Discovery | 4,860 calls | 30 calls | **99.4%** |
| Teams & Games | ~200 calls | ~200 calls | Same |
| Total | ~6,000 calls | ~1,200 calls | **80%** |

### Time Comparison

| Task | Old | New | Improvement |
|------|-----|-----|-------------|
| 1 season | ~30 min | ~1 min | **97% faster** |
| 5 years | 8-12 hours | 15-30 min | **96% faster** |
| 26 years | 2-3 days | 20-30 min | **99% faster** |

---

## Troubleshooting

### "Access Denied" errors
- Verify service account has `bigquery.dataEditor` role
- Check dataset exists and permissions are correct
- Regenerate service account key if rotated

### Missing recent games
- Increase lookback days: `--lookback-days 7`
- Check MLB Stats API status
- Verify game status isn't "Postponed"

### GitHub Actions not running
- Check if workflow is enabled (Actions tab)
- Verify secrets are configured
- Manually trigger to test

---

## Complete Documentation

- **Deployment Guide:** [docs/mlb_deployment_guide.md](mlb_deployment_guide.md)
- **Optimization Details:** [docs/mlb_roster_optimization.md](mlb_roster_optimization.md)
- **Summary:** [OPTIMIZATION_SUMMARY.md](../OPTIMIZATION_SUMMARY.md)
- **Script Reference:** [scripts/README.md](../scripts/README.md)
