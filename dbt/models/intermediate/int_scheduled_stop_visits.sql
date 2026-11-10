-- The published schedule expanded onto real dates: one row per scheduled
-- stop visit (trip x stop) on each day that trip actually runs.

with active as (
    select * from {{ ref('int_active_service_dates') }}
    -- Only expand the schedule for days we have GPS data for.
    where service_date between
        (select min(observed_date) from {{ ref('stg_gtfs_rt__vehicle_positions') }})
        and (select max(observed_date) from {{ ref('stg_gtfs_rt__vehicle_positions') }})
)

select
    a.service_date,
    a.feed_version,
    t.route_id,
    t.trip_id,
    st.stop_id,
    st.stop_sequence,
    st.is_timepoint,
    -- GTFS times are offsets from the start of the service day (local time).
    cast(a.service_date as timestamp) + to_seconds(st.arrival_seconds) as scheduled_arrival_local,
    cast(a.service_date as timestamp) + to_seconds(st.departure_seconds) as scheduled_departure_local,
    min(st.arrival_seconds) over (partition by a.service_date, t.trip_id) as trip_start_seconds
from active a
join {{ ref('stg_gtfs__trips') }} t
  on a.feed_version = t.feed_version and a.service_id = t.service_id
join {{ ref('stg_gtfs__stop_times') }} st
  on t.feed_version = st.feed_version and t.trip_id = st.trip_id
