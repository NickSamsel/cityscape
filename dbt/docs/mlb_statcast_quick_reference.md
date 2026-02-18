# Statcast Data Layer Quick Reference

## Data Flow Diagram
```
Raw BigQuery Tables
    ↓
stg_mlb__statcast_pitches (740K rows)
stg_mlb__statcast_batted_balls (250K rows)
    ↓
    ├── int_mlb__statcast_pitches_enriched (with game/player context)
    │   └── fct_mlb__statcast_pitches ✅ USE FOR PITCH ANALYSIS
    │
    ├── int_mlb__statcast_batted_balls_enriched (with game/player context)
    │   └── fct_mlb__statcast_batted_balls ✅ USE FOR BATTED BALL ANALYSIS
    │
    ├── int_mlb__pitcher_statcast_metrics (aggregated by pitcher)
    │   └── fct_mlb__players (joined) ✅ USE FOR PLAYER PROFILES
    │
    └── int_mlb__batter_statcast_metrics (aggregated by batter)
        └── fct_mlb__players (joined) ✅ USE FOR PLAYER PROFILES
```

## Which Table Should I Use?

### I want to analyze...

**Individual pitches in detail (velocity, spin, location)**
→ `fct_mlb__statcast_pitches` (740K rows/season)
- Has: Every pitch with pitcher/batter/game context
- Grain: One row = one pitch
- Example: "Show me all 100+ mph fastballs thrown in 2024"

**Individual batted balls in detail (exit velo, launch angle)**
→ `fct_mlb__statcast_batted_balls` (250K rows/season)
- Has: Every batted ball with batter/pitcher/game context
- Grain: One row = one batted ball
- Example: "Show me all barrels hit to right field"

**Player career profiles with Statcast averages**
→ `fct_mlb__players` (2K rows)
- Has: Player bio + career stats + Statcast season averages
- Grain: One row = one player
- Example: "Who has the highest average exit velocity?"

**Game-level Statcast summaries**
→ Aggregate `fct_mlb__statcast_*` yourself
```sql
SELECT 
  game_id,
  pitcher_id,
  AVG(release_speed) as avg_fastball_velo,
  COUNT(*) as pitches_thrown
FROM fct_mlb__statcast_pitches
WHERE pitch_type = 'FF'
GROUP BY game_id, pitcher_id
```

**Player vs player matchups**
→ Filter `fct_mlb__statcast_pitches` or `fct_mlb__statcast_batted_balls`
```sql
WHERE pitcher_id = 123 AND batter_id = 456
```

## Quick Field Reference

### fct_mlb__statcast_pitches
| Field | Type | Description | Typical Values |
|-------|------|-------------|----------------|
| play_id | STRING | Unique pitch ID | 12345_10_5 |
| pitcher_id | INT | MLB player ID | 660271 |
| batter_id | INT | MLB player ID | 545361 |
| release_speed | FLOAT | Velocity (mph) | 85-105 |
| release_spin_rate | FLOAT | Spin (rpm) | 2000-3000 |
| zone | INT | Strike zone (1-9 in, 11+ out) | 1-14 |
| pitch_type | STRING | Pitch code | FF, SL, CU, CH, SI |
| pitcher_batter_handedness | STRING | Matchup | Same, Opposite |
| velocity_tier | STRING | Speed bucket | Elite, Average, Soft |

### fct_mlb__statcast_batted_balls
| Field | Type | Description | Typical Values |
|-------|------|-------------|----------------|
| play_id | STRING | Unique batted ball ID | 12345_10_5 |
| batter_id | INT | MLB player ID | 545361 |
| pitcher_id | INT | MLB player ID | 660271 |
| launch_speed | FLOAT | Exit velo (mph) | 50-120 |
| launch_angle | FLOAT | Angle (degrees) | -50 to 90 |
| launch_distance | FLOAT | Distance (feet) | 0-500 |
| is_barrel | BOOL | Barrel flag | true/false |
| is_hard_hit | BOOL | Hard hit (95+ mph) | true/false |
| exit_velo_tier | STRING | Exit velo bucket | Elite, Good, Weak |
| trajectory_bucket | STRING | Ball type | Fly Ball, Line Drive, Ground Ball |
| is_home_run | BOOL | HR flag | true/false |

### fct_mlb__players (Statcast columns only)
| Field | Type | Description | Good Value |
|-------|------|-------------|------------|
| **Batting Statcast** |
| total_batted_balls | INT | Sample size | 100+ |
| avg_exit_velocity | FLOAT | Avg exit velo (mph) | 90+ |
| max_exit_velocity | FLOAT | Max exit velo | 110+ |
| barrel_rate | FLOAT | Barrel % | 10%+ |
| hard_hit_rate | FLOAT | Hard-hit % | 40%+ |
| **Pitching Statcast** |
| statcast_pitches | INT | Sample size | 500+ |
| avg_release_speed | FLOAT | Avg fastball velo | 93+ |
| max_release_speed | FLOAT | Max velo | 98+ |
| avg_spin_rate | FLOAT | Avg spin (rpm) | 2300+ |
| zone_percentage | FLOAT | Zone % | 45%+ |
| primary_pitch_type | STRING | Main pitch | FF, SI, SL |

## Common Filters

```sql
-- High-quality sample sizes
WHERE total_batted_balls >= 100
WHERE statcast_pitches >= 500

-- Elite performance
WHERE avg_exit_velocity >= 92
WHERE barrel_rate >= 0.10
WHERE avg_release_speed >= 95
WHERE zone_percentage >= 0.50

-- Specific situations
WHERE count_description = '3-2'  -- Full count
WHERE pitcher_batter_handedness = 'Opposite'  -- Platoon advantage
WHERE pitch_type IN ('FF', 'SI')  -- Fastballs only
WHERE trajectory_bucket = 'Line Drive'  -- Best batted balls
WHERE is_barrel = TRUE  -- Only barrels
WHERE season = 2024  -- Latest season
```

## Performance Tips

1. **Always filter on season or game_date** for pitch/batted ball tables
2. **Join to dim_mlb__players for player names** rather than using enriched tables if you don't need game context
3. **Use aggregated metrics from fct_mlb__players** for leaderboards instead of aggregating raw pitches
4. **Limit results** - pitch tables have 740K+ rows per season

## Join Cookbook

```sql
-- Player batting stats with Statcast
SELECT 
  bs.*,
  p.avg_exit_velocity,
  p.barrel_rate
FROM fct_mlb__player_batting_stats bs
JOIN fct_mlb__players p ON bs.player_id = p.player_id
WHERE bs.season = 2024

-- Game-level Statcast summary for batters
SELECT
  g.game_id,
  g.batter_id,
  COUNT(*) as batted_balls,
  AVG(g.launch_speed) as avg_exit_velo,
  COUNTIF(g.is_barrel) as barrels
FROM fct_mlb__statcast_batted_balls g
WHERE g.season = 2024
GROUP BY g.game_id, g.batter_id

-- Pitcher arsenal breakdown
SELECT
  pitcher_name,
  pitch_type,
  COUNT(*) as thrown,
  AVG(release_speed) as avg_velo,
  AVG(release_spin_rate) as avg_spin
FROM fct_mlb__statcast_pitches
WHERE season = 2024
GROUP BY pitcher_name, pitch_type
HAVING thrown >= 50

-- Exit velo by pitch type faced
SELECT
  p.pitch_type,
  p.pitch_type_description,
  COUNT(*) as batted_balls,
  AVG(bb.launch_speed) as avg_exit_velo,
  COUNTIF(bb.is_barrel) as barrels
FROM fct_mlb__statcast_pitches p
INNER JOIN fct_mlb__statcast_batted_balls bb
  ON p.play_id = bb.play_id
WHERE p.season = 2024
GROUP BY p.pitch_type, p.pitch_type_description
ORDER BY avg_exit_velo DESC
```

## Metric Benchmarks

### Exit Velocity (mph)
- 🔥 Elite: 110+
- ⭐ Great: 100-109
- ✅ Good: 95-99
- 📊 Average: 90-94
- ⚠️ Below Average: 85-89
- 🔻 Weak: <85

### Pitch Velocity (mph)
- 🔥 Elite: 98+
- ⭐ Above Average: 95-97
- ✅ Average: 92-94
- ⚠️ Below Average: 88-91
- 🔻 Soft: <88

### Barrel Rate
- 🔥 Elite: 15%+
- ⭐ Above Average: 10-15%
- ✅ Average: 6-10%
- ⚠️ Below Average: <6%

### Hard-Hit Rate
- 🔥 Elite: 50%+
- ⭐ Above Average: 40-50%
- ✅ Average: 35-40%
- ⚠️ Below Average: <35%

### Zone %
- 🔥 Elite: 50%+
- ⭐ Above Average: 46-50%
- ✅ Average: 42-46%
- ⚠️ Below Average: <42%
