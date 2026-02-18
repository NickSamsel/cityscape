{{-
  config(
    materialized='table',
    tags=["mart", "nhl", "fact", "games"]
  )
-}}

-- Mart fact table for NHL games
-- Analytics-ready game-level facts

select *
from {{ ref('int_nhl__games_enriched') }}
