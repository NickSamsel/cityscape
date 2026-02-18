# MLB Statcast dbt Infrastructure

## Overview
This document outlines the complete dbt infrastructure for MLB Statcast data and provides guidance on joins, enrichment patterns, and analytical use cases.

## Architecture Layers

### 1. Staging Layer (`stg_mlb__*`)
**Purpose:** Clean and standardize raw data with type casting only

- `stg_mlb__statcast_pitches` - Individual pitch records (740K+ pitches/season)
- `stg_mlb__statcast_batted_balls` - Individual batted ball records (250K+ balls/season)

**Pattern:** Minimal transformation, incremental based on `loaded_at`, unique on `play_id`

### 2. Intermediate Layer (`int_mlb__*`)

#### Enriched Individual Records
**Purpose:** Add game, player, and team context to each record

- `int_mlb__statcast_pitches_enriched` - Every pitch with complete context
  - Joins: games, pitchers (players), batters (players), home teams, away teams
  - Enrichments: pitcher/batter age, experience years, handedness matchups
  - Derived metrics: velocity tiers, spin tiers, count descriptions
  
- `int_mlb__statcast_batted_balls_enriched` - Every batted ball with complete context
  - Joins: games, batters (players), pitchers (players), home teams, away teams
  - Enrichments: batter/pitcher age, experience years, handedness matchups
  - Derived metrics: exit velo tiers, trajectory buckets, quality contact classifications

#### Aggregated Player Metrics
**Purpose:** Roll up individual records to player-level statistics

- `int_mlb__pitcher_statcast_metrics` - Pitcher arsenal metrics
  - Aggregates: avg/max velocity, spin rate, zone %, primary pitch type
  - Grain: One row per pitcher (across all games)
  
- `int_mlb__batter_statcast_metrics` - Batter quality of contact metrics
  - Aggregates: avg/max exit velo, barrel rate, hard-hit rate, launch angle
  - Grain: One row per batter (across all games)

#### Career Statistics
- `int_mlb__career_batting_stats` - Career batting totals (AVG, OBP, SLG, OPS)
- `int_mlb__career_pitching_stats` - Career pitching totals (ERA, WHIP, K/9, BB/9)

### 3. Marts Layer (`fct_mlb__*`, `dim_mlb__*`)
**Purpose:** Analytics-ready tables for BI tools

#### Fact Tables
- `fct_mlb__statcast_pitches` - Pitch-level analysis
- `fct_mlb__statcast_batted_balls` - Batted ball analysis
- `fct_mlb__player_batting_stats` - Game-level batting performance
- `fct_mlb__player_pitching_stats` - Game-level pitching performance
- `fct_mlb__games` - Game-level results
- **`fct_mlb__players`** - Comprehensive player profiles (THE KEY TABLE!)

#### Dimension Tables
- `dim_mlb__players` - Player biographical data
- `dim_mlb__teams` - Team information by season
- `dim_mlb__leagues` - League reference data
- `dim_mlb__divisions` - Division reference data

---

## Key Join Patterns

### Pattern 1: Player Profile Enrichment (`fct_mlb__players`)
**Use Case:** Create comprehensive player profiles with career stats + Statcast metrics

```sql
-- Already implemented in fct_mlb__players
players (biographical)
  LEFT JOIN career_batting (aggregated traditional stats)
  LEFT JOIN career_pitching (aggregated traditional stats)
  LEFT JOIN batter_statcast (aggregated Statcast metrics)
  LEFT JOIN pitcher_statcast (aggregated Statcast metrics)
```

**Grain:** One row per player
**Key Fields:**
- Player demographics (name, age, position, handedness)
- Career totals (games, at-bats, hits, HRs, ERA, strikeouts)
- Statcast averages (exit velo, launch angle, pitch velocity, spin rate)
- Derived flags (is_batter, is_pitcher, is_two_way_player)

**Analytics Use Cases:**
- Player scouting reports
- Free agent evaluation
- Trade analysis
- Fantasy baseball rankings
- Player type segmentation (power hitters, contact hitters, velocity pitchers)

### Pattern 2: Game-Level Performance with Statcast Context
**Use Case:** Evaluate individual game performances with quality of contact metrics

```sql
-- For batters
fct_mlb__player_batting_stats (game-level traditional stats)
  LEFT JOIN (
    SELECT 
      game_id,
      batter_id,
      AVG(launch_speed) as avg_exit_velo,
      MAX(launch_speed) as max_exit_velo,
      AVG(launch_angle) as avg_launch_angle,
      COUNTIF(is_barrel) as barrels,
      COUNTIF(is_hard_hit) as hard_hits
    FROM fct_mlb__statcast_batted_balls
    GROUP BY game_id, batter_id
  ) statcast_summary
  ON batting_stats.game_id = statcast_summary.game_id
  AND batting_stats.player_id = statcast_summary.batter_id
```

**Analytics Use Cases:**
- "Player went 0-4 but had 3 barrels" (unlucky)
- Regression analysis (expected vs actual outcomes)
- Hot/cold streak validation with underlying metrics
- Daily fantasy sports projections

### Pattern 3: Pitch Arsenal Analysis
**Use Case:** Study pitcher effectiveness by pitch type and sequencing

```sql
-- Pitcher effectiveness by pitch type
SELECT
  pitcher_id,
  pitcher_name,
  pitch_type,
  pitch_type_description,
  COUNT(*) as pitches_thrown,
  AVG(release_speed) as avg_velocity,
  AVG(release_spin_rate) as avg_spin_rate,
  COUNTIF(in_strike_zone) / COUNT(*) as zone_pct,
  COUNTIF(pitch_result = 'X') as balls_in_play,
  COUNTIF(pitch_result = 'W') as swinging_strikes
FROM fct_mlb__statcast_pitches
WHERE season = 2024
GROUP BY pitcher_id, pitcher_name, pitch_type, pitch_type_description
```

**Analytics Use Cases:**
- Pitch mix optimization
- Platoon advantage analysis (vs LHB/RHB)
- Count leverage (what pitches in 0-2, 3-2 counts)
- Injury detection (velocity drops)
- Pitch development tracking

### Pattern 4: Matchup Analysis
**Use Case:** Historical pitcher vs batter performance with Statcast depth

```sql
-- Head-to-head matchup history
WITH h2h_pitches AS (
  SELECT
    pitcher_id,
    pitcher_name,
    batter_id,
    batter_name,
    COUNT(*) as pitches_seen,
    AVG(release_speed) as avg_velocity,
    COUNTIF(pitch_result = 'X') as balls_in_play,
    COUNTIF(pitch_result = 'W') as swinging_strikes
  FROM fct_mlb__statcast_pitches
  WHERE pitcher_id = 123 AND batter_id = 456
  GROUP BY 1,2,3,4
),
h2h_batted_balls AS (
  SELECT
    pitcher_id,
    batter_id,
    COUNT(*) as batted_balls,
    AVG(launch_speed) as avg_exit_velo,
    AVG(launch_angle) as avg_launch_angle,
    COUNTIF(is_barrel) as barrels,
    COUNTIF(is_home_run) as home_runs
  FROM fct_mlb__statcast_batted_balls
  WHERE pitcher_id = 123 AND batter_id = 456
  GROUP BY 1,2
)
SELECT
  p.*,
  bb.* EXCEPT(pitcher_id, batter_id)
FROM h2h_pitches p
LEFT JOIN h2h_batted_balls bb USING(pitcher_id, batter_id)
```

**Analytics Use Cases:**
- Pre-game betting analysis
- Lineup optimization
- Pinch-hitting decisions
- Platoon advantage exploitation

### Pattern 5: Ballpark and Environmental Effects
**Use Case:** Study how park factors and conditions affect outcomes

```sql
-- Exit velo vs outcomes by park
SELECT
  bb.game_id,
  bb.home_team_name,
  bb.away_team_name,
  bb.exit_velo_tier,
  COUNT(*) as batted_balls,
  COUNTIF(is_hit) as hits,
  COUNTIF(is_home_run) as home_runs,
  AVG(launch_distance) as avg_distance
FROM fct_mlb__statcast_batted_balls bb
WHERE season = 2024
GROUP BY 1,2,3,4
```

**Analytics Use Cases:**
- Park-adjusted player evaluation
- Weather impact studies
- Home field advantage quantification
- Optimal ballpark for player type

---

## Best Practices for Enrichment

### When to Use Enriched vs Aggregated Models

**Use Enriched Individual Records (`int_mlb__statcast_*_enriched`) When:**
- Need pitch-by-pitch or ball-by-ball granularity
- Analyzing specific at-bats or game situations
- Building ML models with pitch sequences
- Studying in-game adjustments
- Large query volumes (pre-joined data is faster)

**Use Aggregated Metrics (`int_mlb__*_statcast_metrics`) When:**
- Player-level comparisons across season
- Joining to `fct_mlb__players` for complete profiles
- Dashboard KPIs (overall season stats)
- Rank/percentile calculations
- Smaller result sets needed

### Performance Optimization

**Incremental Models:**
All models use incremental materialization with `loaded_at` filtering to avoid full table scans.

**Partitioning Strategy:**
- Pitch/batted ball tables: Partition by `game_date`
- Player aggregations: No partition (manageable size)
- Queries should filter on `season` or `game_date` when possible

**Join Optimization:**
- Player joins use `CAST(player_id AS INT64)` for consistency
- Team joins require both `team_id` AND `season` (teams change leagues/divisions)
- Game joins are 1:1 on `game_id`

### Data Quality Considerations

**NULL Handling:**
- Many Statcast metrics can be NULL (data not captured for all plays)
- Use `COALESCE()` or `IFNULL()` for aggregations
- `sprint_speed` is rarely populated (requires certain play types)

**Barrel Definition:**
- 98+ mph exit velo AND 26-30° launch angle
- Barrels typically result in .500 BA and 1.500 SLG
- Use `is_barrel` flag rather than recalculating

**Hard Hit Definition:**
- 95+ mph exit velocity
- Good predictor of batter skill (less luck-dependent than BA)

---

## Common Analytical Queries

### Top Power Hitters (Exit Velocity Leaders)
```sql
SELECT
  batter_name,
  total_batted_balls,
  avg_exit_velocity,
  max_exit_velocity,
  barrel_rate,
  hard_hit_rate
FROM fct_mlb__players
WHERE total_batted_balls >= 100  -- Min batted balls for sample size
ORDER BY avg_exit_velocity DESC
LIMIT 20
```

### Elite Velocity Pitchers
```sql
SELECT
  full_name as pitcher_name,
  statcast_pitches as pitches_thrown,
  avg_release_speed,
  max_release_speed,
  primary_pitch_type,
  primary_pitch_avg_speed,
  avg_spin_rate
FROM fct_mlb__players
WHERE statcast_pitches >= 500  -- Min pitches for sample size
ORDER BY avg_release_speed DESC
LIMIT 20
```

### Two-Way Players (Ohtani Analysis)
```sql
SELECT
  full_name,
  is_two_way_player,
  -- Batting
  career_games_batted,
  career_batting_avg,
  career_home_runs,
  avg_exit_velocity,
  hard_hit_rate,
  -- Pitching
  career_games_pitched,
  career_era,
  career_k_per_9,
  avg_release_speed,
  zone_percentage
FROM fct_mlb__players
WHERE is_two_way_player = TRUE
```

### Pitch Type Effectiveness (By Pitcher)
```sql
SELECT
  p.pitcher_name,
  p.pitch_type,
  p.pitch_type_description,
  COUNT(*) as pitches,
  AVG(p.release_speed) as avg_velo,
  AVG(p.release_spin_rate) as avg_spin,
  COUNTIF(p.in_strike_zone) / COUNT(*) as zone_rate,
  -- Join to batted balls for outcomes
  COUNTIF(bb.is_barrel) as barrels_allowed,
  COUNTIF(bb.is_hard_hit) as hard_hits_allowed
FROM fct_mlb__statcast_pitches p
LEFT JOIN fct_mlb__statcast_batted_balls bb
  ON p.play_id = bb.play_id
WHERE p.season = 2024
GROUP BY 1,2,3
HAVING pitches >= 50
ORDER BY barrels_allowed DESC
```

---

## Key Metrics Glossary

### Batting Metrics
- **Exit Velocity**: Speed off the bat (mph). Elite: 110+, Average: 90
- **Launch Angle**: Vertical trajectory (degrees). Optimal: 25-35° for HRs
- **Barrel**: 98+ mph exit velo + 26-30° launch angle. ~.500 BA, 1.500 SLG
- **Hard Hit**: 95+ mph exit velocity. Strong skill indicator
- **Hard-Hit Rate**: % of batted balls hit hard. Elite: 45%+, Average: 35%

### Pitching Metrics
- **Release Speed**: Pitch velocity (mph). Fastball average: 93-94 mph
- **Spin Rate**: Pitch rotation (rpm). More spin = more movement
- **Zone %**: Pitches in strike zone. Elite: 50%+, Average: 44%
- **Extension**: Release point distance (feet). More = less reaction time
- **Primary Pitch Type**: Most-thrown pitch (FF, SI, SL, CU, CH)

### Context Metrics
- **Pitcher-Batter Handedness**: Same-handed = pitcher advantage
- **Velocity Tier**: Elite/Above Avg/Average/Below Avg/Soft
- **Count Leverage**: 0-2 (pitcher advantage), 3-2 (hitter advantage)

---

## Next Steps

1. **Run initial dbt build:**
   ```bash
   dbt build --select +fct_mlb__statcast_pitches +fct_mlb__statcast_batted_balls
   ```

2. **Validate data quality:**
   ```bash
   dbt test --select fct_mlb__statcast_pitches fct_mlb__statcast_batted_balls
   ```

3. **Rebuild player profiles:**
   ```bash
   dbt run --select fct_mlb__players --full-refresh
   ```

4. **Connect BI tool:** Point Tableau/Looker/PowerBI to mart tables

5. **Build dashboards:** 
   - Player scouting report (from `fct_mlb__players`)
   - Game recap with Statcast (join game stats + aggregated Statcast)
   - Pitcher arsenal analysis (from `fct_mlb__statcast_pitches`)
   - Quality of contact trends (from `fct_mlb__statcast_batted_balls`)
