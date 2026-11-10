{# Minimal stand-in for dbt_utils.generate_surrogate_key, to avoid a package dependency. #}
{% macro dbt_utils_surrogate_key(columns) -%}
    md5(concat_ws('|', {% for c in columns %}coalesce(cast({{ c }} as varchar), '∅'){% if not loop.last %}, {% endif %}{% endfor %}))
{%- endmacro %}
