{% docs mlb_player_batting_stats %}
Individual player batting performance statistics for each MLB game. This includes at-bats, hits, home runs, RBIs, and other offensive statistics. These are game-by-game records that can be aggregated for season-long analysis.
{% enddocs %}

{% docs mlb_player_pitching_stats %}
Individual player pitching performance statistics for each MLB game. This includes innings pitched, strikeouts, earned runs, and other pitching metrics. These are game-by-game records that can be aggregated for season-long analysis.
{% enddocs %}

{% docs mlb_player_id %}
Unique identifier for an MLB player from the MLB Stats API.
{% enddocs %}

{% docs mlb_player_name %}
The player's full name as provided by the MLB Stats API.
{% enddocs %}

{% docs mlb_batting_order %}
The batting order position for the player in this game. Typically represented as multiples of 100 (100, 200, 300, etc.) where 100 is the leadoff hitter.
{% enddocs %}

{% docs mlb_at_bats %}
Number of official at-bats for the player in this game. This excludes walks, hit-by-pitch, sacrifice flies, and sacrifice bunts.
{% enddocs %}

{% docs mlb_total_bases %}
Total bases accumulated by the player in this game. Calculated as: 1B + (2B × 2) + (3B × 3) + (HR × 4).
{% enddocs %}

{% docs mlb_innings_pitched %}
Number of innings pitched in this game. Uses MLB's standard notation where .1 represents 1/3 inning and .2 represents 2/3 inning (e.g., "5.2" means 5 and 2/3 innings).
{% enddocs %}

{% docs mlb_whip %}
Walks plus Hits per Inning Pitched (WHIP) for this game. Calculated as (Walks + Hits) / Innings Pitched. Lower values indicate better performance.
{% enddocs %}

{% docs mlb_strike_percentage %}
Percentage of total pitches that were strikes in this game. Calculated as (Strikes / Total Pitches) × 100.
{% enddocs %}

{% docs mlb_player_age %}
The player's age at the time of the game, calculated from their birth date.
{% enddocs %}

{% docs mlb_player_career_length %}
The number of years between the player's MLB debut and the game date, representing their career length in years.
{% enddocs %}

{% docs mlb_position %}
The defensive position the player played in this game (e.g., "LF", "SS", "C", "P", "DH").
{% enddocs %}

{% docs mlb_runs %}
Number of runs scored by the player in this game.
{% enddocs %}

{% docs mlb_hits %}
Number of hits recorded by the player in this game. Includes singles, doubles, triples, and home runs.
{% enddocs %}

{% docs mlb_doubles %}
Number of doubles (2B) hit by the player in this game.
{% enddocs %}

{% docs mlb_triples %}
Number of triples (3B) hit by the player in this game.
{% enddocs %}

{% docs mlb_home_runs %}
Number of home runs (HR) hit by the player in this game.
{% enddocs %}

{% docs mlb_rbi %}
Runs batted in - the number of runs that scored as a result of the player's at-bats in this game.
{% enddocs %}

{% docs mlb_stolen_bases %}
Number of successful stolen bases by the player in this game.
{% enddocs %}

{% docs mlb_walks %}
Number of walks (bases on balls) drawn by the player in this game. For pitchers, this is the number of walks allowed.
{% enddocs %}

{% docs mlb_strikeouts %}
Number of strikeouts. For batters, this is times struck out. For pitchers, this is batters struck out.
{% enddocs %}

{% docs mlb_left_on_base %}
Number of runners left on base when the player made an out in this game.
{% enddocs %}

{% docs mlb_singles %}
Number of singles (1B) hit by the player in this game. Calculated as Hits - Doubles - Triples - Home Runs.
{% enddocs %}

{% docs mlb_plate_appearances %}
Total number of plate appearances in this game. Calculated as At Bats + Walks + other plate appearances.
{% enddocs %}

{% docs mlb_extra_base_hits %}
Number of extra-base hits (doubles, triples, and home runs) in this game. Calculated as Doubles + Triples + Home Runs.
{% enddocs %}

{% docs mlb_batting_avg_game %}
Batting average for this specific game. Calculated as Hits / At Bats. Returns null if no at-bats.
{% enddocs %}

{% docs mlb_slugging_pct_game %}
Slugging percentage for this specific game. Calculated as Total Bases / At Bats. Returns null if no at-bats.
{% enddocs %}

{% docs mlb_iso %}
Isolated power (ISO) for this game. Measures raw power by calculating Slugging Percentage - Batting Average.
{% enddocs %}

{% docs mlb_babip %}
Batting Average on Balls In Play. Calculated as (Hits - Home Runs) / (At Bats - Strikeouts - Home Runs). Measures batting average on balls that stay in the field of play.
{% enddocs %}

{% docs mlb_walk_rate %}
Walk rate for this game. Calculated as Walks / Plate Appearances. Indicates plate discipline.
{% enddocs %}

{% docs mlb_strikeout_rate %}
Strikeout rate for this game. Calculated as Strikeouts / Plate Appearances. Indicates contact ability.
{% enddocs %}

{% docs mlb_bb_k_ratio %}
Walk-to-strikeout ratio for this game. Calculated as Walks / Strikeouts. Higher values indicate better plate discipline.
{% enddocs %}

{% docs mlb_power_factor %}
Power factor metric for this game. Calculated as (Home Runs + Extra Base Hits) / At Bats. Measures overall power output.
{% enddocs %}

{% docs mlb_avg %}
Batting average. Calculated as Hits / At Bats. The traditional measure of batting success.
{% enddocs %}

{% docs mlb_obp %}
On-base percentage. Calculated as (Hits + Walks) / (At Bats + Walks). Measures how frequently a player reaches base.
{% enddocs %}

{% docs mlb_slg %}
Slugging percentage. Calculated as Total Bases / At Bats. Measures the power of a hitter.
{% enddocs %}

{% docs mlb_ops %}
On-base plus slugging. Calculated as OBP + SLG. A comprehensive measure of a player's offensive contribution.
{% enddocs %}

{% docs mlb_innings_pitched_decimal %}
Innings pitched converted to decimal format. Converts MLB's fractional notation (e.g., 5.2) to true decimal (e.g., 5.67).
{% enddocs %}

{% docs mlb_earned_runs %}
Number of earned runs allowed by the pitcher in this game. Excludes runs that scored due to defensive errors.
{% enddocs %}

{% docs mlb_pitches %}
Total number of pitches thrown by the pitcher in this game.
{% enddocs %}

{% docs mlb_strikes %}
Total number of strikes thrown by the pitcher in this game, including called strikes, swinging strikes, and foul balls.
{% enddocs %}

{% docs mlb_k_per_nine %}
Strikeouts per nine innings. Calculated as (Strikeouts / Innings Pitched) × 9. Measures strikeout rate normalized to a full game.
{% enddocs %}

{% docs mlb_bb_per_nine %}
Walks per nine innings. Calculated as (Walks / Innings Pitched) × 9. Measures walk rate normalized to a full game.
{% enddocs %}

{% docs mlb_era %}
Earned run average. Calculated as (Earned Runs / Innings Pitched) × 9. The primary measure of pitching effectiveness.
{% enddocs %}

{% docs mlb_k_bb_ratio %}
Strikeout-to-walk ratio. Calculated as Strikeouts / Walks. Higher values indicate better control and command.
{% enddocs %}

{% docs mlb_hr_per_nine %}
Home runs allowed per nine innings. Calculated as (Home Runs / Innings Pitched) × 9.
{% enddocs %}

{% docs mlb_h_per_nine %}
Hits allowed per nine innings. Calculated as (Hits / Innings Pitched) × 9.
{% enddocs %}

{% docs mlb_fip %}
Fielding Independent Pitching. Calculated as ((13 × HR) + (3 × BB) - (2 × K)) / IP + constant. Measures a pitcher's effectiveness independent of defense.
{% enddocs %}

{% docs mlb_pitches_per_inning %}
Average number of pitches thrown per inning. Calculated as Pitches / Innings Pitched. Indicates efficiency.
{% enddocs %}

{% docs mlb_k_percentage %}
Strikeout percentage. Calculated as Strikeouts / Batters Faced. Measures the rate at which a pitcher strikes out batters.
{% enddocs %}

{% docs mlb_is_quality_start %}
Boolean flag indicating whether the pitcher had a quality start (6+ innings pitched with 3 or fewer earned runs).
{% enddocs %}

