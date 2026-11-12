import configparser
import time
import sys
import pandas as pd
from datetime import datetime
from project_config import SOURCE_DATA_DIR, PREPROCESS_DATA_DIR,ANALYSE_DATA_DIR, REPORT_DIR
from project_config import  MYSQL_TABLE_NAME, DAILY_STATION_SUMMARY_TABLE, DAILY_NATIONAL_SUMMARY_TABLE
from data_setting import WEATHER_STATIONS
from src.ingest_data import ingest_data
from src.check_data import run_quality_check, clean_data
from src.preprocess_data import transform_data
from src.store_data_mysql import create_table, insert_values, create_database_engine, execute_sql_statement
from src.store_data_mysql import create_daily_station_table, create_daily_national_table
from src.analyse_data import generate_analyse_data
from src.generate_report import create_report_plotly, create_report_bokeh

# 1. External Initialization Configurationss
config = configparser.ConfigParser()
config.read("config.ini")

API_KEY = config["API"]["WEATHER_API_KEY"]
USER = config["MYSQL"]["USER"]
PASSWORD = config["MYSQL"]["PASSWORD"]
HOST = config["MYSQL"]["HOST"]
DATABASE = config["MYSQL"]["DATABASE"]

LOCATIONS = WEATHER_STATIONS

# 2. Secure Connection and Table Infrastructure Setup
engine = create_database_engine(USER, PASSWORD, HOST, DATABASE)

# ONLY run table creation if script is executed with '--init' flag to prevent accidental data wipes
if "--init" in sys.argv:
    print("⚠️ Re-initialising schema structure: Clearing existing database tables...")
    with engine.connect() as conn:
        create_table_str = create_table(MYSQL_TABLE_NAME)
        execute_sql_statement(conn, create_table_str)

        create_daily_station_table_str = create_daily_station_table(DAILY_STATION_SUMMARY_TABLE)
        execute_sql_statement(conn, create_daily_station_table_str)
        create_daily_national_table_str = create_daily_national_table(DAILY_NATIONAL_SUMMARY_TABLE)
        execute_sql_statement(conn, create_daily_national_table_str)
else:
    print("🔄 Appending mode active: Preserving existing tables. Run with '--init' to completely reset.")

# 3. Dynamic Date Array Timeline Construction
start_date = datetime(2026, 7, 1)
end_date = datetime.now()
ingest_dates = [dt.strftime("%Y-%m-%d") for dt in pd.date_range(start_date, end_date)]

print(f"\n🚀 Starting Pipeline Execution across {len(ingest_dates)} target dates...\n")

# 4. Sequential ETL Execution Loop
for ingest_date in ingest_dates:
    print("="*120)
    print(f"📅 START PROCESSING DATE: {ingest_date} ")
    print("="*120)

    # Establish absolute file routing definitions
    raw_csv = SOURCE_DATA_DIR / f"uk_weather_{ingest_date}.csv"
    cleaned_csv = PREPROCESS_DATA_DIR / f"cleaned_{ingest_date}.csv"
    transformed_csv = PREPROCESS_DATA_DIR / f"transformed_{ingest_date}.csv"
    station_summary_csv = ANALYSE_DATA_DIR / f"station_summary_{ingest_date}.csv"
    national_summary_csv = ANALYSE_DATA_DIR / f"national_summary_{ingest_date}.csv"
    
    try:
        # Step A: Ingestion Inbound Layer
        ingest_data(API_KEY, LOCATIONS, ingest_date, raw_csv)
        
        # Step B: Data Validation & Quality Gatekeeping
        # Assumes run_quality_check returns True if safe, False if completely corrupted
        is_data_healthy = run_quality_check(raw_csv)
        if not is_data_healthy:
            print(f"⚠️ Skipping Database Load for {ingest_date}: Data quality checks failed validation thresholds.")
            continue
            
        # Step C: Data Cleansing & Processing
        clean_data(raw_csv, cleaned_csv)
        
        # Step D: Business Transformation Logic & Feature Engineering
        transform_data(cleaned_csv, transformed_csv)

        # Step E: Build an intermediate Aggregation Layer (often called an OLAP or Summary layer)
        generate_analyse_data(transformed_csv, station_summary_csv, national_summary_csv)

        # Step F: Warehouse Ingestion Target Layer
        insert_values(transformed_csv, MYSQL_TABLE_NAME, engine)
        insert_values(station_summary_csv, DAILY_STATION_SUMMARY_TABLE, engine)
        insert_values(national_summary_csv, DAILY_NATIONAL_SUMMARY_TABLE, engine)

        print("="*120)
        print(f"✅ COMPLETE PROCESSING DATE {ingest_date} and saved to MySQL.\n")
        print("="*120)

        # Guardrail: 1-second pause to respect API rate limit thresholds
        time.sleep(1)

    except Exception as e:
        print(f"❌ PIPELINE ERROR: Processing halted for date {ingest_date} -> Reason: {e}")
        print("⏭️ Moving forward to next calendar day...\n")
        continue

report_plotly_html = REPORT_DIR / f"report_plotly_{ingest_dates[-1]}.html"
report_bokeh_html = REPORT_DIR / f"report_bokeh_{ingest_dates[-1]}.html" 
create_report_plotly(engine, DAILY_STATION_SUMMARY_TABLE, report_plotly_html)
create_report_bokeh(engine, DAILY_STATION_SUMMARY_TABLE, report_bokeh_html) 

# print("="*60)
# print("🏁 MASTER PIPELINE RUN COMPLETE")
# print("="*60)
