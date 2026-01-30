{{ config(tags=["stg", "mlb"]) }}

select
  cast(team_id as varchar) as team_id,
  cast(season as integer) as season,
  cast(team_name as varchar) as team_name,
  cast(team_abbr as varchar) as team_abbr,
  cast(league_id as integer) as league_id,
  cast(division_id as integer) as division_id
from {{ source('raw', 'mlb_teams') }}
