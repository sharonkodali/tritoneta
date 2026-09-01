-- One clean row per (trip, stop, poll) arrival prediction.
--
-- This is the model's raw material. Each row says: "as of `polled_at`, trip T is
-- expected at stop S at `predicted_arrival`, which is `delay_seconds` off the
-- timetable." Poll the same trip 20 minutes later and you get a new row for the
-- same stop with a better estimate — that revision history is exactly what lets
-- us both train on the truth and measure how early a good guess is available.

with source as (

    select * from {{ source('raw', 'trip_updates') }}

),

typed as (

    select
        entity_id,
        trip_id,
        route_id,
        cast(direction_id as integer)                       as direction_id,
        try_strptime(start_date, '%Y%m%d')::date            as service_date,
        vehicle_id,
        stop_id,
        cast(stop_sequence as integer)                      as stop_sequence,

        to_timestamp(cast(arrival_time as bigint))          as predicted_arrival,
        cast(arrival_delay as integer)                      as arrival_delay_seconds,
        to_timestamp(cast(departure_time as bigint))        as predicted_departure,
        cast(departure_delay as integer)                    as departure_delay_seconds,

        -- Most agencies populate arrival; a few only populate departure.
        -- Coalescing keeps one usable delay column for everything downstream.
        coalesce(
            cast(arrival_delay as integer),
            cast(departure_delay as integer)
        )                                                   as delay_seconds,

        to_timestamp(cast(trip_update_timestamp as bigint)) as feed_timestamp,
        cast(polled_at as timestamp with time zone)         as polled_at

    from source
    where trip_id is not null
      and stop_id is not null

),

deduped as (

    -- The same prediction is republished until it changes; keep one row per
    -- distinct prediction rather than one per poll.
    select
        *,
        row_number() over (
            partition by trip_id, service_date, stop_id, stop_sequence, delay_seconds
            order by polled_at
        ) as _rn
    from typed
    where delay_seconds is not null

)

select
    * exclude (_rn),
    delay_seconds / 60.0                                      as delay_minutes,
    date_diff(
        'second',
        polled_at,
        coalesce(predicted_arrival, predicted_departure)
    )                                                         as horizon_seconds,
    polled_at at time zone '{{ var("local_timezone") }}'       as polled_at_local
from deduped
where _rn = 1
  and abs(delay_seconds) <= {{ var('delay_outlier_threshold_seconds') }}
