{{ config(
    tags=["int", "mlb"],
    materialized='table'
) }}

-- Intermediate model for MLB divisions enriched with league information

with divisions as (
    select * from {{ ref('stg_mlb__divisions') }}
),

leagues as (
    select * from {{ ref('stg_mlb__leagues') }}
),

final as (
    select
        d.division_id,
        d.division_name,
        d.division_abbr,
        d.league_id,
        l.league_name,
        l.league_abbr
    from divisions d
    left join leagues l
        on d.league_id = l.league_id
)

select * from final
