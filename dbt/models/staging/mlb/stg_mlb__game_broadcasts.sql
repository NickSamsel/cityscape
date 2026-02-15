{{-
  config(
    materialized='incremental',
    unique_key=['game_id', 'broadcast_name'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb", "schedule"]
  )
-}}

with source as (
  select
    {{ cast_string('game_id') }} as game_id,
    {{ cast_string('broadcast_name') }} as broadcast_name,
    {{ cast_string('broadcast_type') }} as broadcast_type,
    {{ cast_string('call_sign') }} as call_sign,
    cast(is_national as bool) as is_national,
    {{ cast_string('home_away') }} as home_away,
    {{ cast_string('language') }} as language,
    row_number() over (
      partition by {{ cast_string('game_id') }}, {{ cast_string('broadcast_name') }}
      order by loaded_at desc
    ) as row_num
  from {{ source('raw', 'mlb_game_broadcasts') }}

  {% if is_incremental() %}
  where not exists (
    select 1 from {{ this }} as existing
    where existing.game_id = {{ cast_string('game_id') }}
      and existing.broadcast_name = {{ cast_string('broadcast_name') }}
  )
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
