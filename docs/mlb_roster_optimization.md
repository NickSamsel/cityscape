# MLB Data Pipeline Optimization Guide

## Overview

This document outlines the optimization of the MLB data ingestion pipeline to reduce API calls and improve efficiency by leveraging roster data for player discovery.

## Problem Statement

The original pipeline had significant redundancies:

### Before Optimization

1. **Player Stats Fetching**: Made one API call per game to get player stats
   - Full season: 30 teams × 162 games = **4,860+ API calls**
   - Each call to `get_player_game_stats(game_id)`

2. **No Roster Data**: Team-player relationships were derived from game stats in dbt
   - Inefficient team affiliation logic
   - Complex "primary team" calculations for mid-season trades

3. **Individual Player Fetching**: Sequential calls for each player
   - Query BigQuery for unique player IDs from stats
   - Call `get_player_info(player_id)` for each (~1,000+ calls)

### After Optimization

1. **Roster-Based Discovery**: Fetch rosters first
   - **30 API calls** (one per team)
   - Provides team_id ↔ player_id mappings directly
   - Includes position information

2. **Efficient Player Discovery**: Use rosters instead of stats
   - Query single table (raw.mlb_rosters)
   - Direct team affiliations
   - Position context included

3. **Selective Stats Fetching**: Only fetch needed game data
   - Recent games for daily updates
   - Historical backfills when necessary

## Architecture

### New Ingestion Flow

```
1. Ingest Rosters (30 API calls)
   └─> scripts/mlb/ingest_rosters.py
   └─> raw.mlb_rosters

2. Discover Players from Rosters
   └─> Query raw.mlb_rosters for unique player_ids
   └─> Fetch player details in parallel
   └─> raw.mlb_players

3. Selective Game Stats
   └─> Only recent games (daily updates)
   └─> raw.mlb_player_batting_stats
   └─> raw.mlb_player_pitching_stats

4. dbt Transformations
   └─> stg_mlb__rosters
   └─> int_mlb__rosters_enriched
   └─> Enriched marts with roster context
```

## New Components

### 1. Roster Ingestion

**File**: `src/automations/ingest/mlb/rosters.py`

```python
from src.automations.ingest.mlb import ingest_mlb_rosters_bigquery

# Ingest all team rosters for a season
entries = ingest_mlb_rosters_bigquery(
    season=2024,
    parallel=True,
    max_workers=5
)
```

**Script**: `scripts/mlb/ingest_rosters.py`

```bash
# Ingest all teams for current season
python scripts/mlb/ingest_rosters.py

# Specific season
python scripts/mlb/ingest_rosters.py --season 2024

# Specific teams only
python scripts/mlb/ingest_rosters.py --season 2024 --team-ids 147,119,111
```

### 2. Roster-Based Player Discovery

**File**: `src/automations/ingest/mlb/players.py`

```python
from src.automations.ingest.mlb import ingest_players_from_rosters

# More efficient: uses rosters for discovery
players = ingest_players_from_rosters(season=2024)

# Old way: uses game stats for discovery (less efficient)
# players = ingest_players_from_stats()
```

### 3. dbt Models

**Staging**: `dbt/models/staging/mlb/stg_mlb__rosters.sql`
- Clean view of raw roster data

**Intermediate**: `dbt/models/intermediate/mlb/int_mlb__rosters_enriched.sql`
- Enriched with team and player context
- Position groupings
- Tenure calculations
- Field/pitcher classifications

## Usage Examples

### Daily Ingestion Pattern (Recommended)

```bash
# 1. Update rosters (beginning of season or weekly)
python scripts/mlb/ingest_rosters.py --season 2024

# 2. Update players from rosters (weekly or when rosters change)
python scripts/mlb/ingest_players.py --from-rosters --season 2024

# 3. Daily game stats (only recent games)
python scripts/mlb/daily_ingest.py --lookback-days 2
```

### Historical Backfill Pattern

```bash
# 1. Ingest rosters for all seasons
for year in {2020..2024}; do
  python scripts/mlb/ingest_rosters.py --season $year
done

# 2. Discover and fetch all players
for year in {2020..2024}; do
  python scripts/mlb/ingest_players.py --from-rosters --season $year
done

# 3. Backfill game data
python scripts/mlb/ingest_teams_and_games.py --start-year 2020 --end-year 2024 --parallel
```

## Performance Comparison

### API Calls for Full 2024 Season

| Operation | Before | After | Improvement |
|-----------|--------|-------|-------------|
| Team-Player Mapping | 4,860+ game stats | 30 rosters | **99.4% reduction** |
| Player Discovery | 2 BigQuery queries | 1 BigQuery query | **50% reduction** |
| Player Info Fetching | Sequential | Sequential | Same (API limitation) |
| **Total API Calls** | **~6,000+** | **~1,200** | **~80% reduction** |

### Time Savings

Rough estimates for full season ingestion:

- **Before**: ~8-12 hours (game-by-game player stats)
- **After**: ~2-3 hours (roster-based + selective games)
- **Savings**: ~75% faster

## Database Schema

### raw.mlb_rosters

```sql
CREATE TABLE raw.mlb_rosters (
  team_id STRING NOT NULL,
  player_id STRING NOT NULL,
  season INT64 NOT NULL,
  player_name STRING NOT NULL,
  position_code STRING,
  position_name STRING,
  position_abbr STRING,
  raw STRING NOT NULL,
  loaded_at TIMESTAMP NOT NULL,
  PRIMARY KEY (team_id, player_id, season)
);
```

## Using Rosters in dbt

### Example: Player-Team Analysis

```sql
-- Get all players for a specific team and season
with yankees_2024 as (
  select *
  from {{ ref('int_mlb__rosters_enriched') }}
  where team_abbr = 'NYY'
    and season = 2024
)

select
  full_name,
  position_group,
  seasons_since_debut,
  bat_side_description,
  pitch_hand_description
from yankees_2024
order by position_group, full_name
```

### Example: Team Composition Analysis

```sql
-- Analyze roster composition by position
select
  season,
  team_abbr,
  position_group,
  count(*) as player_count,
  count(distinct player_id) as unique_players
from {{ ref('int_mlb__rosters_enriched') }}
where season = 2024
group by 1, 2, 3
order by season, team_abbr, position_group
```

## Migration Steps

For existing pipelines:

1. **Add Roster Ingestion** (backwards compatible)
   ```bash
   python scripts/mlb/ingest_rosters.py --season 2024
   ```

2. **Update Player Ingestion** (optional, both methods work)
   ```python
   # New way (recommended)
   ingest_players_from_rosters(season=2024)
   
   # Old way (still supported)
   ingest_players_from_stats()
   ```

3. **Update dbt Models** (as needed)
   - Use `int_mlb__rosters_enriched` for team-player relationships
   - Simplify existing player-team join logic

4. **Run dbt**
   ```bash
   dbt run --select stg_mlb__rosters+ int_mlb__rosters_enriched+
   ```

## Best Practices

1. **Roster Ingestion Frequency**
   - Full season: Once at start of season
   - Updates: Weekly during season (roster changes)
   - Off-season: As needed for rule 5 draft, trades, etc.

2. **Error Handling**
   - Roster API calls are robust (team-level, not game-level)
   - Failed team fetches are logged but don't fail entire run
   - Parallel processing recommended (5-10 workers)

3. **Data Freshness**
   - Rosters updated before player info fetching
   - Player stats still fetched daily for recent games
   - Historical data remains unchanged

## Troubleshooting

### Issue: Missing Players in Roster

**Symptom**: Player appears in game stats but not in roster table

**Cause**: Player traded mid-season or called up after roster snapshot

**Solution**: Re-run roster ingestion for that team/season
```bash
python scripts/mlb/ingest_rosters.py --season 2024 --team-ids 147
```

### Issue: Roster Position Differs from Player Primary Position

**Symptom**: Player has position "OF" in roster but primary position is "CF"

**Cause**: Rosters use more general position codes vs player's primary position

**Solution**: This is expected. Use:
- `position_code` from roster for that team/season
- `primary_position_code` from player table for career position

## Future Enhancements

1. **Roster History Tracking**: Track position changes within season
2. **Injury List Integration**: Mark IL players in roster data
3. **Minor League Rosters**: Extend to farm system (if needed)
4. **Transaction Log**: Track trades, signings, releases

## Questions & Support

For questions about roster data or optimization strategies, refer to:
- MLB Stats API Documentation
- `docs/mlb/` directory for model-specific docs
- Team discussions on data architecture
