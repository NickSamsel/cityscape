# Scripts

Utility scripts for data ingestion, migrations, and demos.

## Directory Structure

```
scripts/
├── mlb/              # MLB-specific ingestion scripts
├── nba/              # NBA-specific ingestion scripts (placeholder)
├── nfl/              # NFL-specific ingestion scripts (placeholder)
├── nhl/              # NHL-specific ingestion scripts (placeholder)
├── demos/            # Demo and comparison scripts
├── migrations/       # Data migration utilities
└── README.md         # This file
```

## MLB Scripts

### `mlb/ingest_teams_and_games.py`
Ingest MLB teams and games data for one or more seasons.

**Usage:**
```bash
# Default: last completed season
uv run python scripts/mlb/ingest_teams_and_games.py

# Specific season
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024

# Multiple seasons (sequential)
uv run python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024

# Multiple seasons (parallel - much faster!)
uv run python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel

# Date range filter (single season only)
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024 --start-date 2024-04-01 --end-date 2024-04-30

# Include playoff games
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024 --game-types R,F,D,L,W

# Parallel with custom worker count
uv run python scripts/mlb/ingest_teams_and_games.py --start-year 2000 --end-year 2024 --parallel --max-workers 15
```

**Options:**
- `--season`: Single season to ingest
- `--start-year` / `--end-year`: Season range for multi-season ingestion
- `--start-date` / `--end-date`: Filter games by date (YYYY-MM-DD)
- `--game-types`: Game types (R=regular, S=spring, F=wild card, D=division, L=championship, W=world series)
- `--parallel`: Use parallel processing for multi-season ingestion (recommended for large ranges)
- `--max-workers`: Number of concurrent seasons to process (default: 10)

**Performance:** 
- Sequential: ~5-10 seconds per season
- Parallel: Fetches 10 seasons concurrently (~10-15 seconds total for 10 seasons)
  - Uses batch write to avoid BigQuery rate limits

### `mlb/ingest_historical_player_stats.py`
Ingest historical MLB player game-by-game statistics for multiple seasons using parallel processing.

**Usage:**
```bash
# Default: last 20 years
uv run python scripts/mlb/ingest_historical_player_stats.py

# Specific range
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2010 --end-year 2024

# Single season
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2024 --end-year 2024

# Custom settings
uv run python scripts/mlb/ingest_historical_player_stats.py \
  --start-year 2020 \
  --end-year 2024 \
  --max-workers 30 \
  --game-types R,F
```

**Options:**
- `--start-year`: First season to ingest
- `--end-year`: Last season to ingest (inclusive)
- `--max-workers`: Number of parallel workers (default: 20)
- `--game-types`: Game types (R=regular, S=spring, F=wild card, etc.)

**Performance:** ~3 minutes per season with parallel processing

## NBA Scripts

### `nba/ingest_teams_and_games.py`
🚧 **Placeholder** - NBA data ingestion not yet implemented.

## NFL Scripts

### `nfl/ingest_teams_and_games.py`
🚧 **Placeholder** - NFL data ingestion not yet implemented.

## NHL Scripts

### `nhl/ingest_teams_and_games.py`
🚧 **Placeholder** - NHL data ingestion not yet implemented.

## Demo Scripts

### `demos/parallel_ingestion_comparison.py`
Demonstrates the performance difference between sequential and parallel ingestion.

**Usage:**
```bash
uv run python scripts/demos/parallel_ingestion_comparison.py
```

## Migration Scripts

### `migrations/postgres_to_bigquery.py`
Migrate data from Cloud SQL (Postgres) to BigQuery.

**Usage:**
```bash
uv run python scripts/migrations/postgres_to_bigquery.py
```

**Requirements:** Environment variables for both Postgres and BigQuery credentials.

## Implementing New Sport Integrations

To add data ingestion for NBA, NFL, or NHL:

1. **Create API Client** in `src/integrations/{sport}/`
   - Implement client to fetch teams, games, and stats
   - Follow the pattern used in `src/integrations/mlb/`

2. **Create Ingestion Functions** in `src/automations/ingest/`
   - Add functions to transform and load data to BigQuery
   - Follow the pattern in `src/automations/ingest/mlb_bigquery.py`

3. **Create Prefect Flows** in `src/automations/prefect/{sport}.py`
   - Define workflows for orchestration
   - Follow the pattern in `src/automations/prefect/mlb.py`

4. **Update BigQuery Utilities** in `src/utils/bigquery.py`
   - Add table creation and upsert functions
   - Follow the MLB table patterns

5. **Update Script** in `scripts/{sport}/`
   - Replace placeholder with actual implementation
   - Follow the pattern in MLB scripts
