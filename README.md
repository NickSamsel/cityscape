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

- Local run (inside dev container): `uv run python -m cityscape.automations.prefect.mlb`

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

- Keep `profiles.yml` out of git (it’s in `.gitignore`).
- Copy `dbt/.env.example` → `dbt/.env` and use env vars in your `profiles.yml`.

Common commands (inside the dev container):

- `make dbt-deps`
- `make dbt-run`
- `make dbt-test`

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

### Team & Game Data (Postgres)

Fetch MLB season data from the free MLB Stats API and land it into Postgres raw tables:

- `raw.mlb_teams`
- `raw.mlb_games`

Run inside the dev container (with `postgres` service up):

```bash
uv run cityscape ingest mlb --season 2024
```

Then build dbt staging models:

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
uv run python scripts/ingest_historical_player_stats.py

# Specific year range
uv run python scripts/ingest_historical_player_stats.py --start-year 2020 --end-year 2024

# Single season
uv run python scripts/ingest_historical_player_stats.py --start-year 2024 --end-year 2024

# View all options
uv run python scripts/ingest_historical_player_stats.py --help
```

Then build dbt models:

```bash
cd dbt
uv run dbt run --select tag:player_stats
uv run dbt test --select tag:player_stats
```

See [MLB_PLAYER_STATS_PIPELINE.md](./MLB_PLAYER_STATS_PIPELINE.md) for detailed documentation.
