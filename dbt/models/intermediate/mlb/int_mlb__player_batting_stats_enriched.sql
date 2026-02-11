{{ config(
    tags=["int", "mlb", "player_stats"],
    materialized='table'
) }}

with batting_stats as (
    select * from {{ ref('stg_mlb__player_batting_stats') }}
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
        bs.game_id,
        bs.player_id,
        p.full_name,
        -- player specific age and career lenght stats
        date_diff('year', p.birth_date, bs.game_date) as age,
        date_diff('year', p.mlb_debut_date, bs.game_date) as career_length,
        bs.team_id,
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
        bs.batting_order,
        bs.position,
        
        -- Raw counting stats
        bs.at_bats,
        bs.runs,
        bs.hits,
        bs.doubles,
        bs.triples,
        bs.home_runs,
        bs.rbi,
        bs.stolen_bases,
        bs.walks,
        bs.strikeouts,
        bs.left_on_base,
        
        -- Calculated stats
        bs.hits - coalesce(bs.doubles, 0) - coalesce(bs.triples, 0) - coalesce(bs.home_runs, 0) as singles,
        
        (bs.hits - coalesce(bs.doubles, 0) - coalesce(bs.triples, 0) - coalesce(bs.home_runs, 0))
            + (coalesce(bs.doubles, 0) * 2)
            + (coalesce(bs.triples, 0) * 3)
            + (coalesce(bs.home_runs, 0) * 4) as total_bases,
        
        bs.at_bats + coalesce(bs.walks, 0) as plate_appearances,
        
        -- Extra base hits
        coalesce(bs.doubles, 0) + coalesce(bs.triples, 0) + coalesce(bs.home_runs, 0) as extra_base_hits,
        
        -- Advanced rate stats
        case
            when bs.at_bats > 0 then round(safe_cast(bs.hits as float64) / bs.at_bats, 3)
            else null
        end as batting_avg_game,
        
        case
            when bs.at_bats > 0 then 
                round(safe_divide(
                    cast((bs.hits - coalesce(bs.doubles, 0) - coalesce(bs.triples, 0) - coalesce(bs.home_runs, 0))
                        + (coalesce(bs.doubles, 0) * 2)
                        + (coalesce(bs.triples, 0) * 3)
                        + (coalesce(bs.home_runs, 0) * 4) as float64),
                    cast(bs.at_bats as float64)
                ), 3)
            else null
        end as slugging_pct_game,
        
        -- ISO (Isolated Power) = SLG - AVG
        case
            when bs.at_bats > 0 then
                round(
                    safe_divide(
                        cast((bs.hits - coalesce(bs.doubles, 0) - coalesce(bs.triples, 0) - coalesce(bs.home_runs, 0))
                            + (coalesce(bs.doubles, 0) * 2)
                            + (coalesce(bs.triples, 0) * 3)
                            + (coalesce(bs.home_runs, 0) * 4) as float64),
                        cast(bs.at_bats as float64)
                    ) - safe_divide(cast(bs.hits as float64), cast(bs.at_bats as float64)),
                3)
            else null
        end as iso,
        
        -- BABIP (Batting Average on Balls In Play)
        case
            when (bs.at_bats - coalesce(bs.strikeouts, 0) - coalesce(bs.home_runs, 0)) > 0 then
                round(
                    safe_divide(
                        cast(bs.hits - coalesce(bs.home_runs, 0) as float64),
                        cast(bs.at_bats - coalesce(bs.strikeouts, 0) - coalesce(bs.home_runs, 0) as float64)
                    ),
                3)
            else null
        end as babip,
        
        -- Walk rate (BB%)
        case
            when (bs.at_bats + coalesce(bs.walks, 0)) > 0 then
                round(
                    safe_divide(
                        cast(coalesce(bs.walks, 0) as float64),
                        cast(bs.at_bats + coalesce(bs.walks, 0) as float64)
                    ) * 100,
                1)
            else null
        end as walk_rate,
        
        -- Strikeout rate (K%)
        case
            when (bs.at_bats + coalesce(bs.walks, 0)) > 0 then
                round(
                    safe_divide(
                        cast(coalesce(bs.strikeouts, 0) as float64),
                        cast(bs.at_bats + coalesce(bs.walks, 0) as float64)
                    ) * 100,
                1)
            else null
        end as strikeout_rate,
        
        -- BB/K ratio
        case
            when coalesce(bs.strikeouts, 0) > 0 then
                round(
                    safe_divide(
                        cast(coalesce(bs.walks, 0) as float64),
                        cast(bs.strikeouts as float64)
                    ),
                2)
            else null
        end as bb_k_ratio,
        
        -- Power factor (total bases per hit)
        case
            when bs.hits > 0 then
                round(
                    safe_divide(
                        cast((bs.hits - coalesce(bs.doubles, 0) - coalesce(bs.triples, 0) - coalesce(bs.home_runs, 0))
                            + (coalesce(bs.doubles, 0) * 2)
                            + (coalesce(bs.triples, 0) * 3)
                            + (coalesce(bs.home_runs, 0) * 4) as float64),
                        cast(bs.hits as float64)
                    ),
                2)
            else null
        end as power_factor,
        
        -- Season stats from API
        bs.avg,
        bs.obp,
        bs.slg,
        bs.ops
        
    from batting_stats as bs
    left join games as g
        on bs.game_id = cast(g.game_id as string)
    left join teams as t
        on bs.team_id = t.team_id
        and g.season = t.season
    left join leagues as lg
        on t.league_id = lg.league_id
    left join divisions as div
        on t.division_id = div.division_id
    left join players as p
        on bs.player_id = p.player_id
    where bs.at_bats is not null
        or bs.walks is not null
)

select * from final
