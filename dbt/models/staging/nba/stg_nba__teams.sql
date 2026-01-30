{{ config(tags=["stg", "nba"]) }}

select
  cast(null as varchar) as team_id,
  cast(null as varchar) as team_name,
  cast(null as varchar) as team_abbr
from {{ source('raw', 'nba_teams') }}
where 1 = 0
