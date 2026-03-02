{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='game_id',
    partition_by={
      "field": "game_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "home_team_id", "away_team_id"],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source_data as (
    select
        {{ cast_string('game_id') }} as game_id,
        {{ cast_integer('season') }} as season,
        {{ cast_date('game_date') }} as game_date,
        {{ cast_string('game_type') }} as game_type,
        {{ cast_string('status') }} as status,
        {{ cast_string('home_team_id') }} as home_team_id,
        {{ cast_string('away_team_id') }} as away_team_id,
        {{ cast_integer('home_score') }} as home_score,
        {{ cast_integer('away_score') }} as away_score,
        {{ cast_string('venue_id') }} as venue_id
    from {{ source('raw', 'mlb_games') }}

    {% if is_incremental() %}
    -- Look back 3 days to catch stat corrections
    where {{ cast_date('game_date') }} >= date_sub(
      (select max(game_date) from {{ this }}),
      interval 3 day
    )
    {% endif %}
),

deduplicated as (
    select
        *,
        row_number() over (
          partition by game_id, season
          order by game_date desc
        ) as row_num
    from source_data
)

select
    game_id,
    season,
    game_date,
    game_type,
    status,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    venue_id
from deduplicated
where row_num = 1
