{{-
  config(
    materialized='table',
    tags=["intermediate", "nba", "conferences"]
  )
-}}

-- Pass-through for conferences (no enrichment needed at this layer)

select *
from {{ ref('stg_nba__conferences') }}
