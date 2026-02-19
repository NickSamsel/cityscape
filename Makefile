.PHONY: venv install test lint format dbt-deps dbt-run dbt-test dbt-docs dbt-clean

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
	cd dbt && uv run dbt deps --profiles-dir .

dbt-run:
	cd dbt && uv run dbt run --profiles-dir .

dbt-test:
	cd dbt && uv run dbt test --profiles-dir .

dbt-docs:
	cd dbt && uv run dbt docs generate --profiles-dir .

dbt-clean:
	cd dbt && uv run dbt clean --profiles-dir .
