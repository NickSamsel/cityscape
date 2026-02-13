{% macro cast_string(column_name) -%}
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as string)
    {%- else -%}
        cast({{ column_name }} as varchar)
    {%- endif -%}
{%- endmacro %}

{% macro cast_integer(column_name) -%}
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as int64)
    {%- else -%}
        cast({{ column_name }} as integer)
    {%- endif -%}
{%- endmacro %}

{% macro cast_decimal(column_name, precision=10, scale=2) -%}
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as numeric)
    {%- else -%}
        cast({{ column_name }} as decimal({{ precision }}, {{ scale }}))
    {%- endif -%}
{%- endmacro %}

{% macro cast_date(column_name) -%}
    cast({{ column_name }} as date)
{%- endmacro %}

{% macro cast_timestamp(column_name) -%}
    {%- if target.type == 'bigquery' -%}
        cast({{ column_name }} as timestamp)
    {%- else -%}
        cast({{ column_name }} as timestamp)
    {%- endif -%}
{%- endmacro %}
