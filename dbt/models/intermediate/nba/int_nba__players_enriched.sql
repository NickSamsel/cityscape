{{-
  config(
    materialized='table',
    tags=["intermediate", "nba", "players"]
  )
-}}

-- Enrich players with derived attributes and career info

with players as (
  select *
  from {{ ref('stg_nba__players') }}
),

enriched as (
  select
    player_id,
    full_name,
    first_name,
    last_name,
    jersey_number,
    position,
    height,
    weight,
    birth_date,
    -- Calculate age
    date_diff(current_date(), birth_date, year) as current_age,
    country,
    draft_year,
    draft_round,
    draft_number,
    is_active,
    -- Career years
    case
      when draft_year is not null
      then date_diff(current_date(), date(draft_year, 1, 1), year)
      else null
    end as years_since_draft,
    -- Draft position context
    case
      when draft_round = 1 and draft_number <= 5 then 'Lottery Pick'
      when draft_round = 1 and draft_number <= 14 then 'First Round'
      when draft_round = 2 then 'Second Round'
      else 'Undrafted'
    end as draft_category
  from players
)

select * from enriched
