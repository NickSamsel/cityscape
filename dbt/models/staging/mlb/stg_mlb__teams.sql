{{ config(tags=["stg", "mlb"]) }}

select
  cast(team_id as string) as team_id,
  cast(season as int64) as season,
  cast(team_name as string) as team_name,
  cast(team_abbr as string) as team_abbr,
  cast(league_id as int64) as league_id,
  cast(division_id as int64) as division_id
from {{ source('raw', 'mlb_teams') }}
