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
