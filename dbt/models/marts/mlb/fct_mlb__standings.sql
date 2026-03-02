{{-
  config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['team_id', 'season', 'standings_date'],
    partition_by={
      "field": "standings_date",
      "data_type": "date",
      "granularity": "month"
    },
    cluster_by=["season", "team_id", "division_id"],
    on_schema_change='sync_all_columns',
    tags=["mart", "mlb", "fact", "standings"]
  )
-}}

-- Mart fact table for MLB standings
-- Each row represents a team's standings record on a specific date
-- Supports temporal analysis: division races, hot/cold streaks, playoff positioning

with standings as (

    select * from {{ ref('stg_mlb__standings') }}
    {% if is_incremental() %}
    where not exists (
        select 1 from {{ this }} as existing
        where existing.team_id = stg_mlb__standings.team_id
          and existing.season = stg_mlb__standings.season
          and existing.standings_date = stg_mlb__standings.standings_date
    )
    {% endif %}

),

teams as (

    select * from {{ ref('stg_mlb__teams') }}

),

leagues as (

    select * from {{ ref('stg_mlb__leagues') }}

),

divisions as (

    select * from {{ ref('stg_mlb__divisions') }}

),

-- Get previous snapshot for each team to calculate momentum
standings_with_prev as (

    select
        s.*,
        lag(s.wins) over (
            partition by s.team_id, s.season
            order by s.standings_date
        ) as prev_wins,
        lag(s.losses) over (
            partition by s.team_id, s.season
            order by s.standings_date
        ) as prev_losses,
        lag(s.standings_date) over (
            partition by s.team_id, s.season
            order by s.standings_date
        ) as prev_standings_date
    from standings as s

),

final as (

    select
        -- Keys
        s.team_id,
        s.season,
        s.standings_date,

        -- Team context
        t.team_name,
        t.team_abbr,
        s.league_id,
        lg.league_name,
        lg.league_abbr,
        s.division_id,
        div.division_name,
        div.division_abbr,

        -- Record
        s.division_rank,
        s.wins,
        s.losses,
        s.wins + s.losses as games_played,
        round(s.win_pct, 3) as win_pct,
        s.games_back,
        s.wildcard_games_back,

        -- Streaks and recent performance
        s.streak,
        s.last_ten_record,

        -- Splits
        s.home_wins,
        s.home_losses,
        s.away_wins,
        s.away_losses,
        case
            when s.home_wins + s.home_losses > 0
            then round(safe_divide(s.home_wins, s.home_wins + s.home_losses), 3)
        end as home_win_pct,
        case
            when s.away_wins + s.away_losses > 0
            then round(safe_divide(s.away_wins, s.away_wins + s.away_losses), 3)
        end as away_win_pct,

        -- Run production
        s.runs_scored,
        s.runs_allowed,
        s.run_differential,
        case
            when s.wins + s.losses > 0
            then round(safe_divide(s.runs_scored, s.wins + s.losses), 2)
        end as runs_scored_per_game,
        case
            when s.wins + s.losses > 0
            then round(safe_divide(s.runs_allowed, s.wins + s.losses), 2)
        end as runs_allowed_per_game,

        -- Pythagorean expected win%
        round(
            safe_divide(
                power(cast(s.runs_scored as float64), 2),
                power(cast(s.runs_scored as float64), 2) + power(cast(s.runs_allowed as float64), 2)
            ),
        3) as pythagorean_win_pct,

        -- Luck factor (actual win% - expected win%)
        round(
            s.win_pct - safe_divide(
                power(cast(s.runs_scored as float64), 2),
                power(cast(s.runs_scored as float64), 2) + power(cast(s.runs_allowed as float64), 2)
            ),
        3) as luck_factor,

        -- Momentum (wins/losses since previous snapshot)
        s.wins - s.prev_wins as wins_since_last,
        s.losses - s.prev_losses as losses_since_last,
        case
            when (s.wins - s.prev_wins) + (s.losses - s.prev_losses) > 0
            then round(
                safe_divide(
                    s.wins - s.prev_wins,
                    (s.wins - s.prev_wins) + (s.losses - s.prev_losses)
                ),
            3)
        end as win_pct_since_last,
        s.prev_standings_date,

        -- Playoff positioning helpers
        case
            when s.division_rank = 1 then true
            else false
        end as is_division_leader,
        case
            when s.division_rank <= 3 and coalesce(s.wildcard_games_back, 0) <= 0 then true
            when s.wildcard_games_back is not null and s.wildcard_games_back <= 0 then true
            else false
        end as is_in_playoff_position,

        -- Metadata
        current_timestamp() as loaded_at

    from standings_with_prev as s
    left join teams as t
        on s.team_id = t.team_id
        and s.season = t.season
    left join leagues as lg
        on s.league_id = lg.league_id
    left join divisions as div
        on s.division_id = div.division_id

)

select * from final
