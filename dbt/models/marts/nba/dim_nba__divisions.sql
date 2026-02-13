{{-
  config(
    materialized='table',
    tags=["mart", "nba", "dimension", "divisions"]
  )
-}}

-- Dimension table for NBA divisions
-- Analytics-ready division reference data

select
  division_id,
  division_name,
  division_abbr,
  conference_id,
  conference_name,
  conference_abbr
from {{ ref('int_nba__divisions') }}
