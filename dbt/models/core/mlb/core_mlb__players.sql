{{ config(
  tags=["core", "mlb"],
  materialized='view'
) }}

-- Core model for players
-- Simple pass-through from intermediate layer for reference data

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
from {{ ref('int_mlb__players') }}