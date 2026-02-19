# Cityscape

Python workspace for orchestration + analytics.

## 🚀 Quick Start: MLB Data Pipeline

**Two-phase approach for loading and maintaining MLB data:**

### Phase 1: Historical Backfill (One-Time)
Load complete historical data from 2000-2026 in ~20-30 minutes:

```bash
# Run inside dev container
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast  # Optional: faster initial load
```

### Phase 2: Daily Updates (Automated via GitHub Actions)
After initial load, GitHub Actions automatically:
- Runs every morning at 6 AM ET
- Fetches last 3 days (catches stat corrections)
- Updates rosters weekly (Mondays)
- Only runs during season (March-October)

**📖 Complete guide:** [docs/mlb_deployment_guide.md](docs/mlb_deployment_guide.md)

---

## Quickstart (dev container)

- Start services: `docker compose up -d`
- Attach to the `dev` container (VS Code Dev Containers)

Inside the container:

- Create/refresh venv + install deps:
  - `uv venv -p 3.11`
  - `uv pip install -e .[dev]`
- Run tests: `uv run pytest`
- Run CLI: `uv run cityscape hello`

## Orchestration

Data pipelines are orchestrated via **GitHub Actions**:
- Daily MLB data ingestion runs automatically at 6 AM ET (scheduled via cron)
- Manual triggers available via workflow_dispatch for backfills
- See [.github/workflows/mlb-daily-ingest.yml](.github/workflows/mlb-daily-ingest.yml)

For local/manual execution, use the scripts in `scripts/mlb/`:
- `daily_ingest.py` - Daily updates (what GitHub Actions runs)
- `ingest_historical_backfill.py` - One-time historical data load

## dbt

The dbt project lives in `dbt/` and is structured for:

- `models/staging/<league>` (stg)
- `models/intermediate/<league>` (int)
- `models/marts/<league>` (marts)

Naming convention (standardized prefixes):

- Staging: `stg_<league>__<entity>`
- Intermediate: `int_<league>__<entity>`
- Marts: `dim_<league>__<entity>`, `fct_<league>__<entity>`

SQL portability (ANSI-leaning):

- Prefer `CAST(x AS type)` over Postgres `x::type`
- Avoid engine-specific functions when possible

Recommended local setup:

**The dev container automatically creates:**
- `dbt/profiles.yml` (configured for BigQuery with GCP service account)
- `/tmp/gcp-key.json` (GCP credentials from `GCP_SERVICE_ACCOUNT_KEY` env var)
- Installs dbt packages via `dbt deps`

**Required environment variables** (see `.env.example`):
- `GCP_PROJECT_ID` - Your Google Cloud project ID
- `GCP_SERVICE_ACCOUNT_KEY` - JSON service account key (as string)

Common commands (inside the dev container):

- `cd dbt && uv run dbt run --profiles-dir .`
- `cd dbt && uv run dbt test --profiles-dir .`
- `make dbt-run` (from project root)
- `make dbt-test` (from project root)

## Postgres persistence

Postgres data persists outside the containers via a named Docker volume (`cityscape-postgres-data`).

- Safe: `docker compose down` (stops/removes containers, keeps the volume)
- Destroys data: `docker compose down -v` (removes volumes)

## Python package structure

The Python code uses a single installable package under `src/`, organized as:

- `integrations/` — API clients, database clients, external system adapters
  - `mlb/` — MLB Stats API client with models, exceptions, and utilities
  - `http.py` — HTTP utilities
- `automations/` — ingestion pipelines and orchestration logic
  - `ingest/mlb/` — MLB-specific ingestion functions
- `utils/` — shared helpers (settings, logging, BigQuery, database utilities)

## MLB ingestion

### MLB ingest commands (all entrypoints)

All commands below are intended to run inside the dev container and land into BigQuery.

- Daily “do everything” windowed ingest (recommended):

```bash
uv run python scripts/mlb/daily_ingest.py

# Custom window controls
uv run python scripts/mlb/daily_ingest.py --season 2025 --lookback-days 3

# Faster run (skip Statcast)
uv run python scripts/mlb/daily_ingest.py --skip-statcast
```

- Teams + games (+ leagues/divisions) backfill:

```bash
# Single season
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024

# Multi-season (parallel)
uv run python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel
```

- Player game stats backfill (batting + pitching):

```bash
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2020 --end-year 2024
```

- Player dimension (from player IDs observed in stats tables):

```bash
uv run python scripts/mlb/ingest_players.py
uv run python scripts/mlb/ingest_players.py --parallel --max-workers 3
```

- Statcast pitches + batted balls:

```bash
uv run python scripts/mlb/ingest_statcast_data.py --season 2024
```

- Standings snapshots:

```bash
uv run python scripts/mlb/ingest_standings.py --season 2024
uv run python scripts/mlb/ingest_standings.py --start-season 2020 --end-season 2024
```

- Schedule + probable pitchers + broadcasts + lineups (+ venues/ballparks)
  - This is included in `scripts/mlb/daily_ingest.py` (step 5).
  - Standalone (example):

```bash
uv run python -c "from datetime import date; from src.automations.ingest.mlb_bigquery import ingest_mlb_schedule_bigquery; ingest_mlb_schedule_bigquery(season=2024, start_date=date(2024,4,1), end_date=date(2024,4,7))"
```

This standalone run ingests (at minimum):
- `raw.mlb_schedule` (includes `home_probable_pitcher_*` / `away_probable_pitcher_*` and `venue_id`)
- `raw.mlb_game_broadcasts`
- `raw.mlb_game_lineups`
- `raw.mlb_venues` (ballpark metadata like capacity + field dimensions)

- Venues (ballparks) only:

```bash
# Full season (all parks teams played in)
uv run python -m scripts.mlb.ingest_venues --season 2024 --game-types R,P

### MLB Data Pipeline (Complete Historical + Daily Updates)

**RECOMMENDED APPROACH: Two-Phase Deployment**

See comprehensive guide: **[docs/mlb_deployment_guide.md](docs/mlb_deployment_guide.md)**

**Phase 1: Historical Backfill (One-Time)**
```bash
# Load all data from 2000-2026 in ~20-30 minutes
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast  # Optional: faster initial load
```

**Phase 2: Daily Updates (Automated)**
- GitHub Actions runs automatically at 6 AM ET
- Fetches last 3 days (catches stat corrections)
- Updates rosters weekly (Mondays)
- See: `.github/workflows/mlb-daily-ingest.yml`

**Manual daily update:**
```bash
uv run python scripts/mlb/daily_ingest.py --lookback-days 3 --update-rosters-weekly
```

**Transform with dbt:**
```bash
cd dbt
uv run dbt run --select tag:mlb
```

**Documentation:**
- 📖 [Deployment Guide](docs/mlb_deployment_guide.md) - Complete setup instructions
- 📋 [Quick Reference](docs/mlb_quick_reference.md) - Commands cheat sheet
- ⚡ [Optimization Guide](docs/mlb_roster_optimization.md) - Technical details
- 📊 [Optimization Summary](OPTIMIZATION_SUMMARY.md) - What changed

### Individual Data Fetches (Advanced)

If you need to run specific data fetches separately:

**Rosters (Optimized - Start Here):**
```bash
uv run python scripts/mlb/ingest_rosters.py --season 2024
```

**Teams & Games:**
```bash
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024
```

**Players (from rosters):**
```bash
uv run python scripts/mlb/ingest_players.py --season 2024
```

**Standings:**
```bash
# Run via Python module
python -c "from src.automations.ingest.mlb import ingest_standings_bulk_historical; ingest_standings_bulk_historical(start_season=2020, end_season=2024)"
```

**Schedule:**
```bash
python -c "from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery; ingest_mlb_schedule_bigquery(season=2024)"
```

**Venues:**
```bash
# All venues (static data)
python -c "from src.automations.ingest.mlb.venues import ingest_mlb_venues_bigquery; ingest_mlb_venues_bigquery()"

# Or derive from schedule in a date window
uv run python -m scripts.mlb.ingest_venues --season 2024 --start-date 2024-04-01 --end-date 2024-04-07
```

**All scripts:** See [scripts/README.md](scripts/README.md)
