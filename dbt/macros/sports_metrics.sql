-- NBA Metrics

{% macro calculate_true_shooting_pct(points, field_goals_attempted, free_throws_attempted) -%}
    -- True Shooting % = Points / (2 * (FGA + 0.44 * FTA))
    {{ safe_divide(
        points,
        '2 * (' ~ field_goals_attempted ~ ' + 0.44 * ' ~ free_throws_attempted ~ ')',
        none
    ) }}
{%- endmacro %}

{% macro calculate_effective_fg_pct(field_goals_made, three_pointers_made, field_goals_attempted) -%}
    -- Effective FG% = (FGM + 0.5 * 3PM) / FGA
    {{ safe_divide(
        '(' ~ field_goals_made ~ ' + 0.5 * ' ~ three_pointers_made ~ ')',
        field_goals_attempted,
        none
    ) }}
{%- endmacro %}

{% macro calculate_assist_to_turnover_ratio(assists, turnovers) -%}
    -- Assist to Turnover Ratio = Assists / Turnovers
    {{ safe_divide(assists, turnovers, none) }}
{%- endmacro %}

-- MLB Metrics

{% macro calculate_batting_average(hits, at_bats) -%}
    -- Batting Average = Hits / At Bats
    {{ safe_divide(hits, at_bats, none) }}
{%- endmacro %}

{% macro calculate_on_base_pct(hits, walks, at_bats) -%}
    -- On-Base Percentage = (Hits + Walks) / (At Bats + Walks)
    {{ safe_divide(
        '(' ~ hits ~ ' + ' ~ walks ~ ')',
        '(' ~ at_bats ~ ' + ' ~ walks ~ ')',
        none
    ) }}
{%- endmacro %}

{% macro calculate_slugging_pct(singles, doubles, triples, home_runs, at_bats) -%}
    -- Slugging Percentage = Total Bases / At Bats
    -- Total Bases = 1B + 2*2B + 3*3B + 4*HR
    {{ safe_divide(
        '(' ~ singles ~ ' + 2 * ' ~ doubles ~ ' + 3 * ' ~ triples ~ ' + 4 * ' ~ home_runs ~ ')',
        at_bats,
        none
    ) }}
{%- endmacro %}

{% macro calculate_whip(walks, hits, innings_pitched) -%}
    -- WHIP = (Walks + Hits) / Innings Pitched
    {{ safe_divide(
        '(' ~ walks ~ ' + ' ~ hits ~ ')',
        innings_pitched,
        none
    ) }}
{%- endmacro %}

{% macro calculate_era(earned_runs, innings_pitched) -%}
    -- ERA = (Earned Runs * 9) / Innings Pitched
    {{ safe_divide(
        '(' ~ earned_runs ~ ' * 9)',
        innings_pitched,
        none
    ) }}
{%- endmacro %}

{% macro calculate_k_per_nine(strikeouts, innings_pitched) -%}
    -- Strikeouts per 9 innings = (K * 9) / IP
    {{ safe_divide(
        '(' ~ strikeouts ~ ' * 9)',
        innings_pitched,
        none
    ) }}
{%- endmacro %}

{% macro calculate_bb_per_nine(walks, innings_pitched) -%}
    -- Walks per 9 innings = (BB * 9) / IP
    {{ safe_divide(
        '(' ~ walks ~ ' * 9)',
        innings_pitched,
        none
    ) }}
{%- endmacro %}
