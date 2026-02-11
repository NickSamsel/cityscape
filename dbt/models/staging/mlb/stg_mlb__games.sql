{{-
  config(
    materialized='incremental',
    unique_key='game_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source as (
    select
        cast(game_id as string) as game_id,
        cast(season as int64) as season,
        cast(game_date as date) as game_date,
        cast(game_type as string) as game_type,
        cast(status as string) as status,
        cast(home_team_id as string) as home_team_id,
        cast(away_team_id as string) as away_team_id,
        cast(home_score as int64) as home_score,
        cast(away_score as int64) as away_score,
        row_number() over (
          partition by cast(game_id as string), cast(season as int64)
          order by cast(game_date as date) desc
        ) as row_num
    from {{ source('raw', 'mlb_games') }}
    
    {% if is_incremental() %}
    where game_id not in (select game_id from {{ this }})
    {% endif %}
)

select * except(row_num)
from source
where row_num = 1
