-- Reliability scorecard per route and stop: punctuality against the
-- schedule, plus observed vs scheduled headways (the gap between
-- consecutive shuttles, which is what riders feel on frequent routes).
-- On-time follows the common transit standard: no more than 1 min early
-- or 5 min late.

with delays as (
    select * from {{ ref('fct_stop_delays') }}
),

observed_headways as (
    select
        route_id,
        stop_id,
        epoch(arrived_at_local - lag(arrived_at_local) over (
            partition by service_date, route_id, stop_id order by arrived_at_local
        )) / 60.0 as headway_min
    from {{ ref('int_vehicle_runs') }} r
    join (select distinct visit_id, service_date from delays) using (visit_id)
),

scheduled_headways as (
    select
        route_id,
        stop_id,
        epoch(scheduled_arrival_local - lag(scheduled_arrival_local) over (
            partition by service_date, route_id, stop_id order by scheduled_arrival_local
        )) / 60.0 as headway_min
    from {{ ref('int_scheduled_stop_visits') }}
),

headways as (
    select
        o.route_id,
        o.stop_id,
        median(o.headway_min) as median_observed_headway_min,
        quantile_cont(o.headway_min, 0.9) as p90_observed_headway_min
    from observed_headways o
    where o.headway_min is not null and o.headway_min < 120
    group by all
),

scheduled as (
    select route_id, stop_id, median(headway_min) as median_scheduled_headway_min
    from scheduled_headways
    where headway_min > 0
    group by all
),

punctuality as (
    select
        route_id,
        stop_id,
        count(*) as observed_visits,
        count(distinct service_date) as days_observed,
        median(delay_seconds) / 60.0 as median_delay_min,
        quantile_cont(delay_seconds, 0.9) / 60.0 as p90_delay_min,
        avg(case when punctuality = 'on_time' then 1 else 0 end) as on_time_rate,
        avg(case when punctuality = 'early' then 1 else 0 end) as early_rate,
        avg(case when punctuality = 'late' then 1 else 0 end) as late_rate,
        median(dwell_seconds) as median_dwell_seconds
    from delays
    group by all
)

select
    p.route_id,
    r.route_short_name,
    r.route_long_name,
    p.stop_id,
    s.stop_name,
    s.stop_sequence,
    p.observed_visits,
    p.days_observed,
    round(p.median_delay_min, 2) as median_delay_min,
    round(p.p90_delay_min, 2) as p90_delay_min,
    round(p.on_time_rate, 3) as on_time_rate,
    round(p.early_rate, 3) as early_rate,
    round(p.late_rate, 3) as late_rate,
    p.median_dwell_seconds,
    round(h.median_observed_headway_min, 1) as median_observed_headway_min,
    round(h.p90_observed_headway_min, 1) as p90_observed_headway_min,
    round(sh.median_scheduled_headway_min, 1) as median_scheduled_headway_min
from punctuality p
left join headways h using (route_id, stop_id)
left join scheduled sh using (route_id, stop_id)
left join (
    select distinct route_id, route_short_name, route_long_name
    from {{ ref('stg_gtfs__routes') }}
    qualify row_number() over (partition by route_id order by feed_version desc) = 1
) r using (route_id)
left join (
    select route_id, stop_id, stop_name, stop_sequence
    from {{ ref('int_route_stops') }}
    qualify row_number() over (partition by route_id, stop_id order by feed_version desc) = 1
) s using (route_id, stop_id)
