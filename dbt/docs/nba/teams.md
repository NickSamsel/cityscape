{% docs nba_team_id %}
Unique identifier for an NBA team. This is a string value that uniquely identifies each team in the league.
{% enddocs %}

{% docs nba_team_name %}
The full name of the NBA team (e.g., "Los Angeles Lakers", "Boston Celtics"). This is the official team name.
{% enddocs %}

{% docs nba_team_abbr %}
The abbreviated name or code for the NBA team (e.g., "LAL", "BOS"). This is typically a 3 character code used for display purposes.
{% enddocs %}

{% docs nba_team_city %}
The city where the NBA team is based (e.g., "Los Angeles", "Boston").
{% enddocs %}

{% docs nba_home_team_id %}
Unique identifier for the home team in the game. This is a string value that links to the team's record.
{% enddocs %}

{% docs nba_away_team_id %}
Unique identifier for the away (visiting) team in the game. This is a string value that links to the team's record.
{% enddocs %}

{% docs nba_home_team_name %}
The full name of the home team in the game. This is enriched from the teams dimension.
{% enddocs %}

{% docs nba_away_team_name %}
The full name of the away team in the game. This is enriched from the teams dimension.
{% enddocs %}

{% docs nba_home_team_abbr %}
The abbreviated name or code for the home team in the game. This is enriched from the teams dimension.
{% enddocs %}

{% docs nba_away_team_abbr %}
The abbreviated name or code for the away team in the game. This is enriched from the teams dimension.
{% enddocs %}

{% docs nba_year_founded %}
The year the NBA team was founded or established.
{% enddocs %}

{% docs nba_total_wins %}
Total number of wins for a team in the specified time period.
{% enddocs %}

{% docs nba_total_losses %}
Total number of losses for a team in the specified time period.
{% enddocs %}

{% docs nba_win_percentage %}
Win percentage for a team. Calculated as total_wins / games_played.
{% enddocs %}

{% docs nba_home_wins %}
Number of wins at home for a team.
{% enddocs %}

{% docs nba_home_losses %}
Number of losses at home for a team.
{% enddocs %}

{% docs nba_away_wins %}
Number of wins on the road for a team.
{% enddocs %}

{% docs nba_away_losses %}
Number of losses on the road for a team.
{% enddocs %}

{% docs nba_points_per_game %}
Average points scored per game by a player or team.
{% enddocs %}

{% docs nba_points_allowed_per_game %}
Average points allowed per game by a team.
{% enddocs %}

{% docs nba_point_differential %}
Total point differential (points scored minus points allowed) for a team.
{% enddocs %}
