{{-
  config(
    materialized='incremental',
    unique_key='division_id',
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source as (
  select
    cast(division_id as int64) as division_id,
    cast(division_name as string) as division_name,
    cast(division_abbr as string) as division_abbr,
    cast(league_id as int64) as league_id,
    row_number() over (
      partition by cast(division_id as int64)
      order by cast(division_name as string)
    ) as row_num
  from {{ source('raw', 'mlb_divisions') }}

  {% if is_incremental() %}
  where division_id not in (select division_id from {{ this }})
  {% endif %}
)

select * except(row_num)
from source
where row_num = 1
