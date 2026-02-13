{{-
  config(
    materialized='table',
    tags=["intermediate", "nba", "divisions"]
  )
-}}

-- Enrich divisions with conference information

with divisions as (
  select *
  from {{ ref('stg_nba__divisions') }}
),

conferences as (
  select
    conference_id,
    conference_name,
    conference_abbr
  from {{ ref('stg_nba__conferences') }}
),

enriched as (
  select
    d.division_id,
    d.division_name,
    d.division_abbr,
    d.conference_id,
    c.conference_name,
    c.conference_abbr
  from divisions d
  left join conferences c on d.conference_id = c.conference_id
)

select * from enriched
