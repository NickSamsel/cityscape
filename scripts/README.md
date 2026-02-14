# Scripts

Utility scripts for data ingestion, migrations, and demos.

## Directory Structure

```
scripts/
├── mlb/              # MLB-specific ingestion scripts
├── nba/              # NBA-specific ingestion scripts
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
Ingest NBA teams, games, and player game stats for one or more seasons. **Supports historical data back to 1960!**

**Usage:**
```bash
# Default: current season (teams + games + player stats)
uv run python scripts/nba/ingest_teams_and_games.py

# Specific season
uv run python scripts/nba/ingest_teams_and_games.py --season 2024

# Multiple seasons (sequential)
uv run python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024

# Multiple seasons PARALLEL (RECOMMENDED - much faster!)
# Ingests teams, games, AND player stats concurrently
uv run python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel

# Historical backfill from 1960 to present (parallel mode)
uv run python scripts/nba/ingest_teams_and_games.py --start-year 1960 --end-year 2024 --parallel --max-workers 20

# Games only (skip player stats - faster but incomplete)
uv run python scripts/nba/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel --games-only

# Date range filter (single season only)
uv run python scripts/nba/ingest_teams_and_games.py --season 2024 --start-date 2024-10-01 --end-date 2024-12-31

# Include playoffs
uv run python scripts/nba/ingest_teams_and_games.py --season 2024 --season-type "Playoffs"

# Parallel with custom worker count (adjust based on API rate limits)
uv run python scripts/nba/ingest_teams_and_games.py --start-year 2015 --end-year 2024 --parallel --max-workers 15
```

**Options:**
- `--season`: Single season to ingest
- `--start-year` / `--end-year`: Season range for multi-season ingestion (supports back to 1960)
- `--start-date` / `--end-date`: Filter games by date (YYYY-MM-DD)
- `--season-type`: Season type (Regular Season, Playoffs, etc., default: Regular Season)
- `--parallel`: Use parallel processing for multi-season ingestion (HIGHLY recommended for large ranges)
- `--max-workers`: Number of concurrent seasons to process (default: 10, max recommended: 20)
- `--games-only`: Skip player stats ingestion (faster but incomplete data)
- `--include-player-stats`: Include player stats (default: True in parallel mode)

**What gets ingested:**
- NBA teams (30 teams)
- Conferences (East, West)
- Divisions (6 divisions)
- Games for specified seasons and types
- Player game-by-game statistics (individual shot stats, rebounds, assists, etc.)

**Performance:**
- Single season: ~2-5 minutes (depends on number of games)
- Parallel mode (complete): ~5-10 minutes per season (games + player stats)
- Parallel mode (games-only): ~30-60 seconds per season
- Historical backfill (1960-2024, 64 seasons): ~8-12 hours with max_workers=15-20
- Uses batch write to avoid BigQuery rate limits

**Recommended approach for historical data:**
```bash
# Ingest all NBA data from 1960 to present
uv run python scripts/nba/ingest_teams_and_games.py \
  --start-year 1960 \
  --end-year 2024 \
  --parallel \
  --max-workers 15
```

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
