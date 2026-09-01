-- One clean row per vehicle observation.
--
-- Two things happen here that matter downstream:
--   1. The feed repeats a vehicle unchanged across polls when it hasn't moved,
--      so we dedupe on (vehicle, vehicle_timestamp) and keep the first sighting.
--   2. Vehicles occasionally report (0, 0) or a null position while a radio is
--      re-acquiring. Those rows would put a trolley in the Gulf of Guinea.

with source as (

    select * from {{ source('raw', 'vehicle_positions') }}

),

typed as (

    select
        entity_id,
        vehicle_id,
        vehicle_label,
        trip_id,
        route_id,
        cast(direction_id as integer)                      as direction_id,
        try_strptime(start_date, '%Y%m%d')::date           as service_date,
        cast(latitude  as double)                          as latitude,
        cast(longitude as double)                          as longitude,
        cast(bearing as double)                            as bearing,
        cast(speed   as double)                            as speed_mps,
        stop_id,
        cast(current_stop_sequence as integer)             as current_stop_sequence,

        -- GTFS-RT VehicleStopStatus enum
        case cast(current_status as integer)
            when 0 then 'incoming_at'
            when 1 then 'stopped_at'
            when 2 then 'in_transit_to'
        end                                                as current_status,

        to_timestamp(cast(vehicle_timestamp as bigint))    as observed_at,
        cast(polled_at as timestamp with time zone)        as polled_at

    from source
    where vehicle_id is not null
      and vehicle_timestamp is not null

),

deduped as (

    select
        *,
        row_number() over (
            partition by vehicle_id, observed_at
            order by polled_at
        ) as _rn
    from typed

)

select
    * exclude (_rn),
    observed_at at time zone '{{ var("local_timezone") }}' as observed_at_local
from deduped
where _rn = 1
  and latitude between 32.4 and 33.6      -- San Diego County bounding box:
  and longitude between -117.7 and -116.0 -- anything outside is a bad fix.
