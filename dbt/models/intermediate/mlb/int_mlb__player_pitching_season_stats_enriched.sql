{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb", "player_season", "pitching"]
  )
-}}

-- Intermediate enriched player pitching season statistics
-- Combines Statcast metrics with traditional pitching stats and team context
-- Adds percentile rankings for MLB Savant-style analytics

with pitching_stats as (

    select * from {{ ref('int_mlb__player_pitching_stats_enriched') }}

),

games as (

    select * from {{ ref('int_mlb__games_enriched') }}

),

-- Get player-team-season combinations from pitching stats
player_team_seasons as (

    select
        ps.player_id,
        ps.team_id,
        g.season,
        count(distinct ps.game_id) as games_pitched,

        -- Core counting stats
        sum(ps.innings_pitched_decimal) as innings_pitched,
        sum(ps.hits) as hits_allowed,
        sum(ps.runs) as runs_allowed,
        sum(ps.earned_runs) as earned_runs_allowed,
        sum(ps.walks) as walks_allowed,
        sum(ps.strikeouts) as strikeouts,
        sum(ps.home_runs) as home_runs_allowed,
        sum(ps.pitches) as total_pitches,
        sum(ps.strikes) as total_strikes,

        -- Quality starts
        countif(ps.is_quality_start) as quality_starts,

        -- Statcast metrics (averages weighted by pitches thrown)
        safe_divide(
            sum(ps.avg_pitch_velocity * ps.statcast_pitches),
            sum(ps.statcast_pitches)
        ) as avg_pitch_velocity,
        max(ps.max_pitch_velocity) as max_pitch_velocity,
        safe_divide(
            sum(ps.avg_spin_rate * ps.statcast_pitches),
            sum(ps.statcast_pitches)
        ) as avg_spin_rate,
        max(ps.max_spin_rate) as max_spin_rate,
        safe_divide(
            sum(ps.avg_extension * ps.statcast_pitches),
            sum(ps.statcast_pitches)
        ) as avg_extension,
        safe_divide(
            sum(ps.pitches_in_zone),
            sum(ps.statcast_pitches)
        ) as zone_rate,
        sum(ps.called_strikes) as total_called_strikes,
        sum(ps.swinging_strikes) as total_swinging_strikes,
        sum(ps.balls_in_play) as total_balls_in_play,
        sum(ps.balls_thrown) as total_balls

    from pitching_stats as ps
    inner join games as g
        on ps.game_id = g.game_id
    where g.season is not null
    group by 1, 2, 3

),

-- For players who changed teams, get their primary team (most games pitched)
player_primary_team_season as (

    select
        player_id,
        season,
        team_id as primary_team_id,
        games_pitched as primary_team_games,
        innings_pitched,
        hits_allowed,
        runs_allowed,
        earned_runs_allowed,
        walks_allowed,
        strikeouts,
        home_runs_allowed,
        total_pitches,
        total_strikes,
        quality_starts,
        avg_pitch_velocity,
        max_pitch_velocity,
        avg_spin_rate,
        max_spin_rate,
        avg_extension,
        zone_rate,
        total_called_strikes,
        total_swinging_strikes,
        total_balls_in_play,
        total_balls,
        row_number() over (
            partition by player_id, season
            order by games_pitched desc, innings_pitched desc
        ) as team_rank
    from player_team_seasons

),

-- Calculate season-level rate stats
season_metrics as (

    select
        player_id,
        primary_team_id as team_id,
        season,

        -- Game counts
        primary_team_games as games_pitched,

        -- Counting stats
        innings_pitched,
        hits_allowed,
        runs_allowed,
        earned_runs_allowed,
        walks_allowed,
        strikeouts,
        home_runs_allowed,
        total_pitches,
        total_strikes,
        quality_starts,

        -- ERA = (Earned Runs / Innings Pitched) * 9
        safe_divide(earned_runs_allowed, innings_pitched) * 9 as era,

        -- WHIP = (Walks + Hits) / Innings Pitched
        safe_divide(
            walks_allowed + hits_allowed,
            innings_pitched
        ) as whip,

        -- K/9 = (Strikeouts / Innings Pitched) * 9
        safe_divide(strikeouts, innings_pitched) * 9 as k_per_9,

        -- BB/9 = (Walks / Innings Pitched) * 9
        safe_divide(walks_allowed, innings_pitched) * 9 as bb_per_9,

        -- HR/9 = (Home Runs / Innings Pitched) * 9
        safe_divide(home_runs_allowed, innings_pitched) * 9 as hr_per_9,

        -- H/9 = (Hits / Innings Pitched) * 9
        safe_divide(hits_allowed, innings_pitched) * 9 as h_per_9,

        -- K/BB ratio
        safe_divide(strikeouts, walks_allowed) as k_bb_ratio,

        -- Strike percentage
        safe_divide(total_strikes, total_pitches) as strike_pct,

        -- FIP = ((13*HR)+(3*BB)-(2*K))/IP + 3.2
        safe_divide(
            ((13.0 * home_runs_allowed) + (3.0 * walks_allowed) - (2.0 * strikeouts)),
            innings_pitched
        ) + 3.2 as fip,

        -- K% = Strikeouts / Batters Faced (estimated)
        -- Estimate batters faced: (IP * 3) + H + BB
        safe_divide(
            strikeouts,
            (innings_pitched * 3) + hits_allowed + walks_allowed
        ) * 100 as k_percentage,

        -- BB% = Walks / Batters Faced (estimated)
        safe_divide(
            walks_allowed,
            (innings_pitched * 3) + hits_allowed + walks_allowed
        ) * 100 as bb_percentage,

        -- Quality start percentage
        safe_divide(quality_starts, primary_team_games) * 100 as quality_start_pct,

        -- Statcast metrics
        avg_pitch_velocity,
        max_pitch_velocity,
        avg_spin_rate,
        max_spin_rate,
        avg_extension,
        zone_rate * 100 as zone_percentage,

        -- Swinging strike rate
        safe_divide(total_swinging_strikes, total_pitches) * 100 as swinging_strike_rate,

        -- Called strike rate
        safe_divide(total_called_strikes, total_pitches) * 100 as called_strike_rate

    from player_primary_team_season
    where team_rank = 1  -- Only primary team

),

-- Calculate league averages for WAR calculation
league_averages as (

    select
        season,
        avg(era) as league_avg_era,
        avg(fip) as league_avg_fip
    from season_metrics
    group by season

),

-- Add WAR calculations
with_war as (

    select
        sm.*,
        la.league_avg_era,
        la.league_avg_fip,

        -- Simplified pitching WAR calculation
        -- WAR ≈ ((league_FIP - player_FIP) / 9) * (IP / 10)
        -- Using FIP instead of ERA for a defense-independent measure
        safe_divide(
            (la.league_avg_fip - sm.fip) * sm.innings_pitched,
            90
        ) as simplified_pitching_war

    from season_metrics as sm
    left join league_averages as la
        on sm.season = la.season

),

-- Add percentile rankings
enriched as (

    select
        *,

        -- Percentile rankings (0-100 scale like MLB Savant)
        -- Lower is better for ERA, WHIP, etc.
        (100 - percent_rank() over (
            partition by season
            order by era
        ) * 100) as era_percentile,

        (100 - percent_rank() over (
            partition by season
            order by whip
        ) * 100) as whip_percentile,

        (100 - percent_rank() over (
            partition by season
            order by fip
        ) * 100) as fip_percentile,

        -- Higher is better for K/9, K%, velocity
        percent_rank() over (
            partition by season
            order by k_per_9
        ) * 100 as k_per_9_percentile,

        percent_rank() over (
            partition by season
            order by k_percentage
        ) * 100 as k_percentage_percentile,

        percent_rank() over (
            partition by season
            order by avg_pitch_velocity
        ) * 100 as velocity_percentile,

        percent_rank() over (
            partition by season
            order by max_pitch_velocity
        ) * 100 as max_velocity_percentile,

        percent_rank() over (
            partition by season
            order by avg_spin_rate
        ) * 100 as spin_rate_percentile,

        percent_rank() over (
            partition by season
            order by swinging_strike_rate
        ) * 100 as whiff_rate_percentile,

        percent_rank() over (
            partition by season
            order by k_bb_ratio
        ) * 100 as k_bb_ratio_percentile,

        -- Lower is better for BB/9, BB%
        (100 - percent_rank() over (
            partition by season
            order by bb_per_9
        ) * 100) as bb_per_9_percentile,

        (100 - percent_rank() over (
            partition by season
            order by bb_percentage
        ) * 100) as bb_percentage_percentile,

        -- WAR percentile (higher is better)
        percent_rank() over (
            partition by season
            order by simplified_pitching_war
        ) * 100 as war_percentile

    from with_war
    where innings_pitched >= 10  -- Minimum innings filter for meaningful stats

)

select * from enriched
