{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["int", "mlb"]
  )
-}}

with primary_fields as (
    select *
    from {{ ref('stg_mlb__venues') }}
    where country in ('USA', 'Canada')
),

game_counts as (
    select 
        venue_id, 
        home_team_id,
        season,
        count(*) as total_games
    from {{ ref('stg_mlb__games') }}
    where game_type = 'R'
    group by all
),

venue_primary_team as (
    select 
        venue_id,
        home_team_id as primary_home_team_id,
        season,
        row_number() over (
            partition by venue_id, season 
            order by total_games desc
        ) as popularity_rank
    from game_counts
),

team_names as (
    select 
        team_id,
        team_name
    from {{ ref('stg_mlb__teams') }}
)

select distinct
    v.*,
    h.primary_home_team_id,
    t.team_name as primary_home_team_name
from primary_fields v
left join venue_primary_team h 
    on v.venue_id = h.venue_id
left join team_names t
    on h.primary_home_team_id = t.team_id
where h.popularity_rank = 1

{% if is_incremental() %}
  and not exists (
    select 1 from {{ this }} as existing
    where existing.venue_id = v.venue_id
      and existing.season = h.season
  )
{% endif %}