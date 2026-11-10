-- Which GTFS feed and service_id are in effect on each calendar date,
-- applying the weekday pattern and calendar_dates exceptions (holidays).

with calendar as (
    select * from {{ ref('stg_gtfs__calendar') }}
),

exceptions as (
    select * from {{ ref('stg_gtfs__calendar_dates') }}
),

date_spine as (
    select cast(d as date) as service_date
    from range(
        (select min(start_date) from calendar),
        (select max(end_date) from calendar) + interval 1 day,
        interval 1 day
    ) as t(d)
),

weekly_pattern as (
    select
        d.service_date,
        c.feed_version,
        c.service_id
    from date_spine d
    join calendar c
      on d.service_date between c.start_date and c.end_date
     and case dayofweek(d.service_date)
            when 0 then c.sunday
            when 1 then c.monday
            when 2 then c.tuesday
            when 3 then c.wednesday
            when 4 then c.thursday
            when 5 then c.friday
            when 6 then c.saturday
         end
),

removed as (
    select feed_version, service_id, service_date from exceptions where exception_type = 2
),

added as (
    select service_date, feed_version, service_id from exceptions where exception_type = 1
)

select service_date, feed_version, service_id
from (
    select * from weekly_pattern
    except
    select service_date, feed_version, service_id from removed
    union
    select * from added
)
