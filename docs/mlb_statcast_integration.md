# MLB Statcast Integration

This integration adds comprehensive MLB Statcast data to the cityscape analytics platform, enabling advanced player analysis with pitch-level and batted-ball metrics.

## Features

### 🎯 What's New

- **Pitch-Level Metrics**: Track velocity, spin rate, pitch types, and location for every pitch
- **Batted Ball Analytics**: Exit velocity, launch angle, and barrel rates for every ball in play
- **Player Fact Table**: `fct_mlb__players` mart combining biographical data, career stats, and Statcast metrics
- **Advanced Metrics**: 
  - Average/max pitch velocity and spin rate by pitcher
  - Exit velocity, hard-hit rate, and barrel rate by batter
  - Launch angle and spray chart data
  - Sprint speed and defensive metrics

## Getting Started

### 1. Ingest Statcast Data

```bash
# Ingest Statcast data for the current season (default: 5 parallel workers)
python scripts/mlb/ingest_statcast_data.py --season 2024

# Faster with more parallel workers (recommended: 8-10 for good bandwidth)
python scripts/mlb/ingest_statcast_data.py --season 2024 --max-workers 10

# Conservative mode for low memory/bandwidth
python scripts/mlb/ingest_statcast_data.py --season 2024 --max-workers 3 --batch-size 50

# Ingest for specific date range
python scripts/mlb/ingest_statcast_data.py --season 2024 --start-date 2024-06-01 --end-date 2024-06-30

# Ingest for specific games
python scripts/mlb/ingest_statcast_data.py --game-ids 717612,717613,717614 --max-workers 10
```

### 2. Run dbt Models

```bash
# Build all models
cd dbt && dbt build

# Build just Statcast staging models
dbt build --select stg_mlb__statcast*

# Build just the player fact table
dbt build --select fct_mlb__players
```

### 3. Query the Data

```sql
-- Find players with highest average exit velocity (min 50 batted balls)
SELECT 
    full_name,
    primary_position_name,
    avg_exit_velocity,
    max_exit_velocity,
    hard_hit_rate,
    barrel_rate,
    career_home_runs
FROM mlb_marts.fct_mlb__players
WHERE total_batted_balls >= 50
ORDER BY avg_exit_velocity DESC
LIMIT 20;

-- Find hardest throwing pitchers
SELECT 
    full_name,
    primary_position_name,
    avg_release_speed,
    max_release_speed,
    avg_spin_rate,
    primary_pitch_type,
    primary_pitch_description,
    primary_pitch_avg_speed,
    career_era
FROM mlb_marts.fct_mlb__players
WHERE statcast_pitches >= 100
ORDER BY avg_release_speed DESC
LIMIT 20;

-- Two-way players analysis
SELECT 
    full_name,
    years_experience,
    -- Batting
    career_batting_avg,
    career_home_runs,
    avg_exit_velocity,
    -- Pitching
    career_era,
    avg_release_speed,
    primary_pitch_type
FROM mlb_marts.fct_mlb__players
WHERE is_two_way_player = true
ORDER BY years_experience DESC;
```

## Data Models

### Raw Tables
- `raw.mlb_statcast_pitches` - Pitch-level data with velocity, spin, location
- `raw.mlb_statcast_batted_balls` - Batted ball data with exit velo, launch angle

### Staging Models
- `stg_mlb__statcast_pitches` - Cleaned pitch data
- `stg_mlb__statcast_batted_balls` - Cleaned batted ball data

### Intermediate Models
- `int_mlb__pitcher_statcast_metrics` - Aggregated pitcher metrics
- `int_mlb__batter_statcast_metrics` - Aggregated batter metrics
- `int_mlb__career_batting_stats` - Career batting totals
- `int_mlb__career_pitching_stats` - Career pitching totals

### Marts
- `fct_mlb__players` - **Comprehensive player fact table** with all metrics

## Key Metrics Explained

### Batting Metrics

- **Exit Velocity**: Speed of the ball off the bat (mph)
- **Launch Angle**: Vertical angle of the ball off the bat (degrees)
- **Barrel**: Optimal contact (98+ mph exit velo, 26-30° launch angle)
- **Hard Hit**: Batted ball with 95+ mph exit velocity
- **Sprint Speed**: Runner's speed in feet per second

### Pitching Metrics

- **Release Speed**: Pitch velocity (mph)
- **Spin Rate**: Pitch rotation rate (RPM)
- **Release Extension**: Distance from rubber to release point (feet)
- **Zone %**: Percentage of pitches in the strike zone
- **Primary Pitch**: Most frequently thrown pitch type

### Career Stats

- **Traditional**: AVG, OBP, SLG, OPS, ERA, WHIP, K/9, BB/9
- **Advanced**: Strikeout rate, walk rate, K/BB ratio

## Architecture

```
MLB Stats API (play-by-play endpoints)
           ↓
Python Client (src/integrations/mlb/client.py)
           ↓
Ingestion Script (scripts/mlb/ingest_statcast_data.py)
           ↓
BigQuery Raw Tables (raw.mlb_statcast_*)
           ↓
dbt Staging Models (stg_mlb__statcast_*)
           ↓
dbt Intermediate Models (int_mlb__*_metrics)
           ↓
dbt Marts (fct_mlb__players) ← **Analytics-ready!**
```

## Scheduled Updates

To keep Statcast data current, schedule regular ingestion:

```bash
# Daily update (last 3 days to catch late updates, with parallel processing)
python scripts/mlb/ingest_statcast_data.py --season 2024 --lookback-days 3 --max-workers 8

# Weekly full refresh (faster with more workers)
python scripts/mlb/ingest_statcast_data.py --season 2024 --max-workers 10
```

## Performance Characteristics

### Parallel Processing (NEW!)

- **5 workers (default)**: ~30-60 seconds per 100 games
- **10 workers**: ~15-30 seconds per 100 games  
- **Full 2024 season** (~2,469 games): 
  - 5 workers: ~12-30 minutes
  - 10 workers: ~6-15 minutes

### Batch Processing

- **100 games/batch (default)**: ~200-300 MB memory per batch
- **50 games/batch**: More BigQuery writes, slightly slower
- **200 games/batch**: Faster but uses more memory

### Recommendations

- **Good bandwidth + 4GB+ RAM**: `--max-workers 10 --batch-size 100`
- **Limited bandwidth**: `--max-workers 3 --batch-size 100`
- **Low memory (<2GB)**: `--max-workers 3 --batch-size 50`
- **Rate limit issues**: Reduce `--max-workers` to 3-5

## Troubleshooting

**Issue: No Statcast data returned**
- Statcast data only available for recent games (2015+)
- Some games may not have complete Statcast coverage
- Check game IDs are valid and games are completed

**Issue: Process killed with exit code 143**
- Out of memory (OOM) - reduce `--batch-size` to 50
- Or reduce `--max-workers` to free up memory
- Process in smaller date ranges

**Issue: Slow ingestion**
- Increase `--max-workers` (try 8-10 for good bandwidth)
- Check network connection speed
- API may be experiencing high load

**Issue: Rate limiting or connection errors**
- Reduce `--max-workers` to 3-5
- Add delays between batches
- Process during off-peak hours

**Issue: Missing metrics in fct_players**
- Ensure player has sufficient data (thresholds: 50 batted balls, 100 pitches)
- Check intermediate models are built successfully
- Verify joins on player_id are working

**Issue: High memory usage**
- Reduce `--batch-size` (try 50 instead of 100)
- Reduce `--max-workers` (fewer concurrent API calls)
- Process season in monthly chunks using date filters

## Next Steps

1. **Enhance with more metrics**: Add expected stats (xBA, xwOBA)
2. **Historical analysis**: Compare current vs. career trends
3. **Comparative analysis**: Benchmark players against league averages
4. **Visualization**: Build dashboards with exit velo and pitch movement charts
5. **Predictive modeling**: Use Statcast data for performance predictions

## References

- [MLB Stats API Documentation](https://github.com/toddrob99/MLB-StatsAPI)
- [Statcast Glossary](https://www.mlb.com/glossary/statcast)
- [Baseball Savant](https://baseballsavant.mlb.com/)
