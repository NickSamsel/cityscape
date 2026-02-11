{{ config(tags=["core", "mlb", "player_stats"]) }}

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
  batting_order,
  position,
  at_bats,
  runs,
  hits,
  doubles,
  triples,
  home_runs,
  rbi,
  stolen_bases,
  walks,
  strikeouts,
  left_on_base,
  -- Calculate single bases hit (hits - 2B - 3B - HR)
  hits - coalesce(doubles, 0) - coalesce(triples, 0) - coalesce(home_runs, 0) as singles,
  -- Calculate total bases (1B + 2*2B + 3*3B + 4*HR)
  (hits - coalesce(doubles, 0) - coalesce(triples, 0) - coalesce(home_runs, 0))
    + (coalesce(doubles, 0) * 2)
    + (coalesce(triples, 0) * 3)
    + (coalesce(home_runs, 0) * 4) as total_bases,
  -- Season averages
  avg,
  obp,
  slg,
  ops
from {{ ref('int_mlb__player_batting_stats_enriched') }}
-- Remove any records where player didn't actually bat
where at_bats is not null or walks is not null
