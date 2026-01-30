{{ config(tags=["stg", "mlb"]) }}

select
  cast(null as varchar) as team_id,
  cast(null as varchar) as team_name,
  cast(null as varchar) as team_abbr
from {{ source('raw', 'mlb_teams') }}
where 1 = 0
