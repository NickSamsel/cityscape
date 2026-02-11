{{ config(tags=["stg", "mlb"]) }}

select
    cast(player_id as string) as player_id,
    cast(full_name as string) as full_name,
    cast(first_name as string) as first_name,
    cast(last_name as string) as last_name,
    cast(primary_number as string) as primary_number,
    cast(birth_date as date) as birth_date,
    cast(current_age as int64) as current_age,
    cast(birth_city as string) as birth_city,
    cast(birth_state_province as string) as birth_state_province,
    cast(birth_country as string) as birth_country,
    cast(height as string) as height,
    cast(weight as int64) as weight,
    cast(primary_position_code as string) as primary_position_code,
    cast(primary_position_name as string) as primary_position_name,
    cast(primary_position_abbr as string) as primary_position_abbr,
    cast(bat_side_code as string) as bat_side_code,
    cast(bat_side_description as string) as bat_side_description,
    cast(pitch_hand_code as string) as pitch_hand_code,
    cast(pitch_hand_description as string) as pitch_hand_description,
    cast(mlb_debut_date as date) as mlb_debut_date,
    cast(active as boolean) as active,
    cast(raw as string) as raw
from {{ source('raw', 'mlb_players') }}