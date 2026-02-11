{{-
  config(
    materialized='incremental',
    unique_key='league_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source as (
  select
    cast(league_id as int64) as league_id,
    cast(league_name as string) as league_name,
    cast(league_abbr as string) as league_abbr,
    row_number() over (
      partition by cast(league_id as int64)
      order by cast(league_name as string)
    ) as row_num
  from {{ source('raw', 'mlb_leagues') }}

  {% if is_incremental() %}
  where league_id not in (select league_id from {{ this }})
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
