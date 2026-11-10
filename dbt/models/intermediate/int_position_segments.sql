-- Consecutive GPS fixes from the same vehicle, paired into line segments.
-- Pings arrive ~20s apart and shuttles move ~85m between them, so stop
-- passages are found along these segments rather than at individual pings.

with positions as (
    select * from {{ ref('stg_gtfs_rt__vehicle_positions') }}
),

paired as (
    select
        vehicle_id,
        route_id,
        observed_date,
        lag(lat) over w as start_lat,
        lag(lon) over w as start_lon,
        lag(observed_at_local) over w as start_at_local,
        lag(route_id) over w as start_route_id,
        lat as end_lat,
        lon as end_lon,
        observed_at_local as end_at_local
    from positions
    window w as (partition by vehicle_id order by observed_at_utc)
)

select
    vehicle_id,
    route_id,
    observed_date,
    start_lat,
    start_lon,
    end_lat,
    end_lon,
    start_at_local,
    end_at_local,
    epoch(end_at_local - start_at_local) as gap_seconds
from paired
where start_at_local is not null
  -- Drop segments spanning signal loss or a route change.
  and epoch(end_at_local - start_at_local) between 1 and {{ var('max_ping_gap_seconds') }}
  and start_route_id = route_id
