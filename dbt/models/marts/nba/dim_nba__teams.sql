{{-
  config(
    materialized='table',
    tags=["mart", "nba", "dimension", "teams"]
  )
-}}

-- Dimension table for NBA teams
-- Analytics-ready team reference data

select
  team_id,
  team_name,
  team_abbr,
  team_city,
  conference_id,
  conference_name,
  conference_abbr,
  division_id,
  division_name,
  division_abbr,
  year_founded
from {{ ref('int_nba__teams') }}
