select
    regexp_extract(filename, 'gtfs/([^/]+)/', 1) as feed_version,
    trip_id,
    stop_id,
    cast(stop_sequence as integer) as stop_sequence,
    {{ gtfs_time_to_seconds('arrival_time') }} as arrival_seconds,
    {{ gtfs_time_to_seconds('departure_time') }} as departure_seconds,
    cast(timepoint as integer) = 1 as is_timepoint
from {{ source('gtfs', 'stop_times') }}
where arrival_time is not null
