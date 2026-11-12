import os
import sys
import configparser
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from sqlalchemy import text  # Add this import at the top of uk_weather_dag.py

#cp learning/dummy_data_engineer_practise_my_pipeline/uk_weather_dag.py ~/airflow/dags

# 1. Link Airflow to your Desktop project folder
"""
tells Python to add your Desktop project folder to its internal search list. 
Without these 3 lines, Airflow will crash immediately saying it cannot find src or project_config.
"""
PROJECT_ROOT = "/Users/yliu/Desktop/learning/dummy_data_engineer_practise_my_pipeline"
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Import your exact configurations and functions
from project_config import (
    SOURCE_DATA_DIR, PREPROCESS_DATA_DIR, ANALYSE_DATA_DIR, REPORT_DIR,
    MYSQL_TABLE_NAME, DAILY_STATION_SUMMARY_TABLE, DAILY_NATIONAL_SUMMARY_TABLE
)
from data_setting import WEATHER_STATIONS
from src.ingest_data import ingest_data
from src.check_data import run_quality_check, clean_data
from src.preprocess_data import transform_data
from src.store_data_mysql import insert_values, create_database_engine
from src.analyse_data import generate_analyse_data
from src.generate_report import create_report_plotly, create_report_bokeh

def get_config():
    config = configparser.ConfigParser()
    config.read(os.path.join(PROJECT_ROOT, "config.ini"))
    return config
#Airflow executes code from ~/airflow. 
#To prevent ModuleNotFoundError and FileNotFoundError, sys.path.append(PROJECT_ROOT) was added at the top 
# so Airflow knows where your Desktop folder lives, 
# and os.path.join(PROJECT_ROOT, "config.ini") forces it to read your exact configuration file.


# -------------------------------------------------------------------------
# 2. Define Your Pipeline Tasks
# -------------------------------------------------------------------------

# task wrapper functions&**context
"""
• **context: Whenever Airflow runs a function, 
it secretly passes a giant dictionary of metadata behind the scenes 
(containing run IDs, timestamps, and server details). Putting **context in the parentheses catches that dictionary.
• context["ds"]: Stands for Date Stamp. 
Airflow automatically pulls the scheduled date (formatted as YYYY-MM-DD) out of that dictionary 
so your functions know which day's file to create or read.
Airflow triggers the entire DAG once a day based on schedule="0 2 * * *", 
and injects the target date into each function using ingest_date = context["ds"].
• raise ValueError(...): In task_validate_and_clean, your original continue keyword was replaced with raise ValueError. 
In Airflow, raising an error is how a task communicates failure—it turns the box Red, halts the rest of the pipeline,
and logs your custom error message.
"""
def task_ingest(**context):
    ingest_date = context["ds"]  # Airflow automatically passes the target YYYY-MM-DD
    api_key = get_config()["API"]["WEATHER_API_KEY"]
    raw_csv = SOURCE_DATA_DIR / f"uk_weather_{ingest_date}.csv"
    
    ingest_data(api_key, WEATHER_STATIONS, ingest_date, raw_csv)



def task_validate_and_clean(**context):
    ingest_date = context["ds"]
    raw_csv = SOURCE_DATA_DIR / f"uk_weather_{ingest_date}.csv"
    cleaned_csv = PREPROCESS_DATA_DIR / f"cleaned_{ingest_date}.csv"
    
    if not run_quality_check(raw_csv):
        raise ValueError(f"❌ Data quality gate failed for {ingest_date}. Stopping pipeline.")
        
    clean_data(raw_csv, cleaned_csv)

def task_transform_and_analyse(**context):
    ingest_date = context["ds"]
    cleaned_csv = PREPROCESS_DATA_DIR / f"cleaned_{ingest_date}.csv"
    transformed_csv = PREPROCESS_DATA_DIR / f"transformed_{ingest_date}.csv"
    station_summary_csv = ANALYSE_DATA_DIR / f"station_summary_{ingest_date}.csv"
    national_summary_csv = ANALYSE_DATA_DIR / f"national_summary_{ingest_date}.csv"
    
    transform_data(cleaned_csv, transformed_csv)
    generate_analyse_data(transformed_csv, station_summary_csv, national_summary_csv)


# How to Make Your Pipeline Idempotent (Safe to Re-run):
# In data engineering, pipelines should be idempotent, meaning you can run or 
# retry any date multiple times without causing duplicate errors. 
# To fix this permanently, update task_load_mysql in ~/airflow/dags/uk_weather_dag.py 
# so it deletes any existing rows for ingest_date right before inserting the fresh data.
def task_load_mysql(**context):
    ingest_date = context["ds"]
    cfg = get_config()["MYSQL"]
    engine = create_database_engine(cfg["USER"], cfg["PASSWORD"], cfg["HOST"], cfg["DATABASE"])
    
    # 1. IDEMPOTENCY FIX: Clear existing rows for this specific date before inserting
    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {MYSQL_TABLE_NAME} WHERE date = :d"), {"d": ingest_date})
        conn.execute(text(f"DELETE FROM {DAILY_STATION_SUMMARY_TABLE} WHERE date = :d"), {"d": ingest_date})
        conn.execute(text(f"DELETE FROM {DAILY_NATIONAL_SUMMARY_TABLE} WHERE date = :d"), {"d": ingest_date})
    
    # 2. Insert the fresh records cleanly
    transformed_csv = PREPROCESS_DATA_DIR / f"transformed_{ingest_date}.csv"
    station_summary_csv = ANALYSE_DATA_DIR / f"station_summary_{ingest_date}.csv"
    national_summary_csv = ANALYSE_DATA_DIR / f"national_summary_{ingest_date}.csv"
    
    insert_values(transformed_csv, MYSQL_TABLE_NAME, engine)
    insert_values(station_summary_csv, DAILY_STATION_SUMMARY_TABLE, engine)
    insert_values(national_summary_csv, DAILY_NATIONAL_SUMMARY_TABLE, engine)


def task_generate_reports(**context):
    ingest_date = context["ds"]
    cfg = get_config()["MYSQL"]
    engine = create_database_engine(cfg["USER"], cfg["PASSWORD"], cfg["HOST"], cfg["DATABASE"])
    
    report_plotly_html = REPORT_DIR / f"report_plotly_{ingest_date}.html"
    report_bokeh_html = REPORT_DIR / f"report_bokeh_{ingest_date}.html"
    
    create_report_plotly(engine, DAILY_STATION_SUMMARY_TABLE, report_plotly_html)
    create_report_bokeh(engine, DAILY_STATION_SUMMARY_TABLE, report_bokeh_html)


# -------------------------------------------------------------------------
# 3. Schedule & Connect the Tasks
# -------------------------------------------------------------------------
# DAG Configuration & Rules
"""
• retries: 2 & retry_delay: Built-in fault tolerance. 
If the Weather API has a temporary 10-second network hiccup at 2:00 AM, 
Airflow won't give up—it will wait 5 minutes and automatically try again up to 2 times.
• depends_on_past: False:  Means Tuesday's weather run can still proceed even if Monday's run failed.
"""
default_args = {
    "owner": "yliu",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="uk_weather_daily_etl", #name of the dag on airflow
    default_args=default_args,
    description="Automated daily UK weather pipeline",
    schedule="0 2 * * *",           # Runs every morning at 02:00 AM UTC
    start_date=datetime(2026, 11, 11),
    catchup=False,                    # CRITICAL: Ignores July-Nov history; only runs new days
    tags=["weather", "etl"]
) as dag:
    
    """
    • schedule="0 2 * * *": Standard Cron syntax (Minute Hour Day Month DayOfWeek). 
    0 2 * * * translates to 02:00 AM every single day.
    • catchup=False: The most important setting for your use case. 
    Normally, if you set a start_date in the past, Airflow tries to "catch up" by running every missing day simultaneously.
    Setting this to False tells Airflow to ignore all past dates and only run new days moving forward.
    """

    #Section 4: Operators & Dependencies
    """
    • PythonOperator: A wrapper that turns a standard Python function (python_callable) into a visual Airflow task box (task_id).
    • >> (Bitshift Operator): Defines the dependency flow. t1 >> t2 means "Task 2 cannot start until Task 1 finishes and turns dark green."
    """
    t1 = PythonOperator(task_id="1_ingest_api_data", python_callable=task_ingest)
    t2 = PythonOperator(task_id="2_quality_check_and_clean", python_callable=task_validate_and_clean)
    t3 = PythonOperator(task_id="3_transform_and_aggregate", python_callable=task_transform_and_analyse)
    t4 = PythonOperator(task_id="4_load_to_mysql", python_callable=task_load_mysql)
    t5 = PythonOperator(task_id="5_compile_html_reports", python_callable=task_generate_reports)

    t1 >> t2 >> t3 >> t4 >> t5

"""
Part 3: What Happens Under the Hood at 2:00 AM?
1. The Scheduler Wakes Up: Airflow's background scheduler sees it is 02:00 AM on November 12th. 
It creates a DAG Run for the previous completed day (ds = "2026-11-11").
2. Task 1 Executes: Airflow spins up a background worker process, runs task_ingest, 
and saves uk_weather_2026-11-11.csv to your raw_data folder.
3. Handoff to Task 2: Once Task 1 exits cleanly, Airflow marks t1 green 
and immediately triggers t2 (task_validate_and_clean), passing the exact same ds = "2026-11-11" context.
4. Sequential Completion: This handoff repeats through transformation (t3), MySQL database insertion (t4), 
and static HTML report compilation (t5), leaving your dashboard updated and ready before you wake up.
Now that you understand how the DAG orchestrates your scripts, would you like to:
• Learn how to safely stop and restart your local Airflow processes on your Mac 
so it doesn't drain your battery when you aren't testing?
• See how to add Airflow Variables or Connections so you can delete your plain-text config.ini file 
and store passwords inside Airflow's encrypted database?
"""