{% docs nba_season %}
The year representing the NBA season. This is an integer value (e.g., 2024, 2025) indicating the starting year of the season (2024-25 season would be 2024).
{% enddocs %}

{% docs nba_season_type %}
The type of NBA season. Common values include "Regular Season", "Playoffs", "Play-In Tournament", and "Preseason".
{% enddocs %}

{% docs nba_game_id %}
Unique identifier for an NBA game. This is a string value that uniquely identifies each game.
{% enddocs %}

{% docs nba_game_date %}
The date when the NBA game was played or is scheduled to be played.
{% enddocs %}

{% docs nba_status %}
The current status of the game (e.g., "Final", "Scheduled", "In Progress").
{% enddocs %}

{% docs nba_arena %}
The name of the arena or venue where the game was/is being played.
{% enddocs %}

{% docs nba_attendance %}
The number of fans in attendance at the game.
{% enddocs %}

{% docs nba_home_score %}
The final score for the home team in the game.
{% enddocs %}

{% docs nba_away_score %}
The final score for the away (visiting) team in the game.
{% enddocs %}

{% docs nba_score_differential %}
The absolute difference between the home and away scores. Calculated as ABS(home_score - away_score).
{% enddocs %}

{% docs nba_winning_team_id %}
The team ID of the team that won the game. NULL for ties or games not yet completed.
{% enddocs %}

{% docs nba_losing_team_id %}
The team ID of the team that lost the game. NULL for ties or games not yet completed.
{% enddocs %}

{% docs nba_games_played %}
The total number of games played by a player or team in the specified time period.
{% enddocs %}

{% docs nba_games_started %}
The number of games in which a player was in the starting lineup.
{% enddocs %}

{% docs nba_starter %}
Boolean flag indicating whether the player was a starter in this game.
{% enddocs %}

{% docs nba_starter_percentage %}
The percentage of games where the player started. Calculated as games_started / games_played.
{% enddocs %}
