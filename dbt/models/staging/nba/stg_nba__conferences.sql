{{-
  config(
    materialized='table',
    tags=["stg", "nba", "conferences"]
  )
-}}

source_data as (
  select
    {{ cast_integer('conference_id') }} as conference_id,
    {{ cast_string('conference_name') }} as conference_name,
    {{ cast_string('conference_abbr') }} as conference_abbr,
    loaded_at
  from {{ source('raw', 'nba_conferences') }}
),

deduplicated as (
  select
    *,
    row_number() over (partition by conference_id order by loaded_at desc) as row_num
  from source_data
)

select
  conference_id,
  conference_name,
  conference_abbr
from deduplicated
where row_num = 1
