{% docs mlb_play_id %}
Unique identifier for a pitch or batted ball event, constructed as game_id + at-bat index + pitch number.
{% enddocs %}

{% docs mlb_at_bat_index %}
Sequential at-bat number within the game.
{% enddocs %}

{% docs mlb_pitch_number %}
Sequential pitch number within the at-bat.
{% enddocs %}

{% docs mlb_pitcher_id %}
MLB player ID for the pitcher in this matchup.
{% enddocs %}

{% docs mlb_pitcher_name %}
Full name of the pitcher.
{% enddocs %}

{% docs mlb_pitcher_hand %}
Pitcher's throwing hand: "L" for left, "R" for right.
{% enddocs %}

{% docs mlb_pitcher_age %}
Pitcher's age on the game date.
{% enddocs %}

{% docs mlb_batter_id %}
MLB player ID for the batter in this matchup.
{% enddocs %}

{% docs mlb_batter_name %}
Full name of the batter.
{% enddocs %}

{% docs mlb_batter_hand %}
Batter's hitting side: "L" for left, "R" for right.
{% enddocs %}

{% docs mlb_batter_age %}
Batter's age on the game date.
{% enddocs %}

{% docs mlb_pitcher_batter_handedness %}
Handedness matchup classification: "Same" (e.g., RHP vs RHB) or "Opposite" (e.g., RHP vs LHB). Opposite-handed matchups generally favor the batter.
{% enddocs %}

{% docs mlb_pitch_type %}
Pitch type code (e.g., FF=four-seam fastball, SI=sinker, SL=slider, CU=curveball, CH=changeup).
{% enddocs %}

{% docs mlb_pitch_type_description %}
Full descriptive name of the pitch type (e.g., "4-Seam Fastball", "Slider", "Curveball").
{% enddocs %}

{% docs mlb_release_speed %}
Pitch velocity at release point in miles per hour. Fastballs typically 90-100+ mph, breaking balls 70-85 mph.
{% enddocs %}

{% docs mlb_release_spin_rate %}
Pitch spin rate at release in revolutions per minute (rpm). Higher spin creates more movement. Fastballs: 2200-2800 rpm, curves: 2500-3000 rpm.
{% enddocs %}

{% docs mlb_release_extension %}
Pitcher's release point extension toward home plate in feet. Longer extension effectively reduces the batter's reaction time.
{% enddocs %}

{% docs mlb_zone %}
Strike zone location grid. Zones 1-9 map to a 3x3 grid within the strike zone; zones 11+ indicate locations outside the zone.
{% enddocs %}

{% docs mlb_in_strike_zone %}
Boolean flag indicating whether the pitch was located within the strike zone.
{% enddocs %}

{% docs mlb_plate_x %}
Horizontal pitch location at the plate in feet from the center. Negative values are toward the catcher's left, positive toward the right.
{% enddocs %}

{% docs mlb_plate_z %}
Vertical pitch location at the plate in feet above the ground.
{% enddocs %}

{% docs mlb_count_strikes %}
Strike count when the pitch was thrown (0-2).
{% enddocs %}

{% docs mlb_count_balls %}
Ball count when the pitch was thrown (0-3).
{% enddocs %}

{% docs mlb_count_outs %}
Number of outs when the pitch was thrown (0-2).
{% enddocs %}

{% docs mlb_count_description %}
Pitch count as a formatted string (e.g., "2-1" for 2 balls, 1 strike).
{% enddocs %}

{% docs mlb_pitch_result %}
Pitch outcome code: S (called strike), X (in play), B (ball), F (foul), W (swinging strike).
{% enddocs %}

{% docs mlb_velocity_tier %}
Pitch velocity classification bucket: Elite (98+ mph), Above Average (95-97), Average (92-94), Below Average (88-91), Soft (<88).
{% enddocs %}

{% docs mlb_spin_tier %}
Pitch spin rate classification: High, Average, or Low.
{% enddocs %}

{% docs mlb_launch_speed %}
Exit velocity of the batted ball in miles per hour. Elite contact: 110+, hard hit: 95+, average: 85-95, weak: <85.
{% enddocs %}

{% docs mlb_launch_angle %}
Launch angle of the batted ball in degrees. Optimal for power: 25-35°, line drives: 10-25°, ground balls: <10°.
{% enddocs %}

{% docs mlb_launch_distance %}
Projected carry distance of the batted ball in feet. Home run distance typically 350-450+ feet.
{% enddocs %}

{% docs mlb_hit_location %}
Numeric field location code indicating where the ball was hit.
{% enddocs %}

{% docs mlb_hit_trajectory %}
Batted ball trajectory classification: fly_ball, line_drive, ground_ball, or popup.
{% enddocs %}

{% docs mlb_hit_result %}
Play outcome from the batted ball (e.g., Single, Double, Triple, Home Run, Field Out).
{% enddocs %}

{% docs mlb_sprint_speed %}
Runner's sprint speed in feet per second. MLB average is approximately 27 ft/sec.
{% enddocs %}

{% docs mlb_is_barrel %}
Boolean flag for a barrel — optimal exit velocity (98+ mph) and launch angle (26-30°). Barrels produce a batting average of approximately .500 and slugging of 1.500.
{% enddocs %}

{% docs mlb_is_hard_hit %}
Boolean flag for a hard-hit ball (95+ mph exit velocity). Hard-hit rate is a strong predictor of offensive production.
{% enddocs %}

{% docs mlb_exit_velo_tier %}
Exit velocity classification bucket: Elite (110+), Great (100-109), Good (95-99), Average (90-94), Below Average (80-89), Weak (<80).
{% enddocs %}

{% docs mlb_trajectory_bucket %}
Batted ball type based on launch angle: Pop Up (50+°), Fly Ball (25-49°), Line Drive (10-24°), Ground Ball (-10 to 9°), Topped (<-10°).
{% enddocs %}

{% docs mlb_quality_contact_tier %}
Contact quality classification: Barrel (optimal exit velo + angle), Hard Hit Non-Barrel (95+ mph but not barrel), Not Hard Hit (<95 mph).
{% enddocs %}

{% docs mlb_distance_bucket %}
Batted ball distance classification: 400+ ft, 350-399 ft, 300-349 ft, 250-299 ft, etc.
{% enddocs %}

{% docs mlb_is_home_run %}
Boolean flag indicating the batted ball resulted in a home run.
{% enddocs %}

{% docs mlb_is_hit %}
Boolean flag indicating the batted ball resulted in any hit (single, double, triple, or home run).
{% enddocs %}

{% docs mlb_total_batted_balls %}
Total number of batted ball events tracked by Statcast.
{% enddocs %}

{% docs mlb_games_with_batted_balls %}
Number of games where the player had batted ball events tracked by Statcast.
{% enddocs %}

{% docs mlb_max_exit_velocity %}
Maximum exit velocity (mph) recorded — a key indicator of raw power potential.
{% enddocs %}

{% docs mlb_avg_exit_velocity %}
Average exit velocity (mph) across all batted ball events — measures overall quality of contact.
{% enddocs %}

{% docs mlb_p90_exit_velocity %}
90th percentile exit velocity (mph) — measures consistency of hard contact.
{% enddocs %}

{% docs mlb_stddev_exit_velocity %}
Standard deviation of exit velocity — measures contact consistency. Lower values indicate more consistent contact.
{% enddocs %}

{% docs mlb_avg_launch_angle %}
Average launch angle (degrees) across all batted ball events.
{% enddocs %}

{% docs mlb_stddev_launch_angle %}
Standard deviation of launch angle — measures variance in batted ball trajectory.
{% enddocs %}

{% docs mlb_avg_launch_distance %}
Average projected distance (feet) of batted balls.
{% enddocs %}

{% docs mlb_max_launch_distance %}
Maximum projected distance (feet) of batted balls.
{% enddocs %}

{% docs mlb_total_barrels %}
Total barrel events (98+ mph exit velocity, 26-30° launch angle). Barrels represent optimal contact.
{% enddocs %}

{% docs mlb_total_hard_hits %}
Total hard-hit balls (95+ mph exit velocity).
{% enddocs %}

{% docs mlb_barrel_rate %}
Barrels per batted ball. MLB average is approximately 8%; elite hitters achieve 15%+.
{% enddocs %}

{% docs mlb_hard_hit_rate %}
Hard-hit balls per batted ball. MLB average is approximately 35%; elite hitters achieve 50%+.
{% enddocs %}

{% docs mlb_home_run_rate %}
Home runs per batted ball.
{% enddocs %}

{% docs mlb_avg_sprint_speed %}
Average sprint speed (ft/sec). MLB average is approximately 27 ft/sec.
{% enddocs %}

{% docs mlb_max_sprint_speed %}
Maximum sprint speed (ft/sec) recorded.
{% enddocs %}

{% docs mlb_plate_x_bin %}
Horizontal pitch location binned to 0.25 feet (4 bins per foot). Negative values are toward the catcher's left, positive toward the right.
{% enddocs %}

{% docs mlb_plate_z_bin %}
Vertical pitch location binned to 0.25 feet (4 bins per foot). Height above the ground in feet.
{% enddocs %}

{% docs mlb_pitch_result_category %}
Aggregated pitch result category: called_strike, swinging_strike, ball, foul, or in_play.
{% enddocs %}

{% docs mlb_pitch_count %}
Number of pitches in a given aggregation bucket.
{% enddocs %}

{% docs mlb_player_type %}
Classification of the player as "batter" or "pitcher" for the purpose of Statcast aggregation.
{% enddocs %}
