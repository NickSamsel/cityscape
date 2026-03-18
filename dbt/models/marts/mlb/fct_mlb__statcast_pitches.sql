{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "fact", "statcast"]
  )
-}}

-- Mart fact table for MLB Statcast pitch-level data
-- Analytics-ready view of every pitch with complete context
-- Each row represents a single pitch with pitcher, batter, and game details

select *
from {{ ref('int_mlb__statcast_pitches_enriched') }}
