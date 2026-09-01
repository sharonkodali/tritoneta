with source as (

    select * from {{ source('gtfs', 'stops') }}

)

select
    stop_id,
    nullif(stop_code, '')            as stop_code,
    stop_name,
    cast(stop_lat as double)         as stop_lat,
    cast(stop_lon as double)         as stop_lon,
    nullif(parent_station, '')       as parent_station,
    cast(
        nullif(location_type, '') as integer
    )                                as location_type

from source
where stop_lat is not null
  and stop_lon is not null
