{{-
  config(
  materialized='table',
  partition_by={"field": "game_date",
      "data_type": "date",
      "granularity": "month"},
  cluster_by=["game_id", "player_id", "pitcher_id"],
    tags=["modeling", "mlb"]
  )
-}}

{%- set prediction_date = var('prediction_date', none) -%}

with params as (
  select
    {% if prediction_date %}
      date('{{ prediction_date }}') as prediction_date
    {% else %}
      (
        select min(game_date)
        from {{ ref('fct_mlb__schedule') }}
        where game_date > current_date()
      ) as prediction_date
    {% endif %}
)

, games as (
  select
    s.game_id,
    s.season,
    s.game_date,
    s.status,
    s.home_team_id,
    s.away_team_id,
    s.home_probable_pitcher_id,
    s.away_probable_pitcher_id,
    s.has_probable_pitchers
  from {{ ref('fct_mlb__schedule') }} s
  join params p
    on s.game_date = p.prediction_date
  where s.has_probable_pitchers = true
)

, game_sides as (
  -- Expand each game into two “hitter team vs opposing probable pitcher” rows.
  select
    g.game_id,
    g.season,
    g.game_date,
    g.home_team_id,
    g.away_team_id,
    g.away_team_id as team_id,
    g.home_probable_pitcher_id as pitcher_id,
    0 as home_vs_away
  from games g

  union all

  select
    g.game_id,
    g.season,
    g.game_date,
    g.home_team_id,
    g.away_team_id,
    g.home_team_id as team_id,
    g.away_probable_pitcher_id as pitcher_id,
    1 as home_vs_away
  from games g
)

, teams_in_slate as (
  select distinct team_id
  from game_sides
)

, roster_hitters_recent as (
  -- Best-effort “roster”: hitters who have been in lineups recently for that team.
  select distinct
    gl.team_id,
    gl.player_id
  from {{ ref('fct_mlb__game_lineups') }} gl
  join params p
    on gl.game_date >= date_sub(p.prediction_date, interval 30 day)
   and gl.game_date < p.prediction_date
  join teams_in_slate t
    on gl.team_id = t.team_id
)

, roster_hitters_batting_recent as (
  -- Fill any gaps from batting appearances (covers cases where lineups data is sparse).
  select distinct
    bs.team_id,
    bs.player_id
  from {{ ref('fct_mlb__player_batting_stats') }} bs
  join params p
    on bs.game_date >= date_sub(p.prediction_date, interval 30 day)
   and bs.game_date < p.prediction_date
  join teams_in_slate t
    on bs.team_id = t.team_id
)

, roster_hitters_season_fallback as (
  -- Season-level fallback: primary-team hitters for the slate season.
  -- Useful early-season when recent samples are thin.
  select distinct
    ps.team_id,
    ps.player_id
  from {{ ref('int_mlb__player_season_stats_enriched') }} ps
  join games g
    on ps.season = g.season
  join teams_in_slate t
    on ps.team_id = t.team_id
  where ps.plate_appearances >= 1
)

, roster_hitters as (
  select * from roster_hitters_recent
  union distinct
  select * from roster_hitters_batting_recent
  union distinct
  select * from roster_hitters_season_fallback
)

, latest_batter_rolling as (
  select
    r.*
  from {{ ref('ml_mlb__rolling_batter_stats') }} r
  join params p
    on r.game_date < p.prediction_date
  qualify row_number() over (partition by r.player_id order by r.game_date desc, r.game_id desc) = 1
)

, latest_pitcher_rolling as (
  select
    p.*
  from {{ ref('ml_mlb__rolling_pitcher_stats') }} p
  join params x
    on p.game_date < x.prediction_date
  qualify row_number() over (partition by p.pitcher_id order by p.game_date desc, p.game_id desc) = 1
)

, candidate_hitters as (
  select
    rh.team_id,
    rh.player_id,
    lbr.game_date as batter_features_asof_date,
    lbr.avg_L7,
    lbr.avg_L15,
    lbr.avg_L30,
    lbr.games_with_hit_L5,
    lbr.obp_L30,
    lbr.slg_L30,
    lbr.exit_velo_L15,
    lbr.hard_hit_rate_L15,
    lbr.barrel_rate_L15
  from roster_hitters rh
  left join latest_batter_rolling lbr
    on rh.player_id = lbr.player_id
)

select
  -- Identifiers
  ch.player_id,
  gs.game_date,
  gs.pitcher_id,
  gs.game_id,

  -- Player form features
  coalesce(ch.avg_L7, 0) as rolling_batting_avg_L7,
  coalesce(ch.avg_L15, 0) as rolling_batting_avg_L15,
  coalesce(ch.avg_L30, 0) as rolling_batting_avg_L30,
  coalesce(ch.games_with_hit_L5, 0) as games_with_hit_L5,
  coalesce(ch.obp_L30, 0) as obp_L30,
  coalesce(ch.slg_L30, 0) as slg_L30,

  -- Statcast features
  coalesce(ch.exit_velo_L15, 0) as exit_velo_L15,
  coalesce(ch.hard_hit_rate_L15, 0) as hard_hit_rate_L15,
  coalesce(ch.barrel_rate_L15, 0) as barrel_rate_L15,

  -- Matchup features
  coalesce(m.career_avg_vs_pitcher, 0) as career_avg_vs_pitcher,

  -- Zone matchup features
  coalesce(zm.overall_zone_matchup, 0) as zone_matchup_score,
  coalesce(zm.overall_zone_matchup, 0) as normalized_zone_score,
  greatest(
    coalesce(zm.high_zone_matchup, 0),
    coalesce(zm.middle_zone_matchup, 0),
    coalesce(zm.low_zone_matchup, 0),
    coalesce(zm.inside_zone_matchup, 0),
    coalesce(zm.outside_zone_matchup, 0),
    coalesce(zm.heart_zone_matchup, 0)
  ) as max_zone_advantage,

  -- Regional zone features
  coalesce(zm.high_zone_matchup, 0) as high_zone_matchup,
  coalesce(zm.middle_zone_matchup, 0) as middle_zone_matchup,
  coalesce(zm.low_zone_matchup, 0) as low_zone_matchup,
  coalesce(zm.inside_zone_matchup, 0) as inside_zone_matchup,
  coalesce(zm.outside_zone_matchup, 0) as outside_zone_matchup,
  coalesce(zm.heart_zone_matchup, 0) as heart_zone_matchup,
  coalesce(zm.overall_zone_matchup, 0) as overall_zone_matchup,
  coalesce(zm.hitter_high_success, 0) as hitter_high_success,
  coalesce(zm.hitter_low_success, 0) as hitter_low_success,
  coalesce(zm.hitter_inside_success, 0) as hitter_inside_success,
  coalesce(zm.hitter_outside_success, 0) as hitter_outside_success,
  coalesce(zm.pitcher_high_freq, 0) as pitcher_high_freq,
  coalesce(zm.pitcher_low_freq, 0) as pitcher_low_freq,
  coalesce(zm.pitcher_inside_freq, 0) as pitcher_inside_freq,
  coalesce(zm.pitcher_outside_freq, 0) as pitcher_outside_freq,
  coalesce(zm.favorable_high, 0) as favorable_high,
  coalesce(zm.favorable_outside, 0) as favorable_outside,

  -- Pitcher features
  coalesce(lpr.era_L5, 0) as pitcher_era_L5,
  coalesce(lpr.whip_L5, 0) as pitcher_whip_L5,
  coalesce(lpr.fip_L15, 0) as pitcher_fip_L15,

  -- Context
  gs.home_vs_away,

  -- Debug / freshness metadata (optional downstream)
  ch.batter_features_asof_date,
  lpr.game_date as pitcher_features_asof_date

from game_sides gs
join candidate_hitters ch
  on gs.team_id = ch.team_id
left join latest_pitcher_rolling lpr
  on gs.pitcher_id = lpr.pitcher_id
left join {{ ref('ml_mlb__matchups') }} m
  on ch.player_id = m.batter_id
 and gs.pitcher_id = m.pitcher_id
left join {{ ref('ml_mlb__zone_matchup') }} zm
  on ch.player_id = zm.player_id
 and gs.pitcher_id = zm.pitcher_id
 and gs.season = zm.season

