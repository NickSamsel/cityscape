{{-
  config(
    materialized='table',
    tags=["stg", "nba", "divisions"]
  )
-}}

source_data as (
  select
    {{ cast_integer('division_id') }} as division_id,
    {{ cast_string('division_name') }} as division_name,
    {{ cast_string('division_abbr') }} as division_abbr,
    {{ cast_integer('conference_id') }} as conference_id,
    loaded_at
  from {{ source('raw', 'nba_divisions') }}
),

deduplicated as (
  select
    *,
    row_number() over (partition by division_id order by loaded_at desc) as row_num
  from source_data
)

select
  division_id,
  division_name,
  division_abbr,
  conference_id
from deduplicated
where row_num = 1
