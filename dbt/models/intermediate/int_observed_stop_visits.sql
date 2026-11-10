-- When each vehicle actually passed each stop on its route.
--
-- For every GPS segment and every stop on that vehicle's route, project the
-- stop onto the segment (in a local flat-earth approximation, accurate to
-- well under a meter at campus scale) to find the point of closest approach.
-- If that point is within the match radius, the passage time is interpolated
-- along the segment. Consecutive matches at the same stop (a shuttle dwelling
-- for several pings) are then collapsed into a single visit.

with segments as (
    select * from {{ ref('int_position_segments') }}
),

service_feed as (
    -- The feed in effect on each date (feeds do not overlap in time).
    select distinct service_date, feed_version from {{ ref('int_active_service_dates') }}
),

route_stops as (
    select * from {{ ref('int_route_stops') }}
),

projected as (
    select
        s.vehicle_id,
        s.route_id,
        s.observed_date,
        f.feed_version,
        rs.stop_id,
        rs.stop_sequence,
        s.start_at_local,
        s.gap_seconds,
        -- Meters east/north relative to the segment start.
        (s.end_lon - s.start_lon) * cos(radians(s.start_lat)) * 111320 as dx,
        (s.end_lat - s.start_lat) * 110540 as dy,
        (rs.stop_lon - s.start_lon) * cos(radians(s.start_lat)) * 111320 as sx,
        (rs.stop_lat - s.start_lat) * 110540 as sy
    from segments s
    join service_feed f on s.observed_date = f.service_date
    join route_stops rs on rs.feed_version = f.feed_version and rs.route_id = s.route_id
),

closest_approach as (
    select
        *,
        case
            when dx * dx + dy * dy = 0 then 0
            else greatest(0, least(1, (sx * dx + sy * dy) / (dx * dx + dy * dy)))
        end as t
    from projected
),

matches as (
    select
        vehicle_id,
        route_id,
        observed_date,
        feed_version,
        stop_id,
        stop_sequence,
        start_at_local + to_milliseconds(cast(t * gap_seconds * 1000 as bigint)) as passed_at_local,
        sqrt(pow(sx - t * dx, 2) + pow(sy - t * dy, 2)) as distance_m
    from closest_approach
    where sqrt(pow(sx - t * dx, 2) + pow(sy - t * dy, 2)) <= {{ var('stop_match_radius_m') }}
),

visit_breaks as (
    select
        *,
        case
            when epoch(passed_at_local - lag(passed_at_local) over w) <= 180 then 0
            else 1
        end as is_new_visit
    from matches
    window w as (partition by vehicle_id, stop_id order by passed_at_local)
),

visit_ids as (
    select
        *,
        sum(is_new_visit) over (
            partition by vehicle_id, stop_id order by passed_at_local
            rows between unbounded preceding and current row
        ) as visit_number
    from visit_breaks
)

select
    {{ dbt_utils_surrogate_key(['vehicle_id', 'stop_id', 'min(passed_at_local)']) }} as visit_id,
    vehicle_id,
    route_id,
    observed_date,
    feed_version,
    stop_id,
    stop_sequence,
    min(passed_at_local) as arrived_at_local,
    max(passed_at_local) as departed_at_local,
    epoch(max(passed_at_local) - min(passed_at_local)) as dwell_seconds,
    min(distance_m) as closest_distance_m,
    count(*) as matched_segments
from visit_ids
group by vehicle_id, route_id, observed_date, feed_version, stop_id, stop_sequence, visit_number
