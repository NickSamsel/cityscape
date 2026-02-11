{{ config(
    tags=["int", "mlb", "player_stats"],
    materialized='table'
) }}

with pitching_stats as (
    select * from {{ ref('stg_mlb__player_pitching_stats') }}
),

games as (
    select * from {{ ref('stg_mlb__games') }}
),

teams as (
    select * from {{ ref('stg_mlb__teams') }}
),

final as (
    select
        ps.game_id,
        ps.player_id,
        ps.player_name,
        ps.team_id,
        t.team_name,
        t.team_abbr,
        t.league_id,
        t.division_id,
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
        end as bb_per_nine
        
    from pitching_stats as ps
    left join games as g
        on ps.game_id = cast(g.game_id as string)
    left join teams as t
        on ps.team_id = t.team_id
        and g.season = t.season
    where ps.innings_pitched is not null
)

select * from final
