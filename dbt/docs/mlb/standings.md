{% docs mlb_standings_date %}
Date of the standings snapshot. Standings are captured weekly for historical division race tracking.
{% enddocs %}

{% docs mlb_division_rank %}
Team's rank within their division. 1 indicates the division leader.
{% enddocs %}

{% docs mlb_wins %}
Total wins as of this date or period.
{% enddocs %}

{% docs mlb_losses %}
Total losses as of this date or period.
{% enddocs %}

{% docs mlb_games_played %}
Total games played (wins + losses).
{% enddocs %}

{% docs mlb_win_pct %}
Winning percentage. Calculated as wins / games played.
{% enddocs %}

{% docs mlb_games_back %}
Games behind the division leader. 0.0 indicates the team leads the division.
{% enddocs %}

{% docs mlb_wildcard_games_back %}
Games behind the wild card cutoff. 0.0 indicates the team is in wild card position.
{% enddocs %}

{% docs mlb_streak %}
Current winning or losing streak code (e.g., "W5" for 5-game win streak, "L3" for 3-game losing streak).
{% enddocs %}

{% docs mlb_last_ten_record %}
Record in the last 10 games (e.g., "7-3").
{% enddocs %}

{% docs mlb_home_win_pct %}
Winning percentage in home games.
{% enddocs %}

{% docs mlb_away_win_pct %}
Winning percentage in away (road) games.
{% enddocs %}

{% docs mlb_run_differential %}
Season run differential (runs scored minus runs allowed). Positive values indicate more runs scored than allowed.
{% enddocs %}

{% docs mlb_pythagorean_win_pct %}
Expected winning percentage based on the Pythagorean formula: RS^2 / (RS^2 + RA^2). Estimates true team quality independent of win/loss record.
{% enddocs %}

{% docs mlb_luck_factor %}
Difference between actual winning percentage and Pythagorean expected winning percentage. Positive values indicate the team is outperforming its run differential.
{% enddocs %}

{% docs mlb_wins_since_last %}
Wins gained since the previous standings snapshot.
{% enddocs %}

{% docs mlb_losses_since_last %}
Losses gained since the previous standings snapshot.
{% enddocs %}

{% docs mlb_win_pct_since_last %}
Winning percentage in the interval since the previous standings snapshot.
{% enddocs %}

{% docs mlb_is_division_leader %}
Boolean flag indicating whether the team leads their division.
{% enddocs %}

{% docs mlb_is_in_playoff_position %}
Boolean flag indicating whether the team is in a playoff spot (division leader or wild card position).
{% enddocs %}
