# build a streamlit dashboard
# users can pick a custom date range, select a station_name
# view interactive line plots for temperature, feel_like temperatuare, humidity, wind speed and pressure
import configparser
from pathlib import Path
import pandas as pd
from data_setting import WEATHER_STATIONS
from project_config import MYSQL_TABLE_NAME, DAILY_STATION_SUMMARY_TABLE
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

# 1. page configuration
st.set_page_config(page_title="UK Weather Station Explorer")
st.title("UK Weather Telemetry Explorer")

# 2. Database connection
@st.cache_resource
def get_db_engine():
    config = configparser.ConfigParser()
    config.read("config.ini")
   
    USER = config["MYSQL"]["USER"]
    PASSWORD = config["MYSQL"]["PASSWORD"]
    HOST = config["MYSQL"]["HOST"]
    DATABASE = config["MYSQL"]["DATABASE"]

    db_url = f"mysql+pymysql://{USER}:{PASSWORD}@{HOST}/{DATABASE}"
    engine = create_engine(db_url)
    return engine

sql_engine = get_db_engine()

# 3. Set Dates and Stations for dropdown lists
@st.cache_data(ttl=600)
def get_filter_options():
    dates_l = pd.read_sql(f"SELECT MIN(date) as min_d, MAX(date) as max_d from {MYSQL_TABLE_NAME}", con = sql_engine).to_dict()
    #print(dates_l)
    #{'min_d': {0: datetime.date(2026, 7, 1)}, 'max_d': {0: datetime.date(2026, 11, 12)}} 
    stations_l = WEATHER_STATIONS
    #stations_l = pd.read_sql(f"SELECT DISTINCT station_name FROM {MYSQL_TABLE_NAME}ORDER BY station_name ASC", con=sql_engine)
    return dates_l['min_d'][0],dates_l['max_d'][0], stations_l

min_date, max_date, station_list = get_filter_options()
#print(min_date, max_date)
#{0: datetime.date(2026, 7, 1)} {0: datetime.date(2026, 11, 12)}

# 4.Siderbar Controls
default_start = max(min_date, max_date-pd.Timedelta(days=7))
date_range = st.sidebar.date_input(
    "1. Select Date Range:",
    value = (default_start, max_date),
    min_value = min_date,
    max_value = max_date
)

select_station = st.sidebar.selectbox(
    "2. Select Weather Station:",
    options = station_list,
    index = station_list.index("London") if "London" in station_list else 0 
)

# stop execution if user hasn't finished picking both start and end dates
if len(date_range) !=2:
    st.info("Please select both start and end date")
    st.stop()

start_dt, end_dt = date_range

# 5. Query from mysql table
@st.cache_data(ttl=300)
def load_station_data(station, start_date, end_date):
    query_str = text(f"""
                        SELECT date, hour_of_day, station_name, temp_c, feels_like_c,
                        humidity_pct, wind_speed_mph, pressure_mb, condition_text
                        FROM {MYSQL_TABLE_NAME}
                        WHERE station_name =:station
                        AND date BETWEEN :start_date AND :end_date
                        ORDER BY date ASC, hour_of_day ASC
                    """)
    df = pd.read_sql(query_str, con = sql_engine, params={
                      "station":station,
                      "start_date":start_date,
                      "end_date": end_date
                    })
    # Combine date and hour into a continuous datetime column for smooth line plotting
    if not df.empty:
        # FIX: Force hour_of_day to integer before converting to timedelta
        df["datetime"] = pd.to_datetime(df["date"].astype(str)) + pd.to_timedelta(df["hour_of_day"].astype(int), unit="h")
        #df["datetime"] 2026-11-05 00:00:00
    return df

df = load_station_data(select_station, start_dt, end_dt)

if df.empty:
    st.warning(f"No records found for {select_station} between {start_dt} and {end_dt}")

# 6. top summary metric for selected station & date range
st.subheader(f"{select_station} ({start_dt} to {end_dt})")

m1,m2,m3,m4 = st.columns(4)

m1.metric("Max Temperature", f"{df['temp_c'].max()} °C")
m2.metric("Min Temperature", f"{df['temp_c'].min()} °C")
m3.metric("Max Wind Speed", f"{df["wind_speed_mph"].max()} mph")
m4.metric("Avg Humidity", f"{df['humidity_pct'].mean():.0f}%")

st.markdown("---")

# 7. Interactive Line Plots
# Plot 1: Actual Temperature vs Engineered Feels Like Temperature
fig_temp = px.line(
    df,
    x = "datetime",
    y = ["temp_c", "feels_like_c"],
    title=f"Temperature vs Feels like (°C) - {select_station}",
    labels={"datetime": "Date & Time (UTC)", "value": "Temperature (°C)", "variable": "Metric"},
    markers = True
)
st.plotly_chart(fig_temp, use_container_width = True)

# Plot 2&3 Wind Speed and Humidity side by side
col1, col2 = st.columns(2)
with col1:
    fig_wind = px.line(
        df,
        x="datetime",
        y="wind_speed_mph",
       title=f"Wind Speed (mph) — {select_station}",
        labels={"datetime": "Date & Time (UTC)", "wind_speed_mph": "Wind Speed (mph)"},
        color_discrete_sequence=["#3b82f6"]
    )
    st.plotly_chart(fig_wind, use_container_width=True)

with col2:
    fig_humidity = px.line(
        df,
        x="datetime",
        y="humidity_pct",
        title=f"Relative Humidity (%) — {select_station}",
        labels={"datetime": "Date & Time (UTC)", "humidity_pct": "Humidity (%)"},
        color_discrete_sequence=["#10b981"]
    )
    st.plotly_chart(fig_humidity, use_container_width=True)

# Plot 4: Atmospheric Pressure
fig_pressure = px.line(
    df,
    x="datetime",
    y="pressure_mb",
    title=f"Atmospheric Pressure (mb) — {select_station}",
    labels={"datetime": "Date & Time (UTC)", "pressure_mb": "Pressure (mb)"},
    color_discrete_sequence=["#f59e0b"]
)
st.plotly_chart(fig_pressure, use_container_width=True)

# 8. Raw Data Table
with st.expander("📋 View Filtered Hourly Data"):
    st.dataframe(df.drop(columns=["datetime"]), use_container_width=True, hide_index=True)