select
    observation_date,
    station_name,
    count(*) as row_count
from {{ ref('fct_daily_weather_summary') }}
group by
    observation_date,
    station_name
having count(*) > 1
