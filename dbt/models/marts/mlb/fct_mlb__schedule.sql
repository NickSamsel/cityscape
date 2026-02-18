{{-
  config(
    materialized='view',
    tags=["mart", "mlb", "fact", "schedule"]
  )
-}}

-- Mart fact table for MLB schedule
-- Analytics-ready view with full team context, venue, and probable pitcher information
-- Each row represents a scheduled or completed game

select * from {{ ref('int_mlb__schedule_enriched') }}
