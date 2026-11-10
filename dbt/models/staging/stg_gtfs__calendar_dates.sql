-- exception_type 1 = service added on this date, 2 = service removed.
select
    regexp_extract(filename, 'gtfs/([^/]+)/', 1) as feed_version,
    service_id,
    strptime(date, '%Y%m%d')::date as service_date,
    cast(exception_type as integer) as exception_type,
    holiday_name
from {{ source('gtfs', 'calendar_dates') }}
