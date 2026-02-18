{{-
  config(
    materialized='incremental',
    unique_key='player_id',
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "dimension"]
  )
-}}

-- Mart dimension table for MLB players
-- Analytics-ready view built from core model

select *
from {{ ref('int_mlb__players') }}