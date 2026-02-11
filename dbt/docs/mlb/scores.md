{% docs mlb_home_score %}
The total runs scored by the home team in the game. This is an integer value representing the final or current score.
{% enddocs %}

{% docs mlb_away_score %}
The total runs scored by the away team in the game. This is an integer value representing the final or current score.
{% enddocs %}

{% docs mlb_winning_team_id %}
Unique identifier for the team that won the game. This is determined by comparing home and away scores.
{% enddocs %}

{% docs mlb_losing_team_id %}
Unique identifier for the team that lost the game. This is determined by comparing home and away scores.
{% enddocs %}

{% docs mlb_winner %}
Indicates whether the home or away team won the game. Values are 'home', 'away', or null for ties.
{% enddocs %}

{% docs mlb_score_differential %}
The absolute difference between the winning and losing team's scores. Calculated as abs(home_score - away_score).
{% enddocs %}

{% docs mlb_total_runs %}
The total runs scored by both teams combined in the game. Calculated as home_score + away_score.
{% enddocs %}
