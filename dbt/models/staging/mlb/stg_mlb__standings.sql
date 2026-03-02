{{-
  config(
    materialized='incremental',
    unique_key=['team_id', 'season', 'standings_date'],
    on_schema_change='sync_all_columns',
    tags=["stg", "mlb"]
  )
-}}

with source as (
    select
        cast(team_id as string) as team_id,
        cast(season as int64) as season,
        cast(standings_date as date) as standings_date,
        cast(league_id as string) as league_id,
        cast(division_id as string) as division_id,
        cast(division_rank as int64) as division_rank,
        cast(wins as int64) as wins,
        cast(losses as int64) as losses,
        cast(win_pct as float64) as win_pct,
        cast(games_back as float64) as games_back,
        cast(wildcard_games_back as float64) as wildcard_games_back,
        cast(streak as string) as streak,
        cast(last_ten_record as string) as last_ten_record,
        cast(runs_scored as int64) as runs_scored,
        cast(runs_allowed as int64) as runs_allowed,
        cast(run_differential as int64) as run_differential,
        cast(home_wins as int64) as home_wins,
        cast(home_losses as int64) as home_losses,
        cast(away_wins as int64) as away_wins,
        cast(away_losses as int64) as away_losses,
        row_number() over (
            partition by cast(team_id as string), cast(season as int64), cast(standings_date as date)
            order by cast(standings_date as date) desc
        ) as row_num
    from {{ source('raw', 'mlb_standings') }}

    {% if is_incremental() %}
    where not exists (
        select 1 from {{ this }} as existing
        where existing.team_id = cast(team_id as string)
          and existing.season = cast(season as int64)
          and existing.standings_date = cast(standings_date as date)
    )
    {% endif %}
)

select * except(row_num)
from source
where row_num = 1
