{{-
	config(
		materialized='incremental',
		incremental_strategy='merge',
		unique_key=['player_id', 'game_date', 'pitcher_id', 'game_id'],
		partition_by={"field": "game_date", "data_type": "date"},
		cluster_by=['player_id', 'pitcher_id'],
		tags=["modeling", "mlb", "predictions", "outcomes"]
	)
-}}

-- Resolved prediction outcomes
-- Joins predictions with actual batting results to measure model accuracy
-- Only includes games that have been completed

with predictions as (
	select
		player_id,
		game_date,
		pitcher_id,
		game_id,
		hit_probability,
		model_version,
		predicted_at,
		player_name,
		bat_side_code,
		bat_side_description,
		team_id,
		home_team_id,
		away_team_id,
		game_datetime,
		game_status,
		home_vs_away,
		opponent_team_id
	from {{ ref('ml_mlb__daily_predictions') }}

	{% if is_incremental() %}
		-- Only look at recent games that may have completed
		where game_date >= date_sub((select max(game_date) from {{ this }}), interval 7 day)
	{% endif %}
)

, batting_stats as (
	select
		player_id,
		game_date,
		game_id,
		team_id,
		hits,
		at_bats,
		plate_appearances
	from {{ ref('fct_mlb__player_batting_stats') }}
)

, schedule as (
	select
		game_id,
		status
	from {{ ref('fct_mlb__schedule') }}
	where status in ('Final', 'Completed', 'Game Over')  -- Only completed games
)

select
	-- All prediction columns
	p.player_id,
	p.game_date,
	p.pitcher_id,
	p.game_id,
	p.hit_probability,
	p.model_version,
	p.predicted_at,
	p.player_name,
	p.bat_side_code,
	p.bat_side_description,
	p.team_id,
	p.home_team_id,
	p.away_team_id,
	p.game_datetime,
	p.game_status,
	p.home_vs_away,
	p.opponent_team_id,

	-- Actual outcome
	coalesce(bs.hits, 0) > 0 as got_hit,
	coalesce(bs.hits, 0) as actual_hits,
	coalesce(bs.at_bats, 0) as actual_at_bats,
	coalesce(bs.plate_appearances, 0) as actual_plate_appearances,

	-- Prediction accuracy
	-- Using 0.50 as default threshold (can adjust based on model calibration)
	case
		when p.hit_probability >= 0.50 and coalesce(bs.hits, 0) > 0 then true
		when p.hit_probability < 0.50 and coalesce(bs.hits, 0) = 0 then true
		else false
	end as prediction_correct,

	-- Timestamp when outcome was resolved
	current_timestamp() as resolved_at

from predictions p
inner join schedule s
	on p.game_id = s.game_id  -- Only include completed games
left join batting_stats bs
	on p.player_id = bs.player_id
	and p.game_date = bs.game_date
	and p.game_id = bs.game_id
