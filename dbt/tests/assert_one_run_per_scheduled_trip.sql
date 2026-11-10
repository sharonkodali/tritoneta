-- A scheduled trip on a given day can only be operated by one vehicle run.
select service_date, trip_id, count(distinct run_id) as runs
from {{ ref('fct_stop_delays') }}
group by all
having count(distinct run_id) > 1
