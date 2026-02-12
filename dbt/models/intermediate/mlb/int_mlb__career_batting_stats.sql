{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb"]
  )
-}}

-- Aggregate career batting statistics by player
-- Combines all game-level batting stats into career totals

with batting_stats as (

    select * from {{ ref('fct_mlb__player_batting_stats') }}

),

career_batting as (

    select
        player_id,
        
        -- Games and appearances
        count(distinct game_id) as career_games_batted,
        
        -- Core counting stats
        sum(coalesce(at_bats, 0)) as career_at_bats,
        sum(coalesce(runs, 0)) as career_runs,
        sum(coalesce(hits, 0)) as career_hits,
        sum(coalesce(doubles, 0)) as career_doubles,
        sum(coalesce(triples, 0)) as career_triples,
        sum(coalesce(home_runs, 0)) as career_home_runs,
        sum(coalesce(rbi, 0)) as career_rbi,
        sum(coalesce(stolen_bases, 0)) as career_stolen_bases,
        sum(coalesce(walks, 0)) as career_walks,
        sum(coalesce(strikeouts, 0)) as career_strikeouts,
        
        -- Calculate rate stats
        safe_divide(
            sum(coalesce(hits, 0)),
            sum(coalesce(at_bats, 0))
        ) as career_batting_avg,
        
        -- Singles calculated as hits - (2B + 3B + HR)
        sum(coalesce(hits, 0)) - sum(coalesce(doubles, 0)) - sum(coalesce(triples, 0)) - sum(coalesce(home_runs, 0)) as career_singles,
        
        -- Total bases = 1B + (2*2B) + (3*3B) + (4*HR)
        (sum(coalesce(hits, 0)) - sum(coalesce(doubles, 0)) - sum(coalesce(triples, 0)) - sum(coalesce(home_runs, 0)))
        + (2 * sum(coalesce(doubles, 0)))
        + (3 * sum(coalesce(triples, 0)))
        + (4 * sum(coalesce(home_runs, 0))) as career_total_bases,
        
        -- Last game date
        max(game_date) as last_game_date

    from batting_stats
    group by player_id

),

-- Calculate advanced metrics
career_batting_with_metrics as (

    select
        *,
        
        -- Slugging percentage = Total Bases / At Bats
        safe_divide(career_total_bases, career_at_bats) as career_slugging_pct,
        
        -- On-base percentage = (H + BB) / (AB + BB)
        safe_divide(
            career_hits + career_walks,
            career_at_bats + career_walks
        ) as career_obp,
        
        -- OPS = OBP + SLG
        safe_divide(
            career_hits + career_walks,
            career_at_bats + career_walks
        ) + safe_divide(career_total_bases, career_at_bats) as career_ops,
        
        -- Power metrics
        safe_divide(career_home_runs, career_at_bats) as career_hr_rate,
        safe_divide(career_strikeouts, career_at_bats) as career_k_rate,
        safe_divide(career_walks, career_at_bats) as career_bb_rate

    from career_batting

)

select * from career_batting_with_metrics
