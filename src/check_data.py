# This program will do basic quality checks of the one day hourly weather data ingested
import os
import pandas as pd

from data_setting import TARGET_DATE, TEMP_UPPER_BOUND, TEMP_LOWER_BOUND, HUM_UPPER_BOUND, HUM_LOWER_BOUND
from project_config import SOURCE_DATA_DIR, PREPROCESS_DATA_DIR

input_file_path = SOURCE_DATA_DIR/f"UK_WEATHER_{TARGET_DATE}.csv"
output_file_path = PREPROCESS_DATA_DIR/f"cleaned_{TARGET_DATE}.csv"

def run_quality_check(csv_path):
    if not os.path.exists(csv_path):
        print(f"ERROR: File:{csv_path} eos not exist!")
        return

    # load data
    df = pd.read_csv(csv_path)
    total_rows = len(df)
    print(f"Total Rows Ingested:{total_rows}")

    # Track Overall Quality Metrics
    failed_checks = 0

    # RULE 1: check for completely empty DataFrames
    if total_rows == 0:
        print("RULE 1 Failed: the CSV file is completely empty.")
        failed_checks += 1
        return
    else:
        print("RULE 1: Passed: the CSV file is not empty.")

    # RULE 2: check for missing values (Nulls/NaNs):
    null_contents = df.isnull().sum()
    if null_contents.sum() == 0:
        print("RULE 2: Passed: No missing or null values found.")
    else:
        failed_check +=1
        for col, col_null_count in null_contents.items():
            if col_null_count >0:
                print(f"RULE 2 Failed: '{col}' has {col_null_count} missing records.")

    # RULE 3: check for duplicate rows:
    duplicate_mask = df.duplicated(keep=False) # Pandas Series of boolean values (True or False)
    # By default, Pandas only marks the second time it sees a duplicate row as True. Setting keep=False forces Pandas to mark all occurrences as True.
    duplicate_counts = df.duplicated().sum()

    if duplicate_counts == 0:
        print("RULE 3: Passed: No duplicate rows found.")
    else: 
        failed_check += 1
        print("RULE 3: Failed: Found {duplicate_counts} duplicate rows")
        # Extract rows and expose their index positions
        duplicate_rows = df[duplicate_mask]       
        # Display the rows showing the index on the far left
        print(duplicate_rows[["station_name", "timestamp", "temp_c"]]) 
        print("-" * 50)


    # RULE 4: Check if each location has exactly 24 rows
    location_counts = df["station_name"].value_counts()
    incomplete_locations = location_counts[location_counts!=24]
    """
    Index (Labels)    Values (Counts)
    --------------    ---------------
    Manchester        48
    Belfast           23
    dtype: int64
    """

    if incomplete_locations.empty:
        #the filter [location_counts != 24] returns nothing. incomplete_locations 
        # becomes a completely blank Series object, 
        # making incomplete_locations.empty evaluate to True
        print("RULE 4: Passed: All locations have 24 rows")

    else:
        failed_checks += 1
        for city, city_count in incomplete_locations.items():
            print("RULE 4: Failed: '{}' contains {city_count} rows")


    # RULE 5: check Invalid metric ranges
    # temp_c, humidity_pct,wind_speed_mph,pressure_mb,
    # Temperature sanity bounds for the UK: -30°C to 50°C
    temp_anomalies = df[(df['temp_c']<TEMP_LOWER_BOUND) | (df['temp_c'] > TEMP_UPPER_BOUND)]
    if temp_anomalies.empty:
        print("RULE 5: Temperature Range Validity Passed.")
    else:
        failed_check += 1
        print("RULE 5: Temperature Range Validity Failed: Found {len(temp_anomalies)} invalid temperature rows")
        print(temp_anomalies[["timestamp", "station_name", "temp_c"]])

    # Humidity bounds check: 0% to 100%
    humidity_anomalies = df[(df["humidity_pct"] < HUM_LOWER_BOUND) | (df["humidity_pct"] > HUM_UPPER_BOUND)]
    if humidity_anomalies.empty:
        print("RULE 5: Relative Humidity metrics fall within realistic boundaries (0-100%).")
    else:
        failed_checks += 1
        print(f"RULE 5 FAILED: Found {len(humidity_anomalies)} corrupted humidity values out of bounds.")

    # wind_speed_anomalies = df[df['wind_speed_mph']< 0]
    # pressure_anomalies = df[df['pressure_mb']< 0]

    # final summary
    print("\n" + "=" * 60)
    print("DATA QUALITY SUMMARY REPORT")
    print("=" * 60)
    if failed_checks == 0:
        print("ALL CHECKS PASSED: Your dataset is structurally sound and ready for production pipelines!")
        print("=" * 60 + "\n")
        return True
    else:
        print(f"PIPELINE ALERT: Data quality run completed with {failed_checks} failed validation rule(s).")
        print("=" * 60 + "\n")
        return False
    


def clean_data(input_csv_file, output_csv_file):
    df = pd.read_csv(input_csv_file)

    ## Fix RULE 3: Duplicate rows: remove the duplicate rows
    initial_num_rows = df.shape[0]
    df.drop_duplicates(inplace = True)
    dropped_num_rows = initial_num_rows-len(df)
    print(f"Fixed: Successfully drop {dropped_num_rows} rows")

    ## Fix RULE 5: Anomalies : clip the values to its lower and upper bounds if exceeds
    df["temp_c"] = df["temp_c"].clip(lower=TEMP_LOWER_BOUND, upper=TEMP_UPPER_BOUND)
    df["humidity_pct"] = df["humidity_pct"].clip(lower=HUM_LOWER_BOUND, upper=HUM_UPPER_BOUND)
    
    ## Fix RULE 2: Missing Values
    # for categorical gaps: imputation with values "Unknown"
    if df["condition_text"].isnull().sum()>0:
        df["condition_text"] = df["condition_text"].fillna("Unknown")
    # for numeric gaps: fill in missing values by using interpolation method for the same station
    numeric_cols = ["temp_c", "humidity_pct", "wind_speed_mph", "pressure_mb"]
    # Sort chronologically by station to ensure interpolation makes physical sense
    df.sort_values(by=["station_name", "timestamp"], inplace=True)
    for col in numeric_cols:
        if df[col].isnull().sum() > 0:
            df.groupby("station_name")[col].transform(lambda x:x.interpolate(method="linear").bfill().ffill())
            """
            df.groupby("station_name")[col]: Instead of treating the data as one giant block, 
            this splits your DataFrame into independent mini-datasets grouped by individual weather stations.
            • This is a critical data engineering guardrail. 
            Without it, if London was missing data at 23:00, it would accidentally look at Edinburgh's 00:00 data to guess the missing value.

            Inside the lambda function, your data passes through a three-stage cleaning conveyor belt (where x represents the weather column for one specific city):
            • Step A: .interpolate(method="linear")
            This looks at the rows before and after a missing value and mathematically calculates a steady, linear ramp to fill the gap. For example, if temperature drops from 10°C at 01:00 to 12°C at 03:00, it intelligently fills 02:00 with 11°C.
            • Step B: .bfill() (Backward Fill)
            If a station is missing data at the very beginning of the day (e.g., midnight at 00:00), interpolation cannot work because there is no "before" value. .bfill() fixes this by looking forward to the next valid hour (e.g., 01:00) and copying that value backward to midnight.
            • Step C: .ffill() (Forward Fill)
            If a station is missing data at the very end of the day (e.g., 23:00), .ffill() takes care of it by looking at the last known recorded hour (e.g., 22:00) and copying that value forward to the end of the file.
            """
    print(f"File: '{input_csv_file}' has been CLEANED and \n SAVED as File: '{output_csv_file}'")

    df.to_csv(output_csv_file, index=False, encoding="utf-8")

if __name__ == "__main__":
    is_healthy = run_quality_check(input_file_path)
    clean_data(input_file_path, output_file_path)


    
