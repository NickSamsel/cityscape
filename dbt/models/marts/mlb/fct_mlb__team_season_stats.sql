{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "team_stats"]
  )
-}}

-- Mart fact table for MLB team season-level statistics
-- Aggregates team game stats into season totals and averages
-- Each row represents a team's full season performance

with team_games as (

    select * from {{ ref('fct_mlb__team_game_stats') }}
    where game_type = 'R'  -- Regular season only
    {% if is_incremental() %}
    and season not in (select distinct season from {{ this }})
    {% endif %}

),

season_stats as (

    select
        team_id,
        team_name,
        team_abbr,
        league_id,
        league_name,
        league_abbr,
        division_id,
        division_name,
        division_abbr,
        season,

        -- Record
        count(*) as games_played,
        countif(is_win) as wins,
        countif(is_loss) as losses,
        safe_divide(countif(is_win), count(*)) as win_pct,
        countif(is_win and home_away = 'home') as home_wins,
        countif(is_loss and home_away = 'home') as home_losses,
        countif(is_win and home_away = 'away') as away_wins,
        countif(is_loss and home_away = 'away') as away_losses,

        -- Run production
        sum(runs_scored) as total_runs_scored,
        sum(runs_allowed) as total_runs_allowed,
        sum(run_differential) as total_run_differential,
        avg(runs_scored) as avg_runs_scored_per_game,
        avg(runs_allowed) as avg_runs_allowed_per_game,
        avg(run_differential) as avg_run_differential_per_game,

        -- Pythagorean win expectation: RS^2 / (RS^2 + RA^2)
        safe_divide(
            power(sum(runs_scored), 2),
            power(sum(runs_scored), 2) + power(sum(runs_allowed), 2)
        ) as pythagorean_win_pct,

        -- Team batting aggregates
        sum(at_bats) as total_at_bats,
        sum(hits) as total_hits,
        sum(singles) as total_singles,
        sum(doubles) as total_doubles,
        sum(triples) as total_triples,
        sum(home_runs) as total_home_runs,
        sum(rbi) as total_rbi,
        sum(walks) as total_walks,
        sum(strikeouts) as total_strikeouts,
        sum(stolen_bases) as total_stolen_bases,
        sum(total_bases) as total_bases,
        sum(extra_base_hits) as total_extra_base_hits,
        sum(plate_appearances) as total_plate_appearances,
        sum(left_on_base) as total_left_on_base,

        -- Season batting rates
        safe_divide(sum(hits), sum(at_bats)) as season_batting_avg,
        safe_divide(sum(hits) + sum(walks), sum(at_bats) + sum(walks)) as season_obp,
        safe_divide(sum(total_bases), sum(at_bats)) as season_slg,
        safe_divide(sum(hits) + sum(walks), sum(at_bats) + sum(walks))
            + safe_divide(sum(total_bases), sum(at_bats)) as season_ops,
        safe_divide(sum(walks), sum(plate_appearances)) * 100 as season_walk_rate,
        safe_divide(sum(strikeouts), sum(plate_appearances)) * 100 as season_strikeout_rate,

        -- Team pitching aggregates
        sum(team_innings_pitched) as total_innings_pitched,
        sum(hits_allowed) as total_hits_allowed,
        sum(earned_runs) as total_earned_runs,
        sum(walks_allowed) as total_walks_allowed,
        sum(team_strikeouts_pitching) as total_strikeouts_pitching,
        sum(home_runs_allowed) as total_home_runs_allowed,
        sum(total_pitches) as season_total_pitches,
        sum(quality_starts) as total_quality_starts,

        -- Season pitching rates
        safe_divide(sum(earned_runs) * 9, sum(team_innings_pitched)) as season_era,
        safe_divide(sum(hits_allowed) + sum(walks_allowed), sum(team_innings_pitched)) as season_whip,
        safe_divide(sum(team_strikeouts_pitching) * 9, sum(team_innings_pitched)) as season_k_per_nine,
        safe_divide(sum(walks_allowed) * 9, sum(team_innings_pitched)) as season_bb_per_nine,

        -- Statcast batting averages (season level)
        avg(team_avg_exit_velocity) as season_avg_exit_velocity,
        max(team_max_exit_velocity) as season_max_exit_velocity,
        avg(team_avg_launch_angle) as season_avg_launch_angle,
        sum(team_barrels) as season_total_barrels,
        sum(team_hard_hits) as season_total_hard_hits,
        sum(team_batted_balls) as season_total_batted_balls,
        safe_divide(sum(team_barrels), sum(team_batted_balls)) as season_barrel_rate,
        safe_divide(sum(team_hard_hits), sum(team_batted_balls)) as season_hard_hit_rate,

        -- Statcast pitching averages (season level)
        avg(team_avg_pitch_velocity) as season_avg_pitch_velocity,
        max(team_max_pitch_velocity) as season_max_pitch_velocity,
        avg(team_avg_spin_rate) as season_avg_spin_rate,
        avg(team_zone_rate) as season_zone_rate

    from team_games
    group by 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

),

final as (

    select
        team_id,
        team_name,
        team_abbr,
        league_id,
        league_name,
        league_abbr,
        division_id,
        division_name,
        division_abbr,
        season,

        -- Record
        games_played,
        wins,
        losses,
        round(win_pct, 3) as win_pct,
        home_wins,
        home_losses,
        away_wins,
        away_losses,

        -- Run production
        total_runs_scored,
        total_runs_allowed,
        total_run_differential,
        round(avg_runs_scored_per_game, 2) as avg_runs_scored_per_game,
        round(avg_runs_allowed_per_game, 2) as avg_runs_allowed_per_game,
        round(avg_run_differential_per_game, 2) as avg_run_differential_per_game,
        round(pythagorean_win_pct, 3) as pythagorean_win_pct,

        -- Luck factor: actual win % minus expected win %
        round(win_pct - pythagorean_win_pct, 3) as luck_factor,

        -- Batting
        total_at_bats,
        total_hits,
        total_singles,
        total_doubles,
        total_triples,
        total_home_runs,
        total_rbi,
        total_walks,
        total_strikeouts,
        total_stolen_bases,
        total_bases,
        total_extra_base_hits,
        total_plate_appearances,
        total_left_on_base,
        round(season_batting_avg, 3) as season_batting_avg,
        round(season_obp, 3) as season_obp,
        round(season_slg, 3) as season_slg,
        round(season_ops, 3) as season_ops,
        round(season_walk_rate, 1) as season_walk_rate,
        round(season_strikeout_rate, 1) as season_strikeout_rate,

        -- Pitching
        round(total_innings_pitched, 1) as total_innings_pitched,
        total_hits_allowed,
        total_earned_runs,
        total_walks_allowed,
        total_strikeouts_pitching,
        total_home_runs_allowed,
        season_total_pitches,
        total_quality_starts,
        round(season_era, 2) as season_era,
        round(season_whip, 2) as season_whip,
        round(season_k_per_nine, 1) as season_k_per_nine,
        round(season_bb_per_nine, 1) as season_bb_per_nine,

        -- Statcast batting
        round(season_avg_exit_velocity, 1) as season_avg_exit_velocity,
        round(season_max_exit_velocity, 1) as season_max_exit_velocity,
        round(season_avg_launch_angle, 1) as season_avg_launch_angle,
        season_total_barrels,
        season_total_hard_hits,
        season_total_batted_balls,
        round(season_barrel_rate, 3) as season_barrel_rate,
        round(season_hard_hit_rate, 3) as season_hard_hit_rate,

        -- Statcast pitching
        round(season_avg_pitch_velocity, 1) as season_avg_pitch_velocity,
        round(season_max_pitch_velocity, 1) as season_max_pitch_velocity,
        round(season_avg_spin_rate, 0) as season_avg_spin_rate,
        round(season_zone_rate, 3) as season_zone_rate,

        -- Metadata
        current_timestamp() as loaded_at

    from season_stats

)

select * from final
