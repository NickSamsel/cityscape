{{-
  config(
    materialized='table',
    tags=["mart", "nba", "dimension", "players"]
  )
-}}

-- Dimension table for NBA players
-- Analytics-ready player reference data

select
  player_id,
  full_name,
  first_name,
  last_name,
  jersey_number,
  position,
  height,
  weight,
  birth_date,
  current_age,
  country,
  draft_year,
  draft_round,
  draft_number,
  draft_category,
  is_active,
  years_since_draft
from {{ ref('int_nba__players_enriched') }}
