{% docs nba_player_game_stats %}
Individual player performance statistics for each NBA game. This includes points, rebounds, assists, and other key statistics. These are game-by-game records that can be aggregated for season-long analysis.
{% enddocs %}

{% docs nba_minutes %}
Minutes played by the player in the game. Format is typically "MM:SS" (e.g., "35:24").
{% enddocs %}

{% docs nba_field_goals_made %}
Number of field goals made (baskets scored from 2-point or 3-point range, excluding free throws).
{% enddocs %}

{% docs nba_field_goals_attempted %}
Number of field goal attempts.
{% enddocs %}

{% docs nba_field_goal_pct %}
Field goal percentage. Calculated as field_goals_made / field_goals_attempted.
{% enddocs %}

{% docs nba_field_goal_percentage %}
Field goal percentage at the season level. Calculated as total_field_goals_made / total_field_goals_attempted.
{% enddocs %}

{% docs nba_three_pointers_made %}
Number of three-point field goals made.
{% enddocs %}

{% docs nba_three_pointers_attempted %}
Number of three-point field goal attempts.
{% enddocs %}

{% docs nba_three_point_pct %}
Three-point percentage. Calculated as three_pointers_made / three_pointers_attempted.
{% enddocs %}

{% docs nba_three_point_percentage %}
Three-point percentage at the season level. Calculated as total_three_pointers_made / total_three_pointers_attempted.
{% enddocs %}

{% docs nba_free_throws_made %}
Number of free throws made.
{% enddocs %}

{% docs nba_free_throws_attempted %}
Number of free throw attempts.
{% enddocs %}

{% docs nba_free_throw_pct %}
Free throw percentage. Calculated as free_throws_made / free_throws_attempted.
{% enddocs %}

{% docs nba_free_throw_percentage %}
Free throw percentage at the season level. Calculated as total_free_throws_made / total_free_throws_attempted.
{% enddocs %}

{% docs nba_offensive_rebounds %}
Number of offensive rebounds (rebounds on the offensive end).
{% enddocs %}

{% docs nba_defensive_rebounds %}
Number of defensive rebounds (rebounds on the defensive end).
{% enddocs %}

{% docs nba_total_rebounds %}
Total number of rebounds (offensive + defensive).
{% enddocs %}

{% docs nba_rebounds_per_game %}
Average rebounds per game. Calculated as total_rebounds / games_played.
{% enddocs %}

{% docs nba_assists %}
Number of assists (passes that directly lead to a made basket).
{% enddocs %}

{% docs nba_assists_per_game %}
Average assists per game. Calculated as total_assists / games_played.
{% enddocs %}

{% docs nba_steals %}
Number of steals (taking the ball from an opponent).
{% enddocs %}

{% docs nba_steals_per_game %}
Average steals per game. Calculated as total_steals / games_played.
{% enddocs %}

{% docs nba_blocks %}
Number of blocked shots.
{% enddocs %}

{% docs nba_blocks_per_game %}
Average blocks per game. Calculated as total_blocks / games_played.
{% enddocs %}

{% docs nba_turnovers %}
Number of turnovers (losing possession of the ball).
{% enddocs %}

{% docs nba_turnovers_per_game %}
Average turnovers per game. Calculated as total_turnovers / games_played.
{% enddocs %}

{% docs nba_personal_fouls %}
Number of personal fouls committed.
{% enddocs %}

{% docs nba_points %}
Total points scored.
{% enddocs %}

{% docs nba_plus_minus %}
Plus-minus statistic (point differential when player is on the court).
{% enddocs %}

{% docs nba_assist_to_turnover_ratio %}
Ratio of assists to turnovers. Calculated as total_assists / total_turnovers. Higher values indicate better ball handling.
{% enddocs %}

{% docs nba_defensive_plays_per_game %}
Average defensive plays (steals + blocks) per game.
{% enddocs %}

{% docs nba_true_shooting_percentage %}
True shooting percentage (TS%). Accounts for 2-point field goals, 3-point field goals, and free throws. Calculated as Points / (2 * (FGA + 0.44 * FTA)).
{% enddocs %}

{% docs nba_effective_field_goal_percentage %}
Effective field goal percentage (eFG%). Adjusts for the fact that 3-pointers are worth more than 2-pointers. Calculated as (FGM + 0.5 * 3PM) / FGA.
{% enddocs %}

{% docs nba_total_field_goals_made %}
Total field goals made across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_field_goals_attempted %}
Total field goal attempts across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_three_pointers_made %}
Total three-pointers made across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_three_pointers_attempted %}
Total three-point attempts across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_free_throws_made %}
Total free throws made across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_free_throws_attempted %}
Total free throw attempts across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_offensive_rebounds %}
Total offensive rebounds across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_defensive_rebounds %}
Total defensive rebounds across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_assists %}
Total assists across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_steals %}
Total steals across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_blocks %}
Total blocks across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_turnovers %}
Total turnovers across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_personal_fouls %}
Total personal fouls across all games in the aggregation period.
{% enddocs %}

{% docs nba_total_points %}
Total points scored across all games in the aggregation period.
{% enddocs %}
