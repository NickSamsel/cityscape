{% macro cast_string(column_name) -%}
    -- Cast to string/varchar type (database-agnostic)
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as string)
    {%- else -%}
        cast({{ column_name }} as varchar)
    {%- endif -%}
{%- endmacro %}

{% macro cast_integer(column_name) -%}
    -- Cast to integer type (database-agnostic)
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as int64)
    {%- else -%}
        cast({{ column_name }} as integer)
    {%- endif -%}
{%- endmacro %}

{% macro cast_decimal(column_name, precision=10, scale=2) -%}
    -- Cast to decimal/numeric type (database-agnostic)
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as numeric)
    {%- else -%}
        cast({{ column_name }} as decimal({{ precision }}, {{ scale }}))
    {%- endif -%}
{%- endmacro %}

{% macro cast_date(column_name) -%}
    -- Cast to date type (database-agnostic)
    cast({{ column_name }} as date)
{%- endmacro %}

{% macro cast_timestamp(column_name) -%}
    -- Cast to timestamp type (database-agnostic)
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as timestamp)
    {%- else -%}
        cast({{ column_name }} as timestamp)
    {%- endif -%}
{%- endmacro %}
