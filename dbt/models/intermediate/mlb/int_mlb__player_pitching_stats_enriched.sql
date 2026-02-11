{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'player_id', 'team_id'],
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

final as (
    select
        ps.game_id,
        ps.player_id,
        ps.player_name,
        -- player specific age and career lenght stats
        date_diff(g.game_date, p.birth_date, YEAR) as age,
        date_diff(g.game_date, p.mlb_debut_date, YEAR) as career_length,
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
        ps.era,
        
        -- Convert innings pitched string to decimal (e.g., "5.2" means 5 2/3 innings)
        case
            when ps.innings_pitched is null then null
            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
            else safe_cast(ps.innings_pitched as float64)
        end as innings_pitched_decimal,
        
        -- Calculate strike percentage
        case
            when ps.pitches > 0 then round(safe_divide(cast(ps.strikes as float64), cast(ps.pitches as float64)) * 100, 1)
            else null
        end as strike_percentage,
        
        -- Calculate WHIP (Walks + Hits per Inning Pitched)
        case
            when ps.innings_pitched is not null then
                safe_divide(
                    cast(coalesce(ps.walks, 0) + coalesce(ps.hits, 0) as float64),
                    case
                        when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                        when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                        else safe_cast(ps.innings_pitched as float64)
                    end
                )
            else null
        end as whip,
        
        -- Calculate K/9 (Strikeouts per 9 innings)
        case
            when ps.innings_pitched is not null then
                safe_divide(
                    cast(coalesce(ps.strikeouts, 0) as float64) * 9,
                    case
                        when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                        when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                        else safe_cast(ps.innings_pitched as float64)
                    end
                )
            else null
        end as k_per_nine,
        
        -- Calculate BB/9 (Walks per 9 innings)
        case
            when ps.innings_pitched is not null then
                safe_divide(
                    cast(coalesce(ps.walks, 0) as float64) * 9,
                    case
                        when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                        when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                        else safe_cast(ps.innings_pitched as float64)
                    end
                )
            else null
        end as bb_per_nine,
        
        -- Calculate K/BB ratio
        case
            when coalesce(ps.walks, 0) > 0 then
                round(
                    safe_divide(
                        cast(coalesce(ps.strikeouts, 0) as float64),
                        cast(ps.walks as float64)
                    ),
                2)
            else null
        end as k_bb_ratio,
        
        -- Calculate HR/9 (Home Runs per 9 innings)
        case
            when ps.innings_pitched is not null then
                round(
                    safe_divide(
                        cast(coalesce(ps.home_runs, 0) as float64) * 9,
                        case
                            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                            else safe_cast(ps.innings_pitched as float64)
                        end
                    ),
                2)
            else null
        end as hr_per_nine,
        
        -- Calculate H/9 (Hits per 9 innings)
        case
            when ps.innings_pitched is not null then
                round(
                    safe_divide(
                        cast(coalesce(ps.hits, 0) as float64) * 9,
                        case
                            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                            else safe_cast(ps.innings_pitched as float64)
                        end
                    ),
                2)
            else null
        end as h_per_nine,
        
        -- Calculate FIP (Fielding Independent Pitching)
        -- FIP = ((13*HR)+(3*BB)-(2*K))/IP + 3.2
        case
            when ps.innings_pitched is not null then
                round(
                    safe_divide(
                        ((13.0 * coalesce(ps.home_runs, 0)) + (3.0 * coalesce(ps.walks, 0)) - (2.0 * coalesce(ps.strikeouts, 0))),
                        case
                            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                            else safe_cast(ps.innings_pitched as float64)
                        end
                    ) + 3.2,
                2)
            else null
        end as fip,
        
        -- Pitches per inning
        case
            when ps.innings_pitched is not null and ps.pitches is not null then
                round(
                    safe_divide(
                        cast(ps.pitches as float64),
                        case
                            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                            else safe_cast(ps.innings_pitched as float64)
                        end
                    ),
                1)
            else null
        end as pitches_per_inning,
        
        -- Approximate K% (strikeouts / estimated batters faced)
        -- Estimate batters faced: (IP * 3) + H + BB
        case
            when ps.innings_pitched is not null then
                round(
                    safe_divide(
                        cast(coalesce(ps.strikeouts, 0) as float64),
                        cast(
                            (case
                                when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                                when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                                else safe_cast(ps.innings_pitched as float64)
                            end * 3) + coalesce(ps.hits, 0) + coalesce(ps.walks, 0)
                        as float64)
                    ) * 100,
                1)
            else null
        end as k_percentage,
        
        -- Quality start indicator (6+ IP and <= 3 ER)
        case
            when ps.innings_pitched is not null then
                case
                    when (
                        case
                            when ps.innings_pitched like '%.1' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.333
                            when ps.innings_pitched like '%.2' then cast(split(ps.innings_pitched, '.')[offset(0)] as float64) + 0.667
                            else safe_cast(ps.innings_pitched as float64)
                        end >= 6.0
                        and coalesce(ps.earned_runs, 0) <= 3
                    ) then true
                    else false
                end
            else null
        end as is_quality_start
        
    from pitching_stats as ps
    left join games as g
        on ps.game_id = cast(g.game_id as string)
    left join teams as t
        on ps.team_id = t.team_id
        and g.season = t.season
    left join leagues as lg
        on t.league_id = lg.league_id
    left join divisions as div
        on t.division_id = div.division_id
    left join players as p
        on ps.player_id = p.player_id
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

select * from final
