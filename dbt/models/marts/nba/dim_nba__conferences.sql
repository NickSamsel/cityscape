{{-
  config(
    materialized='table',
    tags=["mart", "nba", "dimension", "conferences"]
  )
-}}

-- Dimension table for NBA conferences
-- Analytics-ready conference reference data

select
  conference_id,
  conference_name,
  conference_abbr
from {{ ref('int_nba__conferences') }}
