{{-
  config(
    materialized='incremental',
    unique_key=['venue_id', 'season'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb", "venues"]
  )
-}}

with source_data as (
  select
    {{ cast_string('venue_id') }} as venue_id,
    {{ cast_integer('season') }} as season,
    {{ cast_string('venue_name') }} as venue_name,
    cast(active as bool) as active,

    -- Location
    {{ cast_string('city') }} as city,
    {{ cast_string('state') }} as state,
    {{ cast_string('state_abbrev') }} as state_abbrev,
    {{ cast_string('country') }} as country,
    {{ cast_decimal('latitude') }} as latitude,
    {{ cast_decimal('longitude') }} as longitude,

    -- Field info
    {{ cast_integer('capacity') }} as capacity,
    {{ cast_string('turf_type') }} as turf_type,
    {{ cast_string('roof_type') }} as roof_type,
    {{ cast_decimal('left_line') }} as left_line,
    {{ cast_decimal('right_line') }} as right_line,
    {{ cast_decimal('center') }} as center,
    {{ cast_decimal('left') }} as left,
    {{ cast_decimal('right') }} as right,
    {{ cast_decimal('left_center') }} as left_center,
    {{ cast_decimal('right_center') }} as right_center

  from {{ source('raw', 'mlb_venues') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.venue_id = {{ cast_string('venue_id') }}
      and existing.season = {{ cast_integer('season') }}
  )
  {% endif %}
),

deduplicated as (
  select
    *,
    row_number() over (
      partition by venue_id, season
      order by venue_name
    ) as row_num
  from source_data
)

select
  venue_id,
  season,
  venue_name,
  active,
  city,
  state,
  state_abbrev,
  country,
  latitude,
  longitude,
  capacity,
  turf_type,
  roof_type,
  left_line,
  right_line,
  center,
  left,
  right,
  left_center,
  right_center
from deduplicated
where row_num = 1
