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
