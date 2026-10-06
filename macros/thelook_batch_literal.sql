{% macro thelook_batch_literal() %}
    {% set batch_id = var('thelook_batch_id') | string %}
    {% if not modules.re.fullmatch('[0-9]{8}T[0-9]{6}Z', batch_id) %}
        {{ exceptions.raise_compiler_error('thelook_batch_id must use YYYYMMDDTHHMMSSZ format') }}
    {% endif %}
    {{ return("'" ~ batch_id ~ "'") }}
{% endmacro %}
