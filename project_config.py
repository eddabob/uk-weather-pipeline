from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BASE_DIR/"dummy_data_engineer_practise_my_pipeline"
SOURCE_DATA_DIR = PROJECT_DIR/"data"/"raw_data"
ANALYSE_DATA_DIR = PROJECT_DIR/"data"/"analysed_data"
PREPROCESS_DATA_DIR = PROJECT_DIR/"data"/"preprocessed_data"
REPORT_DIR = PROJECT_DIR/"report_html"

MYSQL_TABLE_NAME = "processed_data"
DAILY_STATION_SUMMARY_TABLE = "station_summary"
DAILY_NATIONAL_SUMMARY_TABLE  = "national_summary"
# print(PROJECT_DIR)#/Users/yliu/Desktop/learning/dummy_data_engineer_practise_my
# print(SOURCE_DATA_DIR)#/Users/yliu/Desktop/learning/dummy_data_engineer_practise_my/data/raw_data