-- Groups each vehicle's stop visits into runs: one trip around the loop.
-- A new run starts when the vehicle jumps back toward the start of the
-- stop sequence (it began another lap) or after a long gap (layover,
-- shift change, signal loss).

with visits as (
    select * from {{ ref('int_observed_stop_visits') }}
),

flagged as (
    select
        *,
        case
            when lag(arrived_at_local) over w is null then 1
            when epoch(arrived_at_local - lag(arrived_at_local) over w) > 30 * 60 then 1
            when route_id != lag(route_id) over w then 1
            -- Allow small reorderings from stops that sit close together.
            when stop_sequence < lag(stop_sequence) over w - 2 then 1
            else 0
        end as is_new_run
    from visits
    window w as (partition by vehicle_id order by arrived_at_local)
),

numbered as (
    select
        *,
        sum(is_new_run) over (
            partition by vehicle_id order by arrived_at_local
            rows between unbounded preceding and current row
        ) as run_number
    from flagged
)

select
    {{ dbt_utils_surrogate_key(['vehicle_id', 'run_number']) }} as run_id,
    visit_id,
    vehicle_id,
    route_id,
    observed_date,
    feed_version,
    stop_id,
    stop_sequence,
    arrived_at_local,
    departed_at_local,
    dwell_seconds,
    closest_distance_m,
    count(*) over (partition by vehicle_id, run_number) as stops_in_run
from numbered
