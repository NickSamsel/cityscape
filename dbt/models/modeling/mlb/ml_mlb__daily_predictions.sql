{{-
	config(
		materialized='incremental',
		incremental_strategy='merge',
		unique_key=['player_id', 'game_date', 'pitcher_id', 'game_id'],
		partition_by={"field": "game_date", "data_type": "date"},
		cluster_by=['player_id', 'pitcher_id'],
		tags=["modeling", "mlb", "predictions"]
	)
-}}

-- Daily predictions from ML inference pipeline
-- Enriched with player, team, and game context for analysis

with raw_predictions as (
	select
		player_id,
		game_date,
		pitcher_id,
		game_id,
		hit_probability,
		model_version,
		predicted_at
	from {{ source('mlb_modeling', 'ml_mlb__model_predictions_raw') }}

	{% if is_incremental() %}
		where game_date >= (select max(game_date) from {{ this }})
	{% endif %}
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
	select
		player_id,
		team_id,
		season
	from {{ ref('fct_mlb__player_team_season') }}
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

