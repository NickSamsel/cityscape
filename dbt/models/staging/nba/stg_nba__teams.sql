{{-
  config(
    materialized='table',
    tags=["stg", "nba", "teams"]
  )
-}}

source_data as (
  select
    {{ cast_string('team_id') }} as team_id,
    {{ cast_string('team_name') }} as team_name,
    {{ cast_string('team_abbr') }} as team_abbr,
    {{ cast_string('team_city') }} as team_city,
    {{ cast_integer('conference_id') }} as conference_id,
    {{ cast_integer('division_id') }} as division_id,
    {{ cast_integer('year_founded') }} as year_founded,
    loaded_at
  from {{ source('raw', 'nba_teams') }}
),

deduplicated as (
  select
    *,
    row_number() over (partition by team_id order by loaded_at desc) as row_num
  from source_data
)

select
  team_id,
  team_name,
  team_abbr,
  team_city,
  conference_id,
  division_id,
  year_founded
from deduplicated
where row_num = 1
