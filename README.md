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

The Python code uses a single installable package under `src/cityscape/`, organized as:

- `integrations/` — API clients, database clients, external system adapters
- `automations/` — orchestration (e.g., Prefect flows/jobs)
- `utils/` — shared helpers (settings, logging, etc.)

## MLB ingestion (free)

This repo can fetch MLB season data from the free MLB Stats API (no API key) using the `MLB-StatsAPI` Python package and land it into Postgres raw tables:

- `raw.mlb_teams`
- `raw.mlb_games`

Run inside the dev container (with `postgres` service up):

- `uv run cityscape ingest mlb --season 2024`

Then build dbt staging models:

- `make dbt-run` (or `cd dbt && uv run dbt run -s tag:mlb`)
