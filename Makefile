.PHONY: venv install test lint format dbt-deps dbt-run dbt-test dbt-docs dbt-clean prefect-pool prefect-deploy

venv:
	uv venv -p 3.11

install:
	uv pip install -e .[dev]

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

dbt-deps:
	cd dbt && uv run dbt deps

dbt-run:
	cd dbt && uv run dbt run

dbt-test:
	cd dbt && uv run dbt test

dbt-docs:
	cd dbt && uv run dbt docs generate

dbt-clean:
	cd dbt && uv run dbt clean

prefect-pool:
	uv run prefect work-pool create cityscape-pool --type process --overwrite

prefect-deploy:
	uv run prefect deploy --prefect-file prefect.yaml --name mlb-season-daily --pool cityscape-pool
