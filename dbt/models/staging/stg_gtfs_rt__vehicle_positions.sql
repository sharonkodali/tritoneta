-- Cleaned GPS fixes: one row per vehicle per distinct fix, in local time.

with source as (
    select * from {{ source('gtfs_rt', 'vehicle_positions') }}
),

deduped as (
    -- The poller re-records a vehicle's last fix until it reports a new one.
    select distinct
        cast(route_id as varchar) as route_id,
        cast(vehicle_id as varchar) as vehicle_id,
        cast(lat as double) as lat,
        cast(lon as double) as lon,
        cast(vehicle_timestamp as bigint) as vehicle_timestamp
    from source
    where vehicle_id is not null
      and vehicle_timestamp is not null
      and route_id is not null
)

select
    {{ dbt_utils_surrogate_key(['vehicle_id', 'vehicle_timestamp']) }} as position_id,
    route_id,
    vehicle_id,
    lat,
    lon,
    to_timestamp(vehicle_timestamp) as observed_at_utc,
    timezone('{{ var("local_timezone") }}', to_timestamp(vehicle_timestamp)) as observed_at_local,
    cast(timezone('{{ var("local_timezone") }}', to_timestamp(vehicle_timestamp)) as date) as observed_date
from deduped
-- Drop fixes outside the San Diego service area (bad GPS, null island).
where lat between 32.7 and 33.0
  and lon between -117.35 and -117.05
-- A vehicle can report two positions with the same timestamp; keep one.
qualify row_number() over (partition by vehicle_id, vehicle_timestamp order by lat, lon) = 1
