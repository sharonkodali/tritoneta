-- The core delay metric: how late (or early) each observed stop visit was
-- relative to the published schedule. The source feeds have no delay field;
-- this is derived by matching GPS-based stop visits to scheduled visits.
--
-- Matching is done per run, not per visit: each run is assigned the one
-- scheduled trip that best explains all of its stops (lowest mean absolute
-- offset). This avoids the noise of matching every stop independently when
-- shuttles run every 10-15 minutes.

with runs as (
    select * from {{ ref('int_vehicle_runs') }}
    where stops_in_run >= 3
),

scheduled as (
    select * from {{ ref('int_scheduled_stop_visits') }}
),

candidates as (
    -- Every (run visit, scheduled visit) pair close enough in time to plausibly match.
    select
        r.run_id,
        r.visit_id,
        s.trip_id,
        epoch(r.arrived_at_local - s.scheduled_arrival_local) as offset_seconds
    from runs r
    join scheduled s
      on s.service_date = r.observed_date
     and s.route_id = r.route_id
     and s.stop_id = r.stop_id
     and abs(epoch(r.arrived_at_local - s.scheduled_arrival_local))
         <= {{ var('max_schedule_offset_minutes') }} * 60
),

per_visit_trip as (
    -- Loops visit the terminal stop twice per trip; keep the closer time.
    select run_id, visit_id, trip_id, arg_min(offset_seconds, abs(offset_seconds)) as offset_seconds
    from candidates
    group by all
),

run_trip_scores as (
    select
        run_id,
        trip_id,
        count(*) as matched_stops,
        avg(abs(offset_seconds)) as mean_abs_offset_seconds
    from per_visit_trip
    group by all
    having count(*) >= 3
),

best_trip_per_run as (
    select * from run_trip_scores
    qualify row_number() over (
        partition by run_id order by matched_stops desc, mean_abs_offset_seconds
    ) = 1
),

one_run_per_trip as (
    -- A scheduled trip can only be operated by one run.
    select b.*
    from best_trip_per_run b
    join (select distinct run_id, observed_date from runs) r using (run_id)
    qualify row_number() over (
        partition by r.observed_date, b.trip_id order by b.matched_stops desc, b.mean_abs_offset_seconds
    ) = 1
)

select
    r.visit_id,
    r.run_id,
    r.vehicle_id,
    r.route_id,
    r.observed_date as service_date,
    r.feed_version,
    t.trip_id,
    r.stop_id,
    s.stop_sequence,
    s.is_timepoint,
    s.scheduled_arrival_local,
    r.arrived_at_local,
    r.departed_at_local,
    r.dwell_seconds,
    r.closest_distance_m,
    v.offset_seconds as delay_seconds,
    case
        when v.offset_seconds < -60 then 'early'
        when v.offset_seconds <= 300 then 'on_time'
        else 'late'
    end as punctuality,
    t.mean_abs_offset_seconds as run_match_quality_seconds
from runs r
join one_run_per_trip t on r.run_id = t.run_id
join per_visit_trip v on v.run_id = r.run_id and v.visit_id = r.visit_id and v.trip_id = t.trip_id
join scheduled s
  on s.service_date = r.observed_date
 and s.trip_id = t.trip_id
 and s.stop_id = r.stop_id
 and epoch(r.arrived_at_local - s.scheduled_arrival_local) = v.offset_seconds
