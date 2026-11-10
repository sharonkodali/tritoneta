select
    regexp_extract(filename, 'gtfs/([^/]+)/', 1) as feed_version,
    trip_id,
    route_id,
    service_id,
    trip_headsign,
    cast(direction_id as integer) as direction_id,
    block_id,
    shape_id
from {{ source('gtfs', 'trips') }}
