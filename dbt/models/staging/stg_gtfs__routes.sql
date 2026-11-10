select
    regexp_extract(filename, 'gtfs/([^/]+)/', 1) as feed_version,
    route_id,
    route_short_name,
    route_long_name,
    cast(route_type as integer) as route_type
from {{ source('gtfs', 'routes') }}
