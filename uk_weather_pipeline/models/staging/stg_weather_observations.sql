with source as (
    select * from {{ source('uk_weather_raw', 'processed_data') }}
),

cleaned as (
    select
        -- Identifiers and timestamps
        cast(date as date) as observation_date,
        cast(hour_of_day as signed) as hour_of_day,
        trim(station_name) as station_name,

        -- Weather measurements
        cast(temp_c as decimal(5, 2)) as temperature_c,
        cast(feels_like_c as decimal(5, 2)) as feels_like_c,
        cast(humidity_pct as decimal(5, 2)) as humidity_pct,
        cast(wind_speed_mph as decimal(6, 2)) as wind_speed_mph,
        cast(pressure_mb as decimal(7, 2)) as pressure_mb,

        -- Descriptive attributes and flags
        trim(condition_text) as weather_condition,
        trim(pressure_trend) as pressure_trend,
        cast(is_freezing as unsigned) as is_freezing

    from source
    where station_name is not null
      and date is not null
)

select * from cleaned
