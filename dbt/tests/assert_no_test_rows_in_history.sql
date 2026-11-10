-- Historical features must only use earlier days: the first day in the data
-- has no history, so its feature must be null.
select *
from {{ ref('fct_eta_training_set') }}
where service_date = (select min(service_date) from {{ ref('fct_eta_training_set') }})
  and hist_route_hour_mean_delay_seconds is not null
