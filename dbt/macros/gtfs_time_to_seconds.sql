{# GTFS times are HH:MM:SS and may exceed 24:00:00 for trips running past midnight. #}
{% macro gtfs_time_to_seconds(column) -%}
    (
        cast(split_part({{ column }}, ':', 1) as integer) * 3600
        + cast(split_part({{ column }}, ':', 2) as integer) * 60
        + cast(split_part({{ column }}, ':', 3) as integer)
    )
{%- endmacro %}
