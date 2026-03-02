{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['game_id', 'player_id', 'team_id'],
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "player_id", "team_id"],
    on_schema_change='sync_all_columns',
    tags=["int", "mlb", "player_stats"]
  )
-}}

with pitching_stats as (
    select * from {{ ref('stg_mlb__player_pitching_stats') }}
),

games as (
    select * from {{ ref('stg_mlb__games') }}
),

teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

leagues as (
    select * from {{ ref('stg_mlb__leagues') }}
),

divisions as (
    select * from {{ ref('stg_mlb__divisions') }}
),

players as (
    select * from {{ ref('stg_mlb__players') }}
),

-- Aggregate Statcast pitch metrics by game + pitcher
game_statcast_pitching as (
    select
        game_id,
        pitcher_id as player_id,
        count(*) as pitches_thrown,
        avg(release_speed) as avg_pitch_velocity,
        max(release_speed) as max_pitch_velocity,
        min(release_speed) as min_pitch_velocity,
        avg(release_spin_rate) as avg_spin_rate,
        max(release_spin_rate) as max_spin_rate,
        avg(release_extension) as avg_extension,
        -- Zone control
        countif(zone between 1 and 9) as pitches_in_zone,
        safe_divide(countif(zone between 1 and 9), count(*)) as zone_rate,
        -- Pitch results
        countif(pitch_result = 'S') as called_strikes,
        countif(pitch_result = 'W') as swinging_strikes,
        countif(pitch_result = 'X') as balls_in_play,
        countif(pitch_result = 'B') as balls,
        -- Primary pitch type (most common)
        approx_top_count(pitch_type, 1)[offset(0)].value as primary_pitch_type
    from {{ ref('stg_mlb__statcast_pitches') }}
    group by 1, 2
),

final as (
    with base_stats as (
        select
            ps.game_id,
            ps.player_id,
            ps.player_name,
            ps.team_id,
            t.team_name,
            t.team_abbr,
            t.league_id,
            lg.league_name,
            lg.league_abbr,
            t.division_id,
            div.division_name,
            div.division_abbr,
            g.game_date,
            g.season,
            g.game_type,
            g.status as game_status,
            
            -- Raw counting stats
            ps.innings_pitched,
            ps.hits,
            ps.runs,
            ps.earned_runs,
            ps.walks,
            ps.strikeouts,
            ps.home_runs,
            ps.pitches,
            ps.strikes,
            ps.era as era,
            
            -- Convert innings pitched string to decimal (e.g., "5.2" means 5 2/3 innings)
            -- Use exact fractions (1.0/3, 2.0/3) not approximations (0.333, 0.667) to avoid
            -- accumulated rounding error in downstream ERA/WHIP/FIP calculations
            case
                when ps.innings_pitched is null then null
                when ps.innings_pitched like '%.1' then safe_cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 1.0/3
                when ps.innings_pitched like '%.2' then safe_cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 2.0/3
                else safe_cast(ps.innings_pitched as float64)
            end as innings_pitched_decimal,
            
            -- player specific age and career length stats
            date_diff(g.game_date, p.birth_date, YEAR) as age,
            date_diff(g.game_date, p.mlb_debut_date, YEAR) as career_length,
            
            -- Statcast pitch metrics (game-level)
            sc.pitches_thrown as statcast_pitches,
            sc.avg_pitch_velocity,
            sc.max_pitch_velocity,
            sc.min_pitch_velocity,
            sc.avg_spin_rate,
            sc.max_spin_rate,
            sc.avg_extension,
            sc.pitches_in_zone,
            sc.zone_rate,
            sc.called_strikes,
            sc.swinging_strikes,
            sc.balls_in_play,
            sc.balls as balls_thrown,
            sc.primary_pitch_type as statcast_primary_pitch
            
        from pitching_stats as ps
        left join games as g
            on ps.game_id = g.game_id
        left join teams as t
            on ps.team_id = t.team_id
            and g.season = t.season
        left join leagues as lg
            on t.league_id = lg.league_id
        left join divisions as div
            on t.division_id = div.division_id
        left join players as p
            on ps.player_id = p.player_id
        left join game_statcast_pitching as sc
            on ps.game_id = sc.game_id
            and ps.player_id = sc.player_id
        where ps.innings_pitched is not null
        
        {% if is_incremental() %}
        and not exists (
            select 1 from {{ this }} as existing
            where existing.game_id = ps.game_id
              and existing.player_id = ps.player_id
              and existing.team_id = ps.team_id
        )
        {% endif %}
    )
    
    select
        -- Identifiers and context
        game_id,
        player_id,
        player_name,
        age,
        career_length,
        team_id,
        team_name,
        team_abbr,
        league_id,
        league_name,
        league_abbr,
        division_id,
        division_name,
        division_abbr,
        game_date,
        season,
        game_type,
        game_status,
        
        -- Raw counting stats
        innings_pitched,
        hits,
        runs,
        earned_runs,
        walks,
        strikeouts,
        home_runs,
        pitches,
        strikes,
        era,
        innings_pitched_decimal,
        
        -- Statcast metrics
        statcast_pitches,
        avg_pitch_velocity,
        max_pitch_velocity,
        min_pitch_velocity,
        avg_spin_rate,
        max_spin_rate,
        avg_extension,
        pitches_in_zone,
        zone_rate,
        called_strikes,
        swinging_strikes,
        balls_in_play,
        balls_thrown,
        statcast_primary_pitch,
        
        -- Calculate strike percentage
        case
            when pitches > 0 then round(safe_divide(cast(strikes as float64), cast(pitches as float64)) * 100, 1)
            else null
        end as strike_percentage,
        
        -- Calculate WHIP (Walks + Hits per Inning Pitched)
        case
            when innings_pitched_decimal > 0 then
                safe_divide(
                    cast(coalesce(walks, 0) + coalesce(hits, 0) as float64),
                    innings_pitched_decimal
                )
            else null
        end as whip,
        
        -- Calculate K/9 (Strikeouts per 9 innings)
        case
            when innings_pitched_decimal > 0 then
                safe_divide(
                    cast(coalesce(strikeouts, 0) as float64) * 9,
                    innings_pitched_decimal
                )
            else null
        end as k_per_nine,
        
        -- Calculate BB/9 (Walks per 9 innings)
        case
            when innings_pitched_decimal > 0 then
                safe_divide(
                    cast(coalesce(walks, 0) as float64) * 9,
                    innings_pitched_decimal
                )
            else null
        end as bb_per_nine,
        
        -- Calculate K/BB ratio
        case
            when coalesce(walks, 0) > 0 then
                round(
                    safe_divide(
                        cast(coalesce(strikeouts, 0) as float64),
                        cast(walks as float64)
                    ),
                2)
            else null
        end as k_bb_ratio,
        
        -- Calculate HR/9 (Home Runs per 9 innings)
        case
            when innings_pitched_decimal > 0 then
                round(
                    safe_divide(
                        cast(coalesce(home_runs, 0) as float64) * 9,
                        innings_pitched_decimal
                    ),
                2)
            else null
        end as hr_per_nine,
        
        -- Calculate H/9 (Hits per 9 innings)
        case
            when innings_pitched_decimal > 0 then
                round(
                    safe_divide(
                        cast(coalesce(hits, 0) as float64) * 9,
                        innings_pitched_decimal
                    ),
                2)
            else null
        end as h_per_nine,
        
        -- Calculate FIP (Fielding Independent Pitching)
        -- FIP = ((13*HR)+(3*BB)-(2*K))/IP + 3.2
        case
            when innings_pitched_decimal > 0 then
                round(
                    safe_divide(
                        ((13.0 * coalesce(home_runs, 0)) + (3.0 * coalesce(walks, 0)) - (2.0 * coalesce(strikeouts, 0))),
                        innings_pitched_decimal
                    ) + 3.2,
                2)
            else null
        end as fip,
        
        -- Pitches per inning
        case
            when innings_pitched_decimal > 0 and pitches is not null then
                round(
                    safe_divide(
                        cast(pitches as float64),
                        innings_pitched_decimal
                    ),
                1)
            else null
        end as pitches_per_inning,
        
        -- Calculate K% (strikeouts / total batters faced)
        -- Use more accurate batters faced calculation: at_bats + walks + hit_by_pitch + sac_fly + sac_bunt
        case
            when innings_pitched_decimal > 0 then
                round(
                    safe_divide(
                        cast(coalesce(strikeouts, 0) as float64),
                        greatest(
                            innings_pitched_decimal * 3 + coalesce(hits, 0) + coalesce(walks, 0),
                            1  -- Avoid division by zero
                        )
                    ) * 100,
                1)
            else null
        end as k_percentage,
        
        -- Quality start indicator (6+ IP and <= 3 ER)
        case
            when innings_pitched_decimal is not null then
                case
                    when (
                        innings_pitched_decimal >= 6.0
                        and coalesce(earned_runs, 0) <= 3
                    ) then true
                    else false
                end
            else null
        end as is_quality_start
        
    from base_stats
)

select * from final
