{% docs mlb_team_id %}
Unique identifier for an MLB team. This is a string value that uniquely identifies each team in the league.
{% enddocs %}

{% docs mlb_team_name %}
The full name of the MLB team (e.g., "New York Yankees", "Los Angeles Dodgers"). This is the official team name.
{% enddocs %}

{% docs mlb_team_abbr %}
The abbreviated name or code for the MLB team (e.g., "NYY", "LAD"). This is typically a 2-3 character code used for display purposes.
{% enddocs %}

{% docs mlb_home_team_id %}
Unique identifier for the home team in the game. This is a string value that links to the team's record.
{% enddocs %}

{% docs mlb_away_team_id %}
Unique identifier for the away (visiting) team in the game. This is a string value that links to the team's record.
{% enddocs %}

{% docs mlb_home_team_name %}
The full name of the home team in the game (e.g., "New York Yankees", "Los Angeles Dodgers"). This is enriched from the teams dimension.
{% enddocs %}

{% docs mlb_away_team_name %}
The full name of the away team in the game (e.g., "New York Yankees", "Los Angeles Dodgers"). This is enriched from the teams dimension.
{% enddocs %}

{% docs mlb_home_team_abbr %}
The abbreviated name or code for the home team in the game (e.g., "NYY", "LAD"). This is enriched from the teams dimension.
{% enddocs %}

{% docs mlb_away_team_abbr %}
The abbreviated name or code for the away team in the game (e.g., "NYY", "LAD"). This is enriched from the teams dimension.
{% enddocs %}

{% docs mlb_primary_home_team_id %}
Team ID for the primary home team associated with a venue. Derived by counting regular-season home games per venue-season.
{% enddocs %}

{% docs mlb_primary_home_team_name %}
Team name for the primary home team associated with a venue. Derived by counting regular-season home games per venue-season.
{% enddocs %}
