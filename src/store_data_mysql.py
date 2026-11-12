# This script will store the preprocessed csv data onto mysql database
# columns: ['date', 'station_name', 'temp_c', 'humidity_pct', 'wind_speed_mph', 
# 'pressure_mb', 'condition_text', 'hour_of_day', 'is_freezing', 'feels_like_c', 
# 'pressure_trend']
import pandas as pd
from sqlalchemy import create_engine, text
# from project_config import PREPROCESS_DATA_DIR, MYSQL_TABLE_NAME, DAILY_STATION_SUMMARY_TABLE,DAILY_STATION_SUMMARY_TABLE
# from data_setting import TARGET_DATE

# import configparser
# config = configparser.ConfigParser()
# config.read("config.ini")

# USER = config["MYSQL"]["USER"]
# PASSWORD = config["MYSQL"]["PASSWORD"]
# HOST = config["MYSQL"]["HOST"]
# DATABASE = config["MYSQL"]["DATABASE"]

# TABLE_NAME = MYSQL_TABLE_NAME
# input_csv_file = PREPROCESS_DATA_DIR/f"transformed_{TARGET_DATE}.csv"


# create a connection to the database
def create_database_engine(USERNAME, PASS, HOSTNAME, DATABASE_NAME):
    engine = create_engine(f"mysql+pymysql://{USERNAME}:{PASS}@{HOSTNAME}/{DATABASE_NAME}")
    return engine

def execute_sql_statement(connection, sql_statements):
    for statement in sql_statements.split(";"):
        statement = statement.strip()
        if statement:
            connection.execute(text(statement))
    print("SQL statement executed successfully!")

def create_table(table_name):
    sql_str = f"""
        DROP TABLE if EXISTS {table_name};
        CREATE TABLE {table_name} (
            date DATE NOT NULL,
            station_name VARCHAR(50) NOT NULL,
            temp_c DECIMAL(4,1),
            humidity_pct INT,
            wind_speed_mph DECIMAL(4,1),
            pressure_mb DECIMAL(6,1),
            condition_text VARCHAR(50),
            hour_of_day INT,
            is_freezing BOOLEAN,
            feels_like_c DECIMAL(4,1),
            pressure_trend VARCHAR(50)
        );
    """
    return sql_str

def create_daily_station_table(table_name):
    sql_str = f"""
        DROP TABLE if EXISTS {table_name};
        CREATE TABLE {table_name}(
            date DATE NOT NULL,
            station_name VARCHAR(50) NOT NULL,
            avg_temp_c DECIMAL(4,1),
            max_temp_c DECIMAL(4,1),
            min_temp_c DECIMAL(4,1),
            avg_humidity_pct INT,
            max_wind_speed_mph DECIMAL(4,1),
            avg_pressure_mb DECIMAL(6,1),
            freezing_hours_count INT,
            PRIMARY KEY(date, station_name)
        );
    """
    return sql_str

def create_daily_national_table(table_name):
    sql_str = f"""
        DROP TABLE if EXISTS {table_name};
        CREATE TABLE {table_name} (
            date DATE NOT NULL,
            national_avg_temp_c DECIMAL(4,1),
            warmest_station_name VARCHAR(50),
            warmest_station_temp DECIMAL(4,1),
            windiest_station_name VARCHAR(50),
            national_peak_wind_mph DECIMAL(4,1),
            PRIMARY KEY(date)
        );
    """
    return sql_str

def insert_values(csv_file_path, table_name, sql_engine):
    df = pd.read_csv(csv_file_path)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # this inserting method also working:
    #for csv_file, table_name in files_to_tables.items():
        # df.to_sql() manages the database insertion for you, 
        # while conn.execute() relies on conn being a valid connection and the transaction being committed.
    #conn = engine.connect() 
    df.to_sql(
        name=table_name,
        con=sql_engine,
        if_exists="append",
        index=False,
        chunksize=100
    )
    print(f"Inserted MYSQL table '{table_name}': {df.shape[0]} rows")

if __name__ == "__main__":
    ### 1. create a connection to the database
    # An engine manages connections to your database. We'll open a connection when we need one and close it when we're done. 
    # This is a best practice to avoid leaving connections open.
    engine = create_database_engine(USER, PASSWORD, HOST, DATABASE)
    conn = engine.connect() 
    create_table_str = create_table(TABLE_NAME)
    execute_sql_statement(conn, create_table_str)
    insert_values(input_csv_file, TABLE_NAME, engine)

# Right now, your script re-creates the table structure or appends blindly. 
# To make this a true enterprise pipeline, you can modify your insert_values module to use MySQL's
# ON DUPLICATE KEY UPDATE syntax. This ensures that if a script is run twice for the same hour/station, 
# it updates the existing row instead of making a messy duplicate.




