{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb", "schedule"]
  )
-}}

with source_data as (
    select
        {{ cast_string('game_id') }} as game_id,
        {{ cast_integer('season') }} as season,
        {{ cast_date('game_date') }} as game_date,
        cast(game_datetime as timestamp) as game_datetime,
        {{ cast_string('game_type') }} as game_type,
        {{ cast_string('status') }} as status,
        {{ cast_string('day_night') }} as day_night,
        {{ cast_string('venue_id') }} as venue_id,
        {{ cast_string('venue_name') }} as venue_name,
        {{ cast_string('home_team_id') }} as home_team_id,
        {{ cast_string('away_team_id') }} as away_team_id,
        {{ cast_string('home_probable_pitcher_id') }} as home_probable_pitcher_id,
        {{ cast_string('home_probable_pitcher_name') }} as home_probable_pitcher_name,
        {{ cast_string('away_probable_pitcher_id') }} as away_probable_pitcher_id,
        {{ cast_string('away_probable_pitcher_name') }} as away_probable_pitcher_name,
        {{ cast_integer('scheduled_innings') }} as scheduled_innings,
        {{ cast_string('series_description') }} as series_description
    from {{ source('raw', 'mlb_schedule') }}
),

deduplicated as (
    select
        *,
        row_number() over (
          partition by game_id
          order by game_date desc
        ) as row_num
    from source_data
)

select
    game_id,
    season,
    game_date,
    game_datetime,
    game_type,
    status,
    day_night,
    venue_id,
    venue_name,
    home_team_id,
    away_team_id,
    home_probable_pitcher_id,
    home_probable_pitcher_name,
    away_probable_pitcher_id,
    away_probable_pitcher_name,
    scheduled_innings,
    series_description
from deduplicated
where row_num = 1
