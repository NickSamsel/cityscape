# MLB Player Game-by-Game Stats Ingestion Pipeline

This pipeline fetches individual player statistics for each MLB game and loads them into BigQuery for analysis.

## Overview

The player stats pipeline complements the existing team/game data by providing detailed player performance metrics:

- **Batting Stats**: At-bats, hits, home runs, RBIs, stolen bases, walks, strikeouts, and more
- **Pitching Stats**: Innings pitched, strikeouts, earned runs, walks, pitches thrown, and more

## Data Flow

```
MLB Stats API (boxscore_data)
    ↓
Raw BigQuery Tables
    • raw.mlb_player_batting_stats
    • raw.mlb_player_pitching_stats
    ↓
dbt Staging Models
    • stg_mlb__player_batting_stats
    • stg_mlb__player_pitching_stats
    ↓
dbt Intermediate Models (enriched with game/team info)
    • int_mlb__player_batting_stats_enriched
    • int_mlb__player_pitching_stats_enriched
    ↓
dbt Core Models (final production models with calculated metrics)
    • core_mlb__player_batting_stats
    • core_mlb__player_pitching_stats
```

## Usage

### 1. Ingest Historical Data (Recommended)

Use the script with command line arguments for easy historical ingestion:

```bash
# Default: last 20 years
uv run python scripts/mlb/ingest_historical_player_stats.py

# Specific year range
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2010 --end-year 2024

# Single season
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2024 --end-year 2024

# Custom workers and game types
uv run python scripts/mlb/ingest_historical_player_stats.py --start-year 2020 --end-year 2024 --max-workers 30 --game-types R

# Show all options
uv run python scripts/mlb/ingest_historical_player_stats.py --help
```

### 2. Ingest a Single Season (via Prefect)

```bash
# Using Prefect flow directly
uv run python -c "from src.automations.prefect.mlb import mlb_player_stats_season_ingestion_parallel; mlb_player_stats_season_ingestion_parallel(season=2024)"
```

### 3. Daily Ingestion (with lookback window)

```bash
# Using daily flow with 2-day lookback for late updates
uv run python -c "from src.automations.prefect.mlb import mlb_player_stats_daily_ingestion_parallel; mlb_player_stats_daily_ingestion_parallel(season=2026, lookback_days=2)"
```

### 4. Build dbt Models

After ingesting raw data, build the dbt transformation models:

```bash
cd dbt

# Build all MLB player stats models
uv run dbt run --select tag:player_stats

# Or build specific layers
uv run dbt run --select tag:stg,tag:player_stats  # Staging only
uv run dbt run --select tag:int,tag:player_stats  # Intermediate only
uv run dbt run --select tag:core,tag:player_stats # Core only
```

### 5. Run dbt Tests

```bash
cd dbt
uv run dbt test --select tag:player_stats
```

## Prefect Deployments

Add these to `prefect.yaml` for scheduled runs:

```yaml
deployments:
  - name: mlb-player-stats-daily
    description: "Daily ingestion of MLB player game stats"
    entrypoint: src/cityscape/automations/prefect/mlb.py:mlb_player_stats_daily_ingestion
    parameters:
      season: 2026
      game_types: R
      lookback_days: 2
    work_pool:
      name: cityscape-pool
    schedule:
      cron: "30 6 * * *"  # 6:30 AM ET daily
      timezone: "America/New_York"
    tags:
      - mlb
      - player_stats
      - ingest

  - name: mlb-player-stats-full-season
    description: "Ingest complete MLB season player stats"
    entrypoint: src/cityscape.automations/prefect/mlb.py:mlb_player_stats_season_ingestion
    parameters:
      season: 2024
      game_types: R
    work_pool:
      name: cityscape-pool
    tags:
      - mlb
      - player_stats
      - backfill
```

## Query Examples

### Top Home Run Hitters for a Season

```sql
SELECT
  player_name,
  COUNT(DISTINCT game_id) as games_played,
  SUM(home_runs) as total_home_runs,
  SUM(rbi) as total_rbi
FROM `your-project.mlb_core.core_mlb__player_batting_stats`
WHERE season = 2024
  AND game_type = 'R'
GROUP BY player_name
HAVING total_home_runs > 0
ORDER BY total_home_runs DESC
LIMIT 10
```

### Top Strikeout Pitchers for a Season

```sql
SELECT
  player_name,
  COUNT(DISTINCT game_id) as games_pitched,
  SUM(innings_pitched_decimal) as total_innings,
  SUM(strikeouts) as total_strikeouts,
  ROUND(AVG(whip), 2) as avg_whip
FROM `your-project.mlb_core.core_mlb__player_pitching_stats`
WHERE season = 2024
  AND game_type = 'R'
GROUP BY player_name
HAVING total_innings >= 50
ORDER BY total_strikeouts DESC
LIMIT 10
```

### Player Performance Over Time

```sql
SELECT
  game_date,
  player_name,
  hits,
  home_runs,
  rbi,
  -- Running total of home runs
  SUM(home_runs) OVER (
    PARTITION BY player_id 
    ORDER BY game_date 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) as season_home_runs_total
FROM `your-project.mlb_core.core_mlb__player_batting_stats`
WHERE player_name = 'Shohei Ohtani'
  AND season = 2024
  AND game_type = 'R'
ORDER BY game_date
```

## Notes

- **Performance**: The parallel version processes ~2,400 games in 3-5 minutes. A full 20-year backfill takes ~60 minutes.
- **API Rate Limits**: The MLB Stats API is free with no strict rate limits, but parallel processing is recommended for large date ranges.
- **Data Quality**: Player stats are only available for completed games. The API returns empty stats for games that haven't been played yet.
- **Updates**: Use the daily ingestion with a lookback window to capture late stat corrections/updates.
- **Game Types**: Default is "R" (regular season). Other options: "S" (spring training), "F" (wild card), "D" (division series), "L" (league championship), "W" (World Series).
- **Command Line**: The `scripts/mlb/ingest_historical_player_stats.py` script provides the easiest interface for backfilling historical data.

## Architecture Details

### Data Models

1. **Raw Tables**: Exact replica of API response with all fields stored as JSON in `raw` column
2. **Staging**: Clean, typed, deduplicated base tables
3. **Intermediate**: Enriched with game context and team information via joins
4. **Core**: Production-ready with calculated metrics (singles, total bases, WHIP, strike %, etc.)

### Key Features

- **Idempotent**: Safe to re-run; uses MERGE/UPSERT logic
- **Incremental**: Can load specific date ranges
- **Comprehensive**: Captures all batting and pitching stats from boxscores
- **Calculated Metrics**: Automatically computes derived stats (WHIP, total bases, strike percentage)

## Troubleshooting

### Missing Player Stats

If you see games but no player stats:
- Verify the game has been completed (check game status)
- Some historical games may not have boxscore data available
- Try a different game from the same season

### BigQuery Permissions

Ensure your service account has:
- `bigquery.tables.create`
- `bigquery.tables.updateData`
- `bigquery.jobs.create`

### API Errors

If you encounter API errors:
- The free MLB Stats API occasionally has downtime
- Try reducing batch size or adding delays between requests
- Check boxscore data availability with a single test game first
