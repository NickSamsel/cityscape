{% docs mlb_ml_mlb_final_features %}
Feature set for MLB hit-probability modeling.

Grain: one row per batter per game, with an opposing starting pitcher (when available).
Includes engineered rolling form metrics, pitcher rolling metrics, batter-vs-pitcher matchup history, and strike-zone matchup features.

Common uses:
- Training data set (includes `got_hit` target)
- Scoring / prediction feature set (drop/ignore `got_hit`)
{% enddocs %}

{% docs mlb_ml_got_hit %}
Binary training target indicating whether the batter recorded at least one hit in the game.

Values:
- 1: batter `hits >= 1`
- 0: batter `hits = 0`
{% enddocs %}

{% docs mlb_ml_rolling_batting_avg_L7 %}
Rolling batting average over the last 7 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_rolling_batting_avg_L15 %}
Rolling batting average over the last 15 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_rolling_batting_avg_L30 %}
Rolling batting average over the last 30 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_games_with_hit_L5 %}
Count of games with at least one hit over the last 5 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_obp_L30 %}
Rolling on-base percentage over the last 30 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_slg_L30 %}
Rolling slugging percentage over the last 30 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_exit_velo_L15 %}
Rolling average exit velocity over the last 15 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_hard_hit_rate_L15 %}
Rolling hard-hit rate over the last 15 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_barrel_rate_L15 %}
Rolling barrel rate over the last 15 games (including current game date) for the batter.
{% enddocs %}

{% docs mlb_ml_career_avg_vs_pitcher %}
Batter's career batting average against the given pitcher across all recorded matchups.

Calculated as total hits / total at-bats with a minimum sample size applied in the matchup table.
{% enddocs %}

{% docs mlb_ml_zone_matchup_score %}
Overall strike-zone matchup score summarizing how well the batter performs in zones where the pitcher tends to locate pitches.
Higher values indicate a more favorable matchup for the hitter.
{% enddocs %}

{% docs mlb_ml_normalized_zone_score %}
Normalized version of `zone_matchup_score` intended to be comparable across seasons / players.
{% enddocs %}

{% docs mlb_ml_max_zone_advantage %}
Maximum per-zone advantage for the batter vs pitcher, capturing the most favorable zone interaction.
{% enddocs %}

{% docs mlb_ml_high_zone_matchup %}
Regional zone matchup score for pitches in the upper portion of the zone.
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_middle_zone_matchup %}
Regional zone matchup score for pitches in the middle portion of the zone.
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_low_zone_matchup %}
Regional zone matchup score for pitches in the lower portion of the zone.
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_inside_zone_matchup %}
Regional zone matchup score for pitches on the inside part of the zone (relative to the batter).
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_outside_zone_matchup %}
Regional zone matchup score for pitches on the outside part of the zone (relative to the batter).
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_heart_zone_matchup %}
Regional zone matchup score for pitches in the "heart" of the strike zone.
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_overall_zone_matchup %}
Overall (weighted) regional zone matchup score combining multiple regions.
Higher values indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}

{% docs mlb_ml_hitter_high_success %}
Hitter success rate profile for high pitches (aggregated by season).
{% enddocs %}

{% docs mlb_ml_hitter_low_success %}
Hitter success rate profile for low pitches (aggregated by season).
{% enddocs %}

{% docs mlb_ml_hitter_inside_success %}
Hitter success rate profile for inside pitches (aggregated by season).
{% enddocs %}

{% docs mlb_ml_hitter_outside_success %}
Hitter success rate profile for outside pitches (aggregated by season).
{% enddocs %}

{% docs mlb_ml_pitcher_high_freq %}
Pitcher location tendency: share of pitches in high region (aggregated by season).
{% enddocs %}

{% docs mlb_ml_pitcher_low_freq %}
Pitcher location tendency: share of pitches in low region (aggregated by season).
{% enddocs %}

{% docs mlb_ml_pitcher_inside_freq %}
Pitcher location tendency: share of pitches in inside region (aggregated by season).
{% enddocs %}

{% docs mlb_ml_pitcher_outside_freq %}
Pitcher location tendency: share of pitches in outside region (aggregated by season).
{% enddocs %}

{% docs mlb_ml_favorable_high %}
Derived binary feature indicating the matchup appears favorable for the hitter specifically in the high region.
{% enddocs %}

{% docs mlb_ml_favorable_outside %}
Derived binary feature indicating the matchup appears favorable for the hitter specifically in the outside region.
{% enddocs %}

{% docs mlb_ml_pitcher_era_L5 %}
Pitcher's rolling ERA over the last 5 starts (including current game date).
{% enddocs %}

{% docs mlb_ml_pitcher_whip_L5 %}
Pitcher's rolling WHIP over the last 5 starts (including current game date).
{% enddocs %}

{% docs mlb_ml_pitcher_fip_L15 %}
Pitcher's rolling FIP over the last 15 days (including current game date).
{% enddocs %}

{% docs mlb_ml_home_vs_away %}
Home/away indicator for the batter's team.

Values:
- 1: batter's team is the home team
- 0: batter's team is the away team
{% enddocs %}


{% docs mlb_ml_mlb_matchups %}
Aggregated batter vs pitcher matchup history.

Grain: one row per batter_id + pitcher_id.
Includes career totals, recent (last 3 seasons) totals, and last matchup metadata.
{% enddocs %}

{% docs mlb_ml_total_matchups %}
Number of games where the batter and pitcher faced each other (as joined via opposing teams in the same game).
{% enddocs %}

{% docs mlb_ml_games_with_hit %}
Number of matchups (games) where the batter recorded at least one hit against the pitcher.
{% enddocs %}

{% docs mlb_ml_total_hits %}
Total hits recorded by the batter in the sampled matchups against the pitcher.
{% enddocs %}

{% docs mlb_ml_total_at_bats %}
Total at-bats recorded by the batter in the sampled matchups against the pitcher.
{% enddocs %}

{% docs mlb_ml_total_home_runs %}
Total home runs recorded by the batter in the sampled matchups against the pitcher.
{% enddocs %}

{% docs mlb_ml_total_strikeouts %}
Total strikeouts recorded by the batter in the sampled matchups against the pitcher.
{% enddocs %}

{% docs mlb_ml_recent_hits %}
Total hits in matchups occurring in the last 3 seasons (relative to current date).
{% enddocs %}

{% docs mlb_ml_recent_at_bats %}
Total at-bats in matchups occurring in the last 3 seasons (relative to current date).
{% enddocs %}

{% docs mlb_ml_last_matchup_date %}
Game date of the most recent recorded matchup between the batter and pitcher.
{% enddocs %}

{% docs mlb_ml_last_matchup_hits %}
Hits recorded by the batter in the most recent recorded matchup against the pitcher.
{% enddocs %}


{% docs mlb_ml_mlb_rolling_batter_stats %}
Rolling (windowed) batter performance features derived from game-by-game batting stats.

Grain: one row per player_id + game_date.
Windows are computed over the player's own game dates (ordered by game_date).
{% enddocs %}

{% docs mlb_ml_hits_L7 %}
Rolling average of hits over the last 7 games.
{% enddocs %}

{% docs mlb_ml_avg_L7 %}
Rolling average of batting average (AVG) over the last 7 games.
{% enddocs %}

{% docs mlb_ml_games_with_hit_L7 %}
Rolling count of games with at least one hit over the last 7 games.
{% enddocs %}

{% docs mlb_ml_hits_L15 %}
Rolling average of hits over the last 15 games.
{% enddocs %}

{% docs mlb_ml_avg_L15 %}
Rolling average of batting average (AVG) over the last 15 games.
{% enddocs %}

{% docs mlb_ml_hits_L30 %}
Rolling average of hits over the last 30 games.
{% enddocs %}

{% docs mlb_ml_avg_L30 %}
Rolling average of batting average (AVG) over the last 30 games.
{% enddocs %}

{% docs mlb_ml_k_rate_L15 %}
Rolling average strikeout rate over the last 15 games.
{% enddocs %}

{% docs mlb_ml_bb_rate_L15 %}
Rolling average walk rate over the last 15 games.
{% enddocs %}

{% docs mlb_ml_total_hits_L3 %}
Rolling sum of hits over the last 3 games.
{% enddocs %}


{% docs mlb_ml_mlb_rolling_pitcher_stats %}
Rolling (windowed) pitcher performance features derived from game-by-game pitching stats.

Grain: one row per pitcher_id + game_date.
Windows are computed over the pitcher's own game dates (ordered by game_date).
{% enddocs %}

{% docs mlb_ml_era_L5 %}
Rolling average ERA over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_whip_L5 %}
Rolling average WHIP over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_k9_L5 %}
Rolling average strikeouts per 9 innings (K/9) over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_bb9_L5 %}
Rolling average walks per 9 innings (BB/9) over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_fip_L15 %}
Rolling average FIP over the last 15 days.
{% enddocs %}

{% docs mlb_ml_velo_L15 %}
Rolling average pitch velocity over the last 15 days.
{% enddocs %}

{% docs mlb_ml_quality_starts_L5 %}
Rolling count of quality starts over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_k_pct_L5 %}
Rolling average strikeout percentage over the last 5 starts.
{% enddocs %}

{% docs mlb_ml_zone_rate_L5 %}
Rolling average zone rate over the last 5 starts.
{% enddocs %}


{% docs mlb_ml_mlb_zone_matchup %}
Regional strike-zone matchup features by batter, pitcher, and season.

This model combines:
- Batter success rates by zone region
- Pitcher pitch-location frequencies by zone region

Grain: one row per player_id (batter) + pitcher_id + season.
Higher matchup scores indicate a more favorable hitter matchup given pitcher tendencies.
{% enddocs %}


{% docs mlb_ml_mlb_daily_predictions %}
Daily MLB batter hit predictions produced by the modeling pipeline.

This model is intended to store scoring outputs (predicted probabilities and/or classifications) keyed by batter and game context.
Column-level documentation should be added once the model SQL is implemented.
{% enddocs %}
