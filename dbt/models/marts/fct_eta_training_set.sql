{{ config(
    materialized = 'external',
    location = var('data_dir') ~ '/processed/eta_training_set.parquet',
    format = 'parquet'
) }}

-- Labeled training data for the arrival-time model. Label: delay_seconds at
-- a stop. Features only use information available before the vehicle reaches
-- that stop (its delay earlier in the same run, schedule context, and
-- historical averages from strictly earlier days), so there is no leakage.
-- The last 7 days are held out as a time-based test split.

with delays as (
    select * from {{ ref('fct_stop_delays') }}
),

with_run_context as (
    select
        *,
        lag(delay_seconds) over run_w as prev_stop_delay_seconds,
        epoch(arrived_at_local - lag(arrived_at_local) over run_w) as seconds_since_prev_stop,
        first_value(delay_seconds) over run_w as run_first_stop_delay_seconds,
        row_number() over run_w - 1 as stops_into_run
    from delays
    window run_w as (partition by run_id order by arrived_at_local)
),

daily_route_hour as (
    select
        route_id,
        hour(scheduled_arrival_local) as hour_of_day,
        service_date,
        sum(delay_seconds) as delay_sum,
        count(*) as n
    from delays
    group by all
),

historical as (
    -- Mean delay for this route and hour over all earlier days.
    select
        route_id,
        hour_of_day,
        service_date,
        sum(delay_sum) over w / nullif(sum(n) over w, 0) as hist_route_hour_mean_delay_seconds
    from daily_route_hour
    window w as (
        partition by route_id, hour_of_day order by service_date
        rows between unbounded preceding and 1 preceding
    )
),

split_cutoff as (
    select max(service_date) - interval 7 day as cutoff from delays
)

select
    c.visit_id,
    c.service_date,
    c.route_id,
    c.stop_id,
    c.trip_id,
    c.vehicle_id,
    -- Features
    c.stop_sequence,
    c.stops_into_run,
    hour(c.scheduled_arrival_local) as hour_of_day,
    dayofweek(c.service_date) as day_of_week,
    dayofweek(c.service_date) in (0, 6) as is_weekend,
    c.is_timepoint,
    c.prev_stop_delay_seconds,
    c.seconds_since_prev_stop,
    c.run_first_stop_delay_seconds,
    h.hist_route_hour_mean_delay_seconds,
    -- Label
    c.delay_seconds,
    case when c.service_date > (select cutoff from split_cutoff) then 'test' else 'train' end as split
from with_run_context c
left join historical h
  on h.route_id = c.route_id
 and h.hour_of_day = hour(c.scheduled_arrival_local)
 and h.service_date = c.service_date
-- The first stop of a run has no earlier in-run signal to predict from.
where c.prev_stop_delay_seconds is not null
