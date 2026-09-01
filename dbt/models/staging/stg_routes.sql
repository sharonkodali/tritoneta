with source as (

    select * from {{ source('gtfs', 'routes') }}

)

select
    route_id,
    coalesce(nullif(route_short_name, ''), route_id)  as route_short_name,
    nullif(route_long_name, '')                      as route_long_name,
    cast(route_type as integer)                      as route_type,

    -- GTFS route_type. MTS runs 0 (Trolley) and 3 (Bus); the rest are here so
    -- the model doesn't silently null out if the feed ever gains a mode.
    case cast(route_type as integer)
        when 0 then 'light_rail'
        when 1 then 'subway'
        when 2 then 'rail'
        when 3 then 'bus'
        when 4 then 'ferry'
        else 'other'
    end                                              as mode,

    -- Feeds store colors bare ("0072BC"); the frontend wants them CSS-ready.
    case
        when route_color is null or route_color = '' then '#6b7280'
        else '#' || route_color
    end                                              as route_color,
    case
        when route_text_color is null or route_text_color = '' then '#ffffff'
        else '#' || route_text_color
    end                                              as route_text_color

from source
