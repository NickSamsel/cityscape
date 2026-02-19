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

### `mlb/ingest_historical_backfill.py` 🚀 ALL-IN-ONE SOLUTION
**THE EASIEST WAY** to load historical data for multiple seasons. One script does everything!

**What it does:**
1. ✅ Rosters (optimized - 30 API calls per season)
2. ✅ Teams & games
3. ✅ Standings
4. ✅ Schedule
5. ✅ Statcast data (2015+ only, where available)
6. ✅ Player dimension data (from rosters)
7. ✅ Venues

**Perfect for:**
- Initial data load (2000-2026)
- Multi-year historical backfills
- Setting up a new environment
- "Just load everything" scenarios

**Usage:**
```bash
# Full historical backfill (2000 to current year)
uv run python scripts/mlb/ingest_historical_backfill.py

# Specific range (e.g., 2000-2026)
uv run python scripts/mlb/ingest_historical_backfill.py --start-year 2000 --end-year 2026

# Skip Statcast for faster ingestion (Statcast is slow!)
uv run python scripts/mlb/ingest_historical_backfill.py --start-year 2000 --end-year 2026 --skip-statcast

# Just recent years with everything
uv run python scripts/mlb/ingest_historical_backfill.py --start-year 2020 --end-year 2026

# Dry run to see what would be executed
uv run python scripts/mlb/ingest_historical_backfill.py --start-year 2000 --end-year 2026 --dry-run

# Skip specific steps if already loaded
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2024 --end-year 2026 \
  --skip-rosters \
  --skip-venues
```

**Options:**
- `--start-year`: First season (default: 2000)
- `--end-year`: Last season (default: current year)
- `--skip-statcast`: Skip Statcast (much faster, but incomplete for 2015+)
- `--skip-rosters`: Skip roster ingestion
- `--skip-teams-games`: Skip teams and games
- `--skip-standings`: Skip standings
- `--skip-schedule`: Skip schedule
- `--skip-players`: Skip player dimension
- `--skip-venues`: Skip venues
- `--game-types`: Game types (default: R,F,D,L,W - regular + playoffs)
- `--dry-run`: Show what would be executed without running
- `--verbose`: Enable detailed logging

**Performance:**
- ~30-60 seconds per season (without Statcast)
- ~2-5 minutes per season (with Statcast for 2015+)
- **Estimated for 2000-2026 (26 seasons):**
  - Without Statcast: ~20-30 minutes
  - With Statcast: ~60-90 minutes

**Example for your use case (2000-2026):**
```bash
# Recommended: Skip Statcast initially, load it later if needed
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2000 \
  --end-year 2026 \
  --skip-statcast

# Later, if you want Statcast for recent years only
uv run python scripts/mlb/ingest_historical_backfill.py \
  --start-year 2015 \
  --end-year 2026 \
  --skip-rosters \
  --skip-teams-games \
  --skip-standings \
  --skip-schedule \
  --skip-players \
  --skip-venues
```

---

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

### `mlb/ingest_rosters.py` ⭐ RECOMMENDED - Start Here!
Ingest MLB team rosters (team-player mappings) for efficient player discovery.

**Why start here?**
- **99.4% fewer API calls** than game-by-game stats (30 vs 4,860+)
- Direct team-player relationships without deriving from game stats
- Includes position information for each player-team combination
- Foundation for the optimized workflow

**Usage:**
```bash
# Default: current season, all teams, parallel
uv run python scripts/mlb/ingest_rosters.py

# Specific season
uv run python scripts/mlb/ingest_rosters.py --season 2024

# Sequential mode (more stable, slower)
uv run python scripts/mlb/ingest_rosters.py --season 2024 --sequential

# Specific teams only (NYY=147, LAD=119, BOS=111)
uv run python scripts/mlb/ingest_rosters.py --season 2024 --team-ids 147,119,111

# More workers for faster processing
uv run python scripts/mlb/ingest_rosters.py --season 2024 --max-workers 10
```

**Options:**
- `--season`: Season year (default: current year)
- `--team-ids`: Comma-separated team IDs (omit for all teams)
- `--sequential`: Use sequential instead of parallel processing
- `--max-workers`: Number of concurrent workers (default: 5, max: 10)
- `--verbose`: Enable detailed logging

**Performance:** ~5-10 seconds for all 30 teams (parallel mode)

### `mlb/ingest_players.py` - Player Discovery (OPTIMIZED!)
Fetch player details using roster-based discovery (recommended) or legacy stats-based discovery.

**Recommended Usage (Roster-Based):**
```bash
# Fetch players from rosters (requires rosters to be loaded first)
uv run python scripts/mlb/ingest_players.py --season 2024

# Multiple seasons
uv run python scripts/mlb/ingest_players.py --season 2024 --season 2023 --season 2022
```

**Legacy Usage (Stats-Based - Slower):**
```bash
# Old method: query stats tables for player discovery
uv run python scripts/mlb/ingest_players.py --from-stats
```

**Options:**
- `--season`: Season(s) to fetch players for (can specify multiple times)
- `--from-stats`: Use legacy stats-based discovery (slower)
- `--player-ids`: Comma-separated player IDs for specific players
- `--verbose`: Enable detailed logging

### `mlb/daily_ingest.py` - Daily Updates (NOW WITH ROSTERS!)
Daily MLB data ingestion pipeline with automatic roster updates.

**Usage:**
```bash
# Default: current season with roster updates
uv run python scripts/mlb/daily_ingest.py

# Custom lookback window
uv run python scripts/mlb/daily_ingest.py --lookback-days 3

# Skip roster updates (if manually run recently)
uv run python scripts/mlb/daily_ingest.py --skip-rosters

# Update rosters weekly only (Mondays)
uv run python scripts/mlb/daily_ingest.py --update-rosters-weekly

# Skip Statcast (faster)
uv run python scripts/mlb/daily_ingest.py --skip-statcast
```

**Options:**
- `--season`: Season year (default: current year)
- `--lookback-days`: Days to look back for updates (default: 2)
- `--skip-rosters`: Skip roster ingestion
- `--update-rosters-weekly`: Only update rosters on Mondays
- `--skip-statcast`: Skip Statcast data ingestion
- `--game-types`: Game type filter (default: R,F,D,L,W,S)

**New in this version:**
- Step 0: Automatic roster updates (can be configured)
- Step 6: Player dimension updates from rosters
- Roster updates can be skipped or scheduled weekly

**Recommended Workflow:**
```bash
# Beginning of season: Load all rosters once
uv run python scripts/mlb/ingest_rosters.py --season 2024

# Daily: Update game stats (rosters auto-update on Mondays)
uv run python scripts/mlb/daily_ingest.py --update-rosters-weekly
```

### `mlb/ingest_teams_and_games.py`
Ingest MLB teams and games data for one or more seasons.

**Usage:**
```bash
# Default: last completed season
uv run python scripts/mlb/ingest_teams_and_games.py

# Specific season
uv run python scripts/mlb/ingest_teams_and_games.py --season 2024

# Multiple seasons
uv run python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024
```

**Options:**
- `--season`: Season year (default: last completed season)
- `--start-year`: First season to ingest
- `--end-year`: Last season to ingest (inclusive)

---

### ⚠️ DEPRECATED: `mlb/ingest_historical_player_stats.py`

**This script has been deprecated in favor of the roster-based workflow.**

**Old approach (DELETED):**
```bash
# ❌ DELETED - The old ingest_historical_player_stats.py script has been removed
# It fetched 4,860+ games per season - very inefficient!
```

**New approach (RECOMMENDED):**
```bash
# ✅ Fetch rosters (30 API calls per season)
for year in {2020..2024}; do
  uv run python scripts/mlb/ingest_rosters.py --season $year
done

# ✅ Discover and fetch players from rosters
uv run python scripts/mlb/ingest_players.py --season 2024 --season 2023 --season 2022 --season 2021 --season 2020

# ✅ Run daily ingestion for each season to get stats
for year in {2020..2024}; do
  uv run python scripts/mlb/daily_ingest.py --season $year --skip-rosters
done
```

**Why the change?**
- **99.4% fewer API calls** (30 vs 4,860+ per season)
- More reliable roster data (official team lists vs derived from game stats)
- Better position information for players
- See [docs/mlb_roster_optimization.md](../docs/mlb_roster_optimization.md) for full details

---

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
