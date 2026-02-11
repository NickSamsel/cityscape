{{ config(tags=["stg", "mlb"]) }}

select
  cast(league_id as int64) as league_id,
  cast(league_name as string) as league_name,
  cast(league_abbr as string) as league_abbr
from {{ source('raw', 'mlb_leagues') }}
