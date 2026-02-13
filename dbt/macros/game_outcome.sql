{% macro calculate_winning_team(home_team_id, away_team_id, home_score, away_score) -%}
    -- Returns the team_id of the winning team, or NULL for ties
    case
        when {{ home_score }} > {{ away_score }} then {{ home_team_id }}
        when {{ away_score }} > {{ home_score }} then {{ away_team_id }}
        else null
    end
{%- endmacro %}

{% macro calculate_losing_team(home_team_id, away_team_id, home_score, away_score) -%}
    -- Returns the team_id of the losing team, or NULL for ties
    case
        when {{ home_score }} > {{ away_score }} then {{ away_team_id }}
        when {{ away_score }} > {{ home_score }} then {{ home_team_id }}
        else null
    end
{%- endmacro %}

{% macro calculate_winner_type(home_score, away_score) -%}
    -- Returns 'home', 'away', or 'tie'
    case
        when {{ home_score }} > {{ away_score }} then 'home'
        when {{ away_score }} > {{ home_score }} then 'away'
        else 'tie'
    end
{%- endmacro %}
