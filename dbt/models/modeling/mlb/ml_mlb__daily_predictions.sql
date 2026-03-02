{{-
	config(
		materialized='incremental',
		incremental_strategy='merge',
		unique_key=['player_id', 'game_date', 'pitcher_id', 'game_id'],
		partition_by={"field": "game_date",
      "data_type": "date",
      "granularity": "month"},
		cluster_by=['player_id', 'pitcher_id'],
		tags=["modeling", "mlb", "predictions"]
	)
-}}

-- Daily predictions from ML inference pipeline
-- Enriched with player, team, and game context for analysis

with raw_predictions_source as (
	select
		cast(player_id as string) as player_id,
		game_date,
		cast(pitcher_id as string) as pitcher_id,
		cast(game_id as string) as game_id,
		hit_probability,
		model_version,
		predicted_at
	from {{ source('mlb_modeling', 'ml_mlb__model_predictions_raw') }}

	{% if is_incremental() %}
		where game_date >= (select max(game_date) from {{ this }})
	{% endif %}
)

, raw_predictions as (
	-- Deduplicate raw predictions - keep most recent prediction
	select
		player_id,
		game_date,
		pitcher_id,
		game_id,
		hit_probability,
		model_version,
		predicted_at
	from (
		select
			*,
			row_number() over (
				partition by player_id, game_date, pitcher_id, game_id
				order by predicted_at desc, model_version desc
			) as row_num
		from raw_predictions_source
	)
	where row_num = 1
)

, players as (
	select
		player_id,
		full_name as player_name,
		bat_side_code,
		bat_side_description
	from {{ ref('dim_mlb__players') }}
)

, schedule as (
	select
		game_id,
		game_date,
		home_team_id,
		away_team_id,
		home_probable_pitcher_id,
		away_probable_pitcher_id,
		game_datetime,
		status
	from {{ ref('fct_mlb__schedule') }}
)

, player_teams as (
	-- Get each player's team for the game date
	-- Use team_rank = 1 to get primary team if player was traded mid-season
	select
		player_id,
		team_id,
		season
	from {{ ref('fct_mlb__player_team_season') }}
	where team_rank = 1  -- Primary team (most games played)
)

, batter_rolling_stats as (
	-- Get latest rolling stats for each player as of the game date
	select
		r.player_id,
		r.avg_L7,
		r.avg_L15,
		r.avg_L30,
		r.games_with_hit_L5,
		r.obp_L30,
		r.slg_L30,
		r.exit_velo_L15,
		r.hard_hit_rate_L15,
		r.barrel_rate_L15,
		r.game_date as stats_asof_date
	from {{ ref('ml_mlb__rolling_batter_stats') }} r
	join (
		select 
			player_id, 
			max(game_date) as max_game_date
		from {{ ref('ml_mlb__rolling_batter_stats') }}
		group by player_id
	) latest on r.player_id = latest.player_id and r.game_date = latest.max_game_date
)

select
	-- Identifiers
	p.player_id,
	p.game_date,
	p.pitcher_id,
	p.game_id,

	-- Prediction outputs
	p.hit_probability,
	p.model_version,
	p.predicted_at,

	-- Player context
	pl.player_name,
	pl.bat_side_code,
	pl.bat_side_description,
	pt.team_id,

	-- Game context
	s.home_team_id,
	s.away_team_id,
	s.game_datetime,
	s.status as game_status,

	-- Rolling batting stats (coalesce to handle missing data)
	coalesce(brs.avg_L7, 0) as rolling_batting_avg_L7,
	coalesce(brs.avg_L15, 0) as rolling_batting_avg_L15,
	coalesce(brs.avg_L30, 0) as rolling_batting_avg_L30,
	coalesce(brs.games_with_hit_L5, 0) as games_with_hit_L5,
	coalesce(brs.obp_L30, 0) as obp_L30,
	coalesce(brs.slg_L30, 0) as slg_L30,
	coalesce(brs.exit_velo_L15, 0) as exit_velo_L15,
	coalesce(brs.hard_hit_rate_L15, 0) as hard_hit_rate_L15,
	coalesce(brs.barrel_rate_L15, 0) as barrel_rate_L15,
	brs.stats_asof_date as batter_stats_asof_date,

	-- Derive whether player is home or away
	case
		when pt.team_id = s.home_team_id then 1
		when pt.team_id = s.away_team_id then 0
		else null
	end as home_vs_away,

	-- Derive opponent team
	case
		when pt.team_id = s.home_team_id then s.away_team_id
		when pt.team_id = s.away_team_id then s.home_team_id
		else null
	end as opponent_team_id

from raw_predictions p
left join players pl
	on p.player_id = pl.player_id
left join schedule s
	on p.game_id = s.game_id
left join player_teams pt
	on p.player_id = pt.player_id
	and extract(year from p.game_date) = pt.season
left join batter_rolling_stats brs
	on p.player_id = brs.player_id

