with staging as (
    select * from {{ ref('stg_weather_observations') }}
),

daily_summary as (
    select
        observation_date,
        station_name,

        -- Temperature metrics
        round(avg(temperature_c), 2) as avg_temperature_c,
        min(temperature_c) as min_temperature_c,
        max(temperature_c) as max_temperature_c,
        round(avg(feels_like_c), 2) as avg_feels_like_c,

        -- Wind, humidity, and pressure metrics
        round(avg(humidity_pct), 2) as avg_humidity_pct,
        round(avg(wind_speed_mph), 2) as avg_wind_speed_mph,
        max(wind_speed_mph) as max_wind_speed_mph,
        round(avg(pressure_mb), 2) as avg_pressure_mb,

        -- Observation counts and freezing flags
        count(*) as total_observations,
        sum(case when is_freezing = 1 then 1 else 0 end) as freezing_hours

    from staging
    group by
        observation_date,
        station_name
)

select * from daily_summary
