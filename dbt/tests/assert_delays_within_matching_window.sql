-- Every matched delay must fall inside the configured matching window.
select *
from {{ ref('fct_stop_delays') }}
where abs(delay_seconds) > {{ var('max_schedule_offset_minutes') }} * 60
