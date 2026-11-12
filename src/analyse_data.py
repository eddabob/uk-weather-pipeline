import configparser
from project_config import PREPROCESS_DATA_DIR,ANALYSE_DATA_DIR
import os
import pandas as pd

TARGET_DATE = "2026-11-08"

input_file_path = PREPROCESS_DATA_DIR/f"transformed_{TARGET_DATE}.csv"
output_file_path1 = ANALYSE_DATA_DIR/f"station_summary_{TARGET_DATE}.csv"
output_file_path2= ANALYSE_DATA_DIR/f"national_summary_{TARGET_DATE}.csv"

def generate_analyse_data(csv_file_path, output_csv_path1, output_csv_path2):
    if not os.path.exists(csv_file_path):
        raise FileNotFoundError(f"Transformed file source missing:{csv_file_path}")

    df = pd.read_csv(csv_file_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df['is_freezing'] = df['is_freezing'].astype(int)

    station_summary = df.groupby(['date', 'station_name']).agg(
        avg_temp_c = ('temp_c', lambda x:round(x.mean(), 1)),
        max_temp_c = ('temp_c', 'max'),
        min_temp_c = ('temp_c', 'min'),
        avg_humidity_pct = ('humidity_pct', lambda x:int(round(x.mean(),0))),
        max_wind_speed_mph = ('wind_speed_mph', 'max'),
        avg_pressure_mb = ('pressure_mb', lambda x:round(x.mean(),1)),
        freezing_hours_count = ('is_freezing', 'sum')
    ).reset_index()

    # Identify extreme station locations for the day via index lookups
    warmest_row = df.loc[df['temp_c'].idxmax()]
    #print(warmest_row)
    """
    date              2026-11-08
    station_name        Plymouth
    temp_c                  12.1
    humidity_pct              73
    wind_speed_mph           8.7
    pressure_mb           1020.0
    condition_text      Overcast
    hour_of_day               13
    is_freezing                0
    feels_like_c             8.8
    pressure_trend        Steady
    Name: 301, dtype: object
    """
    windiest_row = df.loc[df['wind_speed_mph'].idxmax()]
    #print(windiest_row)
    a_dict = {}
    a_dict['date'] = df['date'].iloc[0]
    a_dict['national_avg_temp_c'] = round(df['temp_c'].mean(),1)
    a_dict['warmest_station_name'] = warmest_row['station_name']
    a_dict['warmest_station_temp'] = warmest_row['temp_c']
    a_dict['windiest_station_name'] = windiest_row['station_name']
    a_dict['national_peak_wind_mph'] = windiest_row['wind_speed_mph']
    national_summary = pd.DataFrame([a_dict])
    
    station_summary.sort_values(by=["station_name"], inplace=True)
    station_summary.to_csv(output_csv_path1, index=False, encoding="utf-8")
    
    national_summary.to_csv(output_csv_path2, index=False, encoding="utf-8")

if __name__ == "__main__":
    generate_analyse_data(input_file_path, output_file_path1, output_file_path2)










