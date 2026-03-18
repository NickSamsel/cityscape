{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "fact", "statcast"]
  )
-}}

-- Mart fact table for MLB Statcast batted ball data
-- Analytics-ready view of every batted ball with complete context
-- Each row represents a single batted ball with exit velocity, launch angle, and outcomes

select *
from {{ ref('int_mlb__statcast_batted_balls_enriched') }}
