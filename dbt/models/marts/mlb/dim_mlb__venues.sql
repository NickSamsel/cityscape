{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "dimension", "venues"]
  )
-}}

-- Dimension table for MLB venues (ballparks)
-- One row per venue_id using the latest available season

with ranked as (
  select
    *,
    row_number() over (
      partition by venue_id
      order by season desc
    ) as row_num
  from {{ ref('core_mlb__venues') }}
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
from ranked
where row_num = 1
