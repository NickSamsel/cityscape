{{-
  config(
    materialized='table',
    tags=["intermediate", "nba", "teams"]
  )
-}}

-- Enrich teams with conference and division information

with teams as (
  select *
  from {{ ref('stg_nba__teams') }}
),

conferences as (
  select
    conference_id,
    conference_name,
    conference_abbr
  from {{ ref('stg_nba__conferences') }}
),

divisions as (
  select
    division_id,
    division_name,
    division_abbr
  from {{ ref('stg_nba__divisions') }}
),

enriched as (
  select
    t.team_id,
    t.team_name,
    t.team_abbr,
    t.team_city,
    t.conference_id,
    c.conference_name,
    c.conference_abbr,
    t.division_id,
    d.division_name,
    d.division_abbr,
    t.year_founded
  from teams t
  left join conferences c on t.conference_id = c.conference_id
  left join divisions d on t.division_id = d.division_id
)

select * from enriched
