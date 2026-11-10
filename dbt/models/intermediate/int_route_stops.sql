-- Every stop each route serves, per feed version, with its position in the loop.

select
    t.feed_version,
    t.route_id,
    st.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    min(st.stop_sequence) as stop_sequence,
    count(distinct st.trip_id) as scheduled_trips
from {{ ref('stg_gtfs__stop_times') }} st
join {{ ref('stg_gtfs__trips') }} t
  on st.feed_version = t.feed_version and st.trip_id = t.trip_id
join {{ ref('stg_gtfs__stops') }} s
  on st.feed_version = s.feed_version and st.stop_id = s.stop_id
group by all
