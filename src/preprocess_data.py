# All data transformation goes in here:
# This program will generate Enrichment columns based on application requirements
# add more features or drop unncessary columns

import os
import pandas as pd
import numpy as np

from data_setting import TARGET_DATE
from project_config import  PREPROCESS_DATA_DIR

input_file_path = PREPROCESS_DATA_DIR/f"cleaned_{TARGET_DATE}.csv"
output_file_path = PREPROCESS_DATA_DIR/f"transformed_{TARGET_DATE}.csv"

"""
To add real application value for analytical or downstream machine learning pipelines, the script injects these calculated fields:
• feels_like_c (Apparent Temperature): 
Calculated using wind speed and humidity to reflect real-world human comfort indices.
• is_freezing (Boolean Flag): 
Sets to True if conditions dip below 0.0°C to immediately alert logistics or transit frameworks.
• pressure_trend (Categorical String): 
Compares barometric trends over time to classify whether a weather system is Rising, Falling, or Steady (useful for immediate storm forecasting).
• hour_of_day (Integer Extract): 
Isolates the integer hour chunk out of the timestamp string to accelerate indexing, aggregation, and partitioning.
"""
def transform_data(input_csv_path, output_csv_path):
    df = pd.read_csv(input_csv_path)
    # Sort data explicitly to guarantee time-series windows execute flawlessly
    df.sort_values(by=["station_name", "timestamp"], inplace= True)

    # 1. extract hour & month
    df["hour_of_day"] = pd.to_datetime(df["timestamp"]).dt.hour
    # df['month'] = pd.to_datetime(df['date']).dt.month
    # df['month_str'] = pd.to_datetime(df['date']).dt.strftime('%B')
    # 2. is_freezing
    df["is_freezing"] = df["temp_c"].apply(lambda x:True if x<=0.0 else False)

    # 3. calculate human 'feels like' temperature by using 'humidity_pct', 'wind_speed_mph' and 'temp_c'
    vapor_pressure = (df["humidity_pct"] / 100.0) * 6.105 * np.exp((17.27 * df["temp_c"]) / (237.7 + df["temp_c"])) #Pandas Series object
    wind_meters_per_sec = df["wind_speed_mph"] * 0.44704 #Pandas Series object
    df["feels_like_c"] = df["temp_c"] + (0.33 * vapor_pressure) - (0.70 * wind_meters_per_sec) - 4.0
    df["feels_like_c"] = df["feels_like_c"].round(1)

    """
    # not as efficient as the numpy vectorisation code like above, here just for recap by using apply
    # the function runs a standard Python loop behind the scenes.
    def calculate_feels_like(row):
        temp = row['temp_c']
        humidity = row['humidity_pct']
        wind = row['wind_speed_mph']
        e = (humidity / 100.0) * 6.105 * np.exp((17.27 * temp) / (237.7 + temp))
        feels_like = temp + (0.33 * e) - (0.70 * (wind * 0.44704)) - 4.0
        return np.round(feels_like, 1)
    df["feels_like_c"] = df.apply(calculate_feels_like, axis=1)
    # By default, .apply() looks at columns (axis=0).
    # Setting axis=1 switches the execution to horizontal rows. Inside the function, 
    # the row variable becomes a dictionary-like object representing one individual row of your CSV. 
    # You can pull any column data you need simply by passing its name like row["temp_c"].
    """

    # 4. calculate barometric pressure trend
    # compare current pressure to the previous hour slot per station
    df['pressure_diff'] = df.groupby("station_name")['pressure_mb'].diff() # back value -previous value
    df['pressure_trend'] = df['pressure_diff'].apply(lambda x:'Rising' if x>0.5 else ("Falling" if x<-0.5 else "Steady"))
    #from a data engineering performance standpoint, using .apply() with a lambda loop runs row-by-row in pure Python.
    # It is significantly slower than using NumPy vectorization (np.where).
    # df["pressure_trend"] = np.where(df["pressure_diff"] > 0.5, "Rising", np.where(df["pressure_diff"] < -0.5, "Falling", "Steady"))
    """
        Index	station_name	timestamp	pressure_mb	Calculated .diff() Output	
        0	London	            2026-11-07 00:00	1013.0	NaN	            Steady (Since it isn't > 0.5 or < -0.5)
        1	London	            2026-11-07 01:00	1014.2	1.2	            Rising (Value is higher than 0.5)
        2	London	            2026-11-07 02:00	1013.7	-0.5	        Steady (Boundary threshold check)
        3	London	            2026-11-07 03:00	1013.6	-0.1	        Steady
        4	London	            2026-11-07 04:00	1014.5	0.9	            Rising (Value is higher than 0.5)
    """
    
    # Final cleanup: Sort table chronologically by location
    df.sort_values(by=["station_name", "timestamp"], inplace=True)
    # FIX: Use single square brackets [] for the list of columns
    df.drop(columns=['timestamp', 'latitude', 'longitude', 'pressure_diff'], axis=1, inplace=True, errors='ignore')
    
    df.to_csv(output_csv_path, index=False, encoding="utf-8")

    print("\n" + "=" * 60)
    print("TRANSFORMATION SUMMARY")
    print("=" * 60)
    print(f"File SAVED to: {output_csv_path}")
    print(f"Final Rowcount: {len(df)}")
    #print(f"Enriched Columns: {list(df.columns)}")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    transform_data(input_file_path, output_file_path)







