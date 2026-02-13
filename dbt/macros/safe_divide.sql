{% macro safe_divide(numerator, denominator, default_value=0) -%}
    -- ANSI SQL compliant safe division
    -- Returns NULL when denominator is 0 or NULL by default, or custom default_value
    case
        when {{ denominator }} is null or {{ denominator }} = 0 then
            {% if default_value is none %}
                null
            {% else %}
                {{ default_value }}
            {% endif %}
        else {{ numerator }} / {{ denominator }}
    end
{%- endmacro %}
