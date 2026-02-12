{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'team_id'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "team_stats"]
  )
-}}

-- Mart fact table for MLB team game-level statistics
-- Aggregates player batting and pitching stats to the team level per game
-- Each row represents a team's total performance in a single game

with games as (

    select * from {{ ref('fct_mlb__games') }}
    {% if is_incremental() %}
    where game_id not in (select distinct game_id from {{ this }})
    {% endif %}

),

batting as (

    select * from {{ ref('fct_mlb__player_batting_stats') }}

),

pitching as (

    select * from {{ ref('fct_mlb__player_pitching_stats') }}

),

-- Aggregate batting stats by team per game
team_batting as (

    select
        b.game_id,
        b.team_id,
        b.season,

        -- Counting stats
        count(distinct b.player_id) as batters_used,
        sum(b.at_bats) as at_bats,
        sum(b.hits) as hits,
        sum(b.singles) as singles,
        sum(b.doubles) as doubles,
        sum(b.triples) as triples,
        sum(b.home_runs) as home_runs,
        sum(b.rbi) as rbi,
        sum(b.runs) as runs,
        sum(b.walks) as walks,
        sum(b.strikeouts) as strikeouts,
        sum(b.stolen_bases) as stolen_bases,
        sum(b.total_bases) as total_bases,
        sum(b.extra_base_hits) as extra_base_hits,
        sum(coalesce(b.at_bats, 0) + coalesce(b.walks, 0)) as plate_appearances,
        sum(b.left_on_base) as left_on_base,

        -- Team rate stats
        safe_divide(sum(b.hits), sum(b.at_bats)) as team_batting_avg,
        safe_divide(sum(b.hits) + sum(b.walks), sum(b.at_bats) + sum(b.walks)) as team_obp,
        safe_divide(sum(b.total_bases), sum(b.at_bats)) as team_slg,
        safe_divide(sum(b.hits) + sum(b.walks), sum(b.at_bats) + sum(b.walks))
            + safe_divide(sum(b.total_bases), sum(b.at_bats)) as team_ops,
        safe_divide(sum(b.walks), sum(b.at_bats) + sum(b.walks)) * 100 as team_walk_rate,
        safe_divide(sum(b.strikeouts), sum(b.at_bats) + sum(b.walks)) * 100 as team_strikeout_rate,

        -- Statcast batting metrics (averaged across players with data)
        avg(b.avg_exit_velocity) as team_avg_exit_velocity,
        max(b.max_exit_velocity) as team_max_exit_velocity,
        avg(b.avg_launch_angle) as team_avg_launch_angle,
        sum(b.barrels) as team_barrels,
        sum(b.hard_hits) as team_hard_hits,
        sum(b.batted_balls) as team_batted_balls,
        safe_divide(sum(b.barrels), sum(b.batted_balls)) as team_barrel_rate,
        safe_divide(sum(b.hard_hits), sum(b.batted_balls)) as team_hard_hit_rate

    from batting as b
    group by 1, 2, 3

),

-- Aggregate pitching stats by team per game
team_pitching as (

    select
        p.game_id,
        p.team_id,

        -- Counting stats
        count(distinct p.player_id) as pitchers_used,
        sum(p.innings_pitched_decimal) as innings_pitched,
        sum(p.hits) as hits_allowed,
        sum(p.runs) as runs_allowed,
        sum(p.earned_runs) as earned_runs,
        sum(p.walks) as walks_allowed,
        sum(p.strikeouts) as strikeouts_pitching,
        sum(p.home_runs) as home_runs_allowed,
        sum(p.pitches) as total_pitches,
        sum(p.strikes) as total_strikes,

        -- Team pitching rate stats
        safe_divide(sum(p.earned_runs) * 9, sum(p.innings_pitched_decimal)) as team_era,
        safe_divide(sum(p.walks) + sum(p.hits), sum(p.innings_pitched_decimal)) as team_whip,
        safe_divide(sum(p.strikeouts) * 9, sum(p.innings_pitched_decimal)) as team_k_per_nine,
        safe_divide(sum(p.walks) * 9, sum(p.innings_pitched_decimal)) as team_bb_per_nine,
        safe_divide(sum(p.strikes), sum(p.pitches)) * 100 as team_strike_percentage,
        countif(p.is_quality_start) as quality_starts,

        -- Statcast pitching metrics
        avg(p.avg_pitch_velocity) as team_avg_pitch_velocity,
        max(p.max_pitch_velocity) as team_max_pitch_velocity,
        avg(p.avg_spin_rate) as team_avg_spin_rate,
        safe_divide(sum(p.pitches_in_zone), sum(p.statcast_pitches)) as team_zone_rate

    from pitching as p
    group by 1, 2

),

-- Unpivot games so each team gets its own row
team_games as (

    select
        g.game_id,
        g.season,
        g.game_date,
        g.game_type,
        g.home_team_id as team_id,
        g.home_team_name as team_name,
        g.home_team_abbr as team_abbr,
        g.home_league_id as league_id,
        g.home_league_name as league_name,
        g.home_league_abbr as league_abbr,
        g.home_division_id as division_id,
        g.home_division_name as division_name,
        g.home_division_abbr as division_abbr,
        g.home_score as runs_scored,
        g.away_score as runs_allowed,
        g.home_score - g.away_score as run_differential,
        'home' as home_away,
        case when g.winning_team_id = g.home_team_id then true else false end as is_win,
        case when g.losing_team_id = g.home_team_id then true else false end as is_loss,
        g.away_team_id as opponent_team_id,
        g.away_team_name as opponent_team_name,
        g.away_team_abbr as opponent_team_abbr
    from games as g

    union all

    select
        g.game_id,
        g.season,
        g.game_date,
        g.game_type,
        g.away_team_id as team_id,
        g.away_team_name as team_name,
        g.away_team_abbr as team_abbr,
        g.away_league_id as league_id,
        g.away_league_name as league_name,
        g.away_league_abbr as league_abbr,
        g.away_division_id as division_id,
        g.away_division_name as division_name,
        g.away_division_abbr as division_abbr,
        g.away_score as runs_scored,
        g.home_score as runs_allowed,
        g.away_score - g.home_score as run_differential,
        'away' as home_away,
        case when g.winning_team_id = g.away_team_id then true else false end as is_win,
        case when g.losing_team_id = g.away_team_id then true else false end as is_loss,
        g.home_team_id as opponent_team_id,
        g.home_team_name as opponent_team_name,
        g.home_team_abbr as opponent_team_abbr
    from games as g

),

final as (

    select
        -- Game and team identifiers
        tg.game_id,
        tg.team_id,
        tg.team_name,
        tg.team_abbr,
        tg.league_id,
        tg.league_name,
        tg.league_abbr,
        tg.division_id,
        tg.division_name,
        tg.division_abbr,
        tg.season,
        tg.game_date,
        tg.game_type,
        tg.home_away,

        -- Opponent info
        tg.opponent_team_id,
        tg.opponent_team_name,
        tg.opponent_team_abbr,

        -- Game outcome
        tg.runs_scored,
        tg.runs_allowed,
        tg.run_differential,
        tg.is_win,
        tg.is_loss,

        -- Team batting
        tb.batters_used,
        tb.at_bats,
        tb.hits,
        tb.singles,
        tb.doubles,
        tb.triples,
        tb.home_runs,
        tb.rbi,
        tb.walks,
        tb.strikeouts,
        tb.stolen_bases,
        tb.total_bases,
        tb.extra_base_hits,
        tb.plate_appearances,
        tb.left_on_base,
        round(tb.team_batting_avg, 3) as team_batting_avg,
        round(tb.team_obp, 3) as team_obp,
        round(tb.team_slg, 3) as team_slg,
        round(tb.team_ops, 3) as team_ops,
        round(tb.team_walk_rate, 1) as team_walk_rate,
        round(tb.team_strikeout_rate, 1) as team_strikeout_rate,

        -- Team Statcast batting
        round(tb.team_avg_exit_velocity, 1) as team_avg_exit_velocity,
        round(tb.team_max_exit_velocity, 1) as team_max_exit_velocity,
        round(tb.team_avg_launch_angle, 1) as team_avg_launch_angle,
        tb.team_barrels,
        tb.team_hard_hits,
        tb.team_batted_balls,
        round(tb.team_barrel_rate, 3) as team_barrel_rate,
        round(tb.team_hard_hit_rate, 3) as team_hard_hit_rate,

        -- Team pitching
        tp.pitchers_used,
        round(tp.innings_pitched, 1) as team_innings_pitched,
        tp.hits_allowed,
        tp.earned_runs,
        tp.walks_allowed,
        tp.strikeouts_pitching as team_strikeouts_pitching,
        tp.home_runs_allowed,
        tp.total_pitches,
        tp.total_strikes,
        round(tp.team_era, 2) as team_era,
        round(tp.team_whip, 2) as team_whip,
        round(tp.team_k_per_nine, 1) as team_k_per_nine,
        round(tp.team_bb_per_nine, 1) as team_bb_per_nine,
        round(tp.team_strike_percentage, 1) as team_strike_percentage,
        tp.quality_starts,

        -- Team Statcast pitching
        round(tp.team_avg_pitch_velocity, 1) as team_avg_pitch_velocity,
        round(tp.team_max_pitch_velocity, 1) as team_max_pitch_velocity,
        round(tp.team_avg_spin_rate, 0) as team_avg_spin_rate,
        round(tp.team_zone_rate, 3) as team_zone_rate,

        -- Metadata
        current_timestamp() as loaded_at

    from team_games as tg
    left join team_batting as tb
        on tg.game_id = tb.game_id
        and tg.team_id = tb.team_id
    left join team_pitching as tp
        on tg.game_id = tp.game_id
        and tg.team_id = tp.team_id

)

select * from final
