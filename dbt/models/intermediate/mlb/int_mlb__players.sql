{{-
  config(
    materialized='incremental',
    unique_key='player_id',
    on_schema_change='sync_all_columns',
    tags=["int", "mlb"]
  )
-}}

-- Intermediate model for MLB players
-- No additional enrichment needed at intermediate layer for reference data

select
    player_id,
    full_name,
    first_name,
    last_name,
    primary_number,
    birth_date,
    current_age,
    birth_city,
    birth_state_province,
    birth_country,
    height,
    weight,
    primary_position_code,
    primary_position_name,
    primary_position_abbr,
    bat_side_code,
    bat_side_description,
    pitch_hand_code,
    pitch_hand_description,
    mlb_debut_date,
    active,
    raw
from {{ ref('stg_mlb__players') }}

{% if is_incremental() %}
  where player_id not in (select player_id from {{ this }})
{% endif %}