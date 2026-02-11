{% docs mlb_full_name %}
Player's full name as it appears in official MLB records (e.g., "Mike Trout", "Ronald Acuña Jr.").
{% enddocs %}

{% docs mlb_first_name %}
Player's first (given) name.
{% enddocs %}

{% docs mlb_last_name %}
Player's last (family) name.
{% enddocs %}

{% docs mlb_primary_number %}
Player's primary jersey number. This may be null if a player hasn't been assigned a number or is not currently on a roster.
{% enddocs %}

{% docs mlb_birth_date %}
Player's date of birth in YYYY-MM-DD format.
{% enddocs %}

{% docs mlb_current_age %}
Player's age calculated as of the current date or season.
{% enddocs %}

{% docs mlb_birth_city %}
City where the player was born.
{% enddocs %}

{% docs mlb_birth_state_province %}
State or province where the player was born. May be null for international players from countries without state/province divisions.
{% enddocs %}

{% docs mlb_birth_country %}
Country where the player was born (e.g., "USA", "Dominican Republic", "Japan").
{% enddocs %}

{% docs mlb_height %}
Player's height, typically stored as a string in feet and inches format (e.g., "6' 2\"").
{% enddocs %}

{% docs mlb_weight %}
Player's weight in pounds.
{% enddocs %}

{% docs mlb_primary_position_code %}
Numeric code representing the player's primary fielding position (e.g., 1 for Pitcher, 2 for Catcher, 3 for First Base, etc.).
{% enddocs %}

{% docs mlb_primary_position_name %}
Full name of the player's primary fielding position (e.g., "Pitcher", "Catcher", "Shortstop", "Outfielder").
{% enddocs %}

{% docs mlb_primary_position_abbr %}
Abbreviated code for the player's primary fielding position (e.g., "P", "C", "SS", "OF", "DH").
{% enddocs %}

{% docs mlb_bat_side_code %}
Single-character code indicating which side of the plate the player bats from: "L" for Left, "R" for Right, "S" for Switch hitter.
{% enddocs %}

{% docs mlb_bat_side_description %}
Full description of batting side (e.g., "Left", "Right", "Switch").
{% enddocs %}

{% docs mlb_pitch_hand_code %}
Single-character code indicating which hand the player throws with: "L" for Left, "R" for Right.
{% enddocs %}

{% docs mlb_pitch_hand_description %}
Full description of pitching/throwing hand (e.g., "Left", "Right").
{% enddocs %}

{% docs mlb_debut_date %}
Date of the player's first Major League Baseball game in YYYY-MM-DD format. This represents when the player officially became an MLB player.
{% enddocs %}

{% docs mlb_active %}
Boolean flag indicating whether the player is currently active in MLB. True means the player is on an active roster, false means retired or inactive.
{% enddocs %}

{% docs mlb_raw_player %}
Raw JSON data from the MLB API containing the complete player record. Useful for accessing fields not explicitly modeled in the staging layer.
{% enddocs %}
