{{ config(tags=["stg", "mlb"]) }}

select
  cast(division_id as int64) as division_id,
  cast(division_name as string) as division_name,
  cast(division_abbr as string) as division_abbr,
  cast(league_id as int64) as league_id
from {{ source('raw', 'mlb_divisions') }}
