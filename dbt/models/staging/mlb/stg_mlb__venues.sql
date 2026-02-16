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
        active,

        {{ cast_string('city') }} as city,
        {{ cast_string('state') }} as state,
        {{ cast_string('state_abbrev') }} as state_abbrev,
        {{ cast_string('country') }} as country,
        {{ cast_float('latitude') }} as latitude,
        {{ cast_float('longitude') }} as longitude,

        {{ cast_integer('capacity') }} as capacity,
        {{ cast_string('turf_type') }} as turf_type,
        {{ cast_string('roof_type') }} as roof_type,
        {{ cast_float('left_line') }} as left_line,
        {{ cast_float('right_line') }} as right_line,
        {{ cast_float('center') }} as center,
        {%- if target.type == 'bigquery' -%}
        {{ cast_float('`left`') }} as left_distance,
        {{ cast_float('`right`') }} as right_distance,
        {%- else -%}
        {{ cast_float('left') }} as left_distance,
        {{ cast_float('right') }} as right_distance,
        {%- endif -%}
        {{ cast_float('left_center') }} as left_center,
        {{ cast_float('right_center') }} as right_center
    from {{ source('raw', 'mlb_venues') }}

    {% if is_incremental() %}
    where not exists (
        select 1
        from {{ this }} as existing
        where existing.venue_id = {{ cast_string('venue_id') }}
          and coalesce(existing.season, -1) = coalesce({{ cast_integer('season') }}, -1)
    )
    {% endif %}
),

deduplicated as (
    select
        *,
        row_number() over (
          partition by venue_id, coalesce(season, -1)
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
    left_distance,
    right_distance,
    left_center,
    right_center
from deduplicated
where row_num = 1
