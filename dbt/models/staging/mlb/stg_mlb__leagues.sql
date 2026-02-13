{{-
  config(
    materialized='incremental',
    unique_key='league_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source_data as (
  select
    {{ cast_integer('league_id') }} as league_id,
    {{ cast_string('league_name') }} as league_name,
    {{ cast_string('league_abbr') }} as league_abbr
  from {{ source('raw', 'mlb_leagues') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.league_id = {{ cast_integer('league_id') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by league_id
      order by league_name
    ) as row_num
  from source_data
)

select
  league_id,
  league_name,
  league_abbr
from deduplicated
where row_num = 1
