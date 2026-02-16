{% docs nba_game_event_id %}
Unique event ID within the game for this shot attempt.
{% enddocs %}

{% docs nba_period %}
Quarter or period of the game (1-4 for regulation, 5+ for overtime).
{% enddocs %}

{% docs nba_minutes_remaining %}
Minutes remaining in the period when the shot was taken.
{% enddocs %}

{% docs nba_seconds_remaining %}
Seconds remaining in the period when the shot was taken.
{% enddocs %}

{% docs nba_event_type %}
Type of shot event: "Made Shot" or "Missed Shot".
{% enddocs %}

{% docs nba_action_type %}
Specific type of shot attempt (e.g., "Jump Shot", "Layup Shot", "Dunk Shot", "Hook Shot").
{% enddocs %}

{% docs nba_shot_type %}
Shot point value classification: "2PT Field Goal" or "3PT Field Goal".
{% enddocs %}

{% docs nba_shot_zone_basic %}
Basic shot zone on the court (e.g., "Above the Break 3", "In The Paint (Non-RA)", "Mid-Range", "Restricted Area").
{% enddocs %}

{% docs nba_shot_zone_area %}
Area of the court where the shot was taken (e.g., "Left Side", "Right Side", "Center", "Back Court").
{% enddocs %}

{% docs nba_shot_zone_range %}
Distance range bucket for the shot (e.g., "Less Than 8 ft.", "8-16 ft.", "16-24 ft.", "24+ ft.").
{% enddocs %}

{% docs nba_shot_distance %}
Distance of the shot from the basket in feet.
{% enddocs %}

{% docs nba_loc_x %}
X coordinate on the court (-250 to 250, where 0 is center court).
{% enddocs %}

{% docs nba_loc_y %}
Y coordinate on the court (0 to 940, distance from baseline).
{% enddocs %}

{% docs nba_shot_attempted_flag %}
Flag indicating a shot was attempted (always 1).
{% enddocs %}

{% docs nba_shot_made_flag %}
Flag indicating whether the shot was made (1) or missed (0).
{% enddocs %}

{% docs nba_htm %}
Home team abbreviation for this game.
{% enddocs %}

{% docs nba_vtm %}
Visiting (away) team abbreviation for this game.
{% enddocs %}
