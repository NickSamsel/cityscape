{{-
  config(
    materialized='incremental',
    unique_key='division_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source_data as (
  select
    {{ cast_string('division_id') }} as division_id,
    {{ cast_string('division_name') }} as division_name,
    {{ cast_string('division_abbr') }} as division_abbr,
    {{ cast_string('league_id') }} as league_id
  from {{ source('raw', 'mlb_divisions') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.division_id = {{ cast_string('division_id') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by division_id
      order by division_name
    ) as row_num
  from source_data
)

select
  division_id,
  division_name,
  division_abbr,
  league_id
from deduplicated
where row_num = 1
