{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

source_data as (
  select
    {{ cast_string('team_id') }} as team_id,
    {{ cast_integer('season') }} as season,
    {{ cast_string('team_name') }} as team_name,
    {{ cast_string('team_abbr') }} as team_abbr,
    {{ cast_integer('league_id') }} as league_id,
    {{ cast_integer('division_id') }} as division_id
  from {{ source('raw', 'mlb_teams') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.team_id = {{ cast_string('team_id') }}
      and existing.season = {{ cast_integer('season') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by team_id, season
      order by team_name
    ) as row_num
  from source_data
)

select
  team_id,
  season,
  team_name,
  team_abbr,
  league_id,
  division_id
from deduplicated
where row_num = 1
