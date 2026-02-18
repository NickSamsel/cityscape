{{-
  config(
    materialized='table',
    tags=["mart", "nfl", "fact", "games"]
  )
-}}

-- Mart fact table for NFL games
-- Analytics-ready game-level facts

select *
from {{ ref('int_nfl__games_enriched') }}
