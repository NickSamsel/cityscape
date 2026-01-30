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

- `models/staging` (stg)
- `models/intermediate` (int)
- `models/core` (core)

Recommended local setup:

- Keep `profiles.yml` out of git (it’s in `.gitignore`).
- Copy `dbt/.env.example` → `dbt/.env` and use env vars in your `profiles.yml`.

Common commands (inside the dev container):

- `make dbt-deps`
- `make dbt-run`
- `make dbt-test`
