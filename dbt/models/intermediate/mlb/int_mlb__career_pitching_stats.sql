{{-
  config(
    materialized='table',
    tags=["intermediate", "mlb"]
  )
-}}

-- Aggregate career pitching statistics by player
-- Combines all game-level pitching stats into career totals

with pitching_stats as (

    select * from {{ ref('int_mlb__player_pitching_stats_enriched') }}

),

career_pitching as (

    select
        player_id,
        
        -- Games and appearances
        count(distinct game_id) as career_games_pitched,
        
        -- Core counting stats
        sum(coalesce(pitches, 0)) as career_pitches,
        sum(coalesce(strikes, 0)) as career_strikes,
        sum(coalesce(hits, 0)) as career_hits_allowed,
        sum(coalesce(runs, 0)) as career_runs_allowed,
        sum(coalesce(earned_runs, 0)) as career_earned_runs,
        sum(coalesce(walks, 0)) as career_walks_allowed,
        sum(coalesce(strikeouts, 0)) as career_strikeouts,
        sum(coalesce(home_runs, 0)) as career_home_runs_allowed,
        
        -- Parse innings pitched (format: "6.1" = 6 1/3 innings)
        sum(
            cast(split(innings_pitched, '.')[safe_offset(0)] as int64) +
            safe_divide(cast(split(innings_pitched, '.')[safe_offset(1)] as int64), 3)
        ) as career_innings_pitched,
        
        -- Last game date
        max(game_date) as last_game_date

    from pitching_stats
    where innings_pitched is not null
    group by player_id

),

-- Calculate advanced metrics
career_pitching_with_metrics as (

    select
        *,
        
        -- ERA = (Earned Runs / Innings Pitched) * 9
        safe_divide(career_earned_runs, career_innings_pitched) * 9 as career_era,
        
        -- WHIP = (Walks + Hits) / Innings Pitched
        safe_divide(
            career_walks_allowed + career_hits_allowed,
            career_innings_pitched
        ) as career_whip,
        
        -- K/9 = (Strikeouts / Innings Pitched) * 9
        safe_divide(career_strikeouts, career_innings_pitched) * 9 as career_k_per_9,
        
        -- BB/9 = (Walks / Innings Pitched) * 9
        safe_divide(career_walks_allowed, career_innings_pitched) * 9 as career_bb_per_9,
        
        -- K/BB ratio
        safe_divide(career_strikeouts, career_walks_allowed) as career_k_bb_ratio,
        
        -- Strike percentage
        safe_divide(career_strikes, career_pitches) as career_strike_pct

    from career_pitching

)

select * from career_pitching_with_metrics
