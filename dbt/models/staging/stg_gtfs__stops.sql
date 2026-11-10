select
    regexp_extract(filename, 'gtfs/([^/]+)/', 1) as feed_version,
    stop_id,
    stop_name,
    cast(stop_lat as double) as stop_lat,
    cast(stop_lon as double) as stop_lon
from {{ source('gtfs', 'stops') }}
