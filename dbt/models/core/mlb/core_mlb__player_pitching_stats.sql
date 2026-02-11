{{ config(
  tags=["core", "mlb", "player_stats", "deprecated"],
  materialized='view'
) }}

/*
 * DEPRECATED: This model has been replaced by fct_mlb__player_pitching_stats in marts/mlb/
 * Please use {{ ref('fct_mlb__player_pitching_stats') }} instead.
 * This model will be removed in a future version.
 */

select
  game_id,
  player_id,
  player_name,
  team_id,
  team_name,
  team_abbr,
  game_date,
  season,
  game_type,
  innings_pitched,
  -- Convert innings pitched string to decimal (e.g., "5.2" means 5 2/3 innings = 5.667)
  case
    when innings_pitched is null then null
    when innings_pitched like '%.1' then cast(split(innings_pitched, '.')[offset(0)] as float64) + 0.333
    when innings_pitched like '%.2' then cast(split(innings_pitched, '.')[offset(0)] as float64) + 0.667
    else safe_cast(innings_pitched as float64)
  end as innings_pitched_decimal,
  hits,
  runs,
  earned_runs,
  walks,
  strikeouts,
  home_runs,
  pitches,
  strikes,
  -- Calculate strike percentage
  case
    when pitches > 0 then round(safe_divide(strikes, pitches) * 100, 1)
    else null
  end as strike_percentage,
  -- Calculate WHIP (Walks + Hits per Inning Pitched)
  case
    when innings_pitched is not null then
      safe_divide(
        coalesce(walks, 0) + coalesce(hits, 0),
        case
          when innings_pitched like '%.1' then cast(split(innings_pitched, '.')[offset(0)] as float64) + 0.333
          when innings_pitched like '%.2' then cast(split(innings_pitched, '.')[offset(0)] as float64) + 0.667
          else safe_cast(innings_pitched as float64)
        end
      )
    else null
  end as whip,
  era
from {{ ref('int_mlb__player_pitching_stats_enriched') }}
-- Remove any records where pitcher didn't actually pitch
where innings_pitched is not null
