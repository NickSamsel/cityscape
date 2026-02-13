{{-
  config(
    materialized='table',
    tags=["stg", "nba", "players"]
  )
-}}

source_data as (
  select
    {{ cast_string('player_id') }} as player_id,
    {{ cast_string('full_name') }} as full_name,
    {{ cast_string('first_name') }} as first_name,
    {{ cast_string('last_name') }} as last_name,
    {{ cast_string('jersey_number') }} as jersey_number,
    {{ cast_string('position') }} as position,
    {{ cast_string('height') }} as height,
    {{ cast_integer('weight') }} as weight,
    {{ cast_date('birth_date') }} as birth_date,
    {{ cast_string('country') }} as country,
    {{ cast_integer('draft_year') }} as draft_year,
    {{ cast_integer('draft_round') }} as draft_round,
    {{ cast_integer('draft_number') }} as draft_number,
    cast(is_active as bool) as is_active,
    loaded_at
  from {{ source('raw', 'nba_players') }}
),

deduplicated as (
  select
    *,
    row_number() over (partition by player_id order by loaded_at desc) as row_num
  from source_data
)

select
  player_id,
  full_name,
  first_name,
  last_name,
  jersey_number,
  position,
  height,
  weight,
  birth_date,
  country,
  draft_year,
  draft_round,
  draft_number,
  is_active
from deduplicated
where row_num = 1
