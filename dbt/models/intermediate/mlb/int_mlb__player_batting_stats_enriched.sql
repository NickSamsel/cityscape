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

final as (
    select
        bs.game_id,
        bs.player_id,
        bs.player_name,
        bs.team_id,
        t.team_name,
        t.team_abbr,
        t.league_id,
        lg.league_name,
        lg.league_abbr as league_abbr_name,
        t.division_id,
        div.division_name,
        div.division_abbr as division_abbr_name,
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
        
        -- Batting average (from API)
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
    where bs.at_bats is not null
        or bs.walks is not null
)

select * from final
