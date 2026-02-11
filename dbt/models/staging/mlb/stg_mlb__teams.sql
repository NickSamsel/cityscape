{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source as (
  select
    cast(team_id as string) as team_id,
    cast(season as int64) as season,
    cast(team_name as string) as team_name,
    cast(team_abbr as string) as team_abbr,
    cast(league_id as int64) as league_id,
    cast(division_id as int64) as division_id,
    row_number() over (
      partition by cast(team_id as string), cast(season as int64)
      order by cast(team_name as string)
    ) as row_num
  from {{ source('raw', 'mlb_teams') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.team_id = cast(team_id as string)
      and existing.season = cast(season as int64)
  )
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
