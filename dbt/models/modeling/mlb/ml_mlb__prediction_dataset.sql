{{-
  config(
    materialized='table',
    tags=["modeling", "mlb"]
  )
-}}

select
    s.game_id,
    