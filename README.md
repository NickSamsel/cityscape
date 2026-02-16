# Cityscape

Python workspace for orchestration + analytics.

## Quickstart (dev container)

- Start services: `docker compose up -d`
- Attach to the `dev` container (VS Code Dev Containers)

Inside the container:

- Create/refresh venv + install deps:
  - `uv venv -p 3.11`
  - `uv pip install -e .[dev]`
- Run tests: `uv run pytest`
- Run CLI: `uv run cityscape hello`

## Prefect

The compose file starts Prefect Server on `http://localhost:4200` and sets `PREFECT_API_URL` in the dev container.

### Running flows

- Local run (inside dev container): `uv run python -m src.automations.prefect.mlb`

### Scheduling (yes, you can)

Prefect schedules are managed via **deployments**. A deployment has:

- an entrypoint (your flow function)
- optional parameters
- an optional schedule (cron/interval)

To actually execute scheduled runs, you also run a Prefect **worker** connected to your local server.

This repo includes a deployment definition at `prefect.yaml` and a compose service `prefect-worker`.

The MLB deployment uses a daily schedule, but the flow is **season-aware**:

- It calls the free MLB Stats API to determine the regular season start/end dates.
- If the season hasn’t started yet, the scheduled run logs a message and exits successfully.
- It ingests a small rolling window (`lookback_days`) for robustness.

Typical flow:

- `make prefect-pool` (create the local process work pool once)
- `make prefect-deploy` (apply deployments from `prefect.yaml`)
- `docker compose up -d prefect-worker` (start polling/executing scheduled runs)

Note: when running `prefect deploy` in the dev container, choose **not** to build a custom Docker image.

This project uses a **process** work pool/worker by default (runs flows as Python processes inside the worker container). A **docker** work pool is a different setup and typically requires Docker daemon access from the worker.

## dbt

The dbt project lives in `dbt/` and is structured for:

- `models/staging/<league>` (stg)
- `models/intermediate/<league>` (int)
- `models/core/<league>` (core)

Naming convention (standardized prefixes):

- Staging: `stg_<league>__<entity>`
- Intermediate: `int_<league>__<entity>`
- Core: `core_<league>__<entity>`

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
- `automations/` — orchestration (e.g., Prefect flows/jobs)
  - `ingest/mlb/` — MLB-specific ingestion functions
  - `prefect/` — Prefect flow definitions
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

# Or derive venue IDs from schedule in a small date window
uv run python -m scripts.mlb.ingest_venues --season 2024 --start-date 2024-04-01 --end-date 2024-04-07

# Or pass explicit venue IDs
uv run python -m scripts.mlb.ingest_venues --season 2024 --venue-ids 3,10,12
```

### Team & Game Data (BigQuery)

Fetch MLB season data from the free MLB Stats API and land it into BigQuery raw tables:

- `raw.mlb_teams`
- `raw.mlb_games`

Run inside the dev container:

```bash
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024
```

Then build dbt models:

```bash
make dbt-run  # or: cd dbt && uv run dbt run -s tag:mlb
```

### Player Stats (BigQuery)

Fetch player game-by-game statistics and land them into BigQuery:

- `raw.mlb_player_batting_stats`
- `raw.mlb_player_pitching_stats`

**Quick start:**

```bash
# Ingest last 20 years (parallel, ~60 minutes)
uv run python scripts/mlb/ingest_historical_player_stats.py

# Specific year range
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2020 --end-year 2024

# Single season
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2024 --end-year 2024

# Show all options
uv run python scripts/mlb/ingest_historical_player_stats.py --help
```

Then build dbt models:

```bash
cd dbt
uv run dbt run --select tag:player_stats
uv run dbt test --select tag:player_stats
```

See [MLB_PLAYER_STATS_PIPELINE.md](./MLB_PLAYER_STATS_PIPELINE.md) for detailed documentation.
