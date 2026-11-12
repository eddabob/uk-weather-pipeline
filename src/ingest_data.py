# This program will ingest one day hourly weather data 
# from 30 main UK weather stations
# https://api.weatherapi.com/v1/current.json?key=0c282e441dd14883a39192528260811&q=London
# import requests res = requests.get('https://api.weatherapi.com/v1/current.json?key=0c282e441dd14883a39192528260811&q=London') print(res.json())

import pandas as pd
import requests

def ingest_data(API_KEY, LOCATIONS, TARGET_DATE, output_file_path):
    # IMMUNE TO SYSTEM STRIPPING: Dynamically building the absolute API path
    DOMAIN_PART = "api" + "." + "weatherapi" + ".com"
    ENDPOINT_PART = "/" + "v1" + "/" + "history" + "." + "json"
    BASE_URL = f"http://{DOMAIN_PART}{ENDPOINT_PART}"
    #print(BASE_URL) #http://api.weatherapi.com/v1/history.json

    all_rows = [] #list of dictionaries

    #print(f"🚀 Starting 24-hour WeatherAPI data ingest loop for {TARGET_DATE}...")

    for city in LOCATIONS:
        params = {
            "key": API_KEY,
            "q": city,
            "dt": TARGET_DATE
        }
        
        try:
            response = requests.get(BASE_URL, params=params)
            #http://api.weatherapi.com/v1/history.json?key=0c282e441dd14883a39192528260811&q=London&dt=2026-11-07

            response.raise_for_status()
            data = response.json()
            #print(data)

            # Extract top-level location metadata details
            location_meta = data.get("location", {}) 
            #• The second argument ({}) is a fallback default value (an empty dictionary).
            #  If the "location" key is missing, Python returns {} instead of crashing the program.

            #print(location_meta)

            city_name = location_meta.get("name")
            lat = location_meta.get("lat")
            lon = location_meta.get("lon")
            
            # WeatherAPI groups historical entries under forecast -> forecastday -> hour list
            
            forecast_days = data.get("forecast", {}).get("forecastday", [])
            #Because .get("condition", {}) guarantees you will get a dictionary back 
            # (even if it's empty), you can safely chain another .get() 

            #print(forecast_days)
            #forecast_days is a list, as we only query one day, so the list is length 1, 
            # so use forecast_days[0] to get the one day record we queried

            if forecast_days:
                # Grab the 24 hourly data array points from the first day matched
                #print(forecast_days[0])
                """
                {
                    "date": "2026-11-07",
                    "day": {
                        "maxtemp_c": 11.4,
                        "mintemp_c": 6.2,
                        "totalprecip_mm": 0.0,
                        # ... other daily summary metrics
                    },
                    "astro": {
                        "sunrise": "07:05 AM",
                        "sunset": "04:22 PM"
                    },
                    "hour": [
                        # This is an array of 24 distinct dictionaries (one for each hour)
                        {"time": "2026-11-07 00:00", "temp_c": 7.2, ...},
                        {"time": "2026-11-07 01:00", "temp_c": 7.0, ...},
                        # ... up to index [23]
                    ]
                }
                """
                hourly_records = forecast_days[0].get("hour", []) # hourly_records is a list of hours record
                for hour_data in hourly_records:
                    #print(hour_data)
                    """
                    {'time_epoch': 1794013200, 'time': '2026-11-07 01:00', 
                    'temp_c': 6.7, 'temp_f': 44.1, 'is_day': 0, 
                    'condition': {'text': 'Clear', 'icon': '//cdn.weatherapi.com/weather/64x64/night/113.png', 'code': 1000}, 
                    'wind_mph': 1.6, 'wind_kph': 2.5, 'wind_degree': 350, 'wind_dir': 'N', 
                    'pressure_mb': 1023.0, 'pressure_in': 30.22, 'precip_mm': 0.0, 
                    'precip_in': 0.0, 'snow_cm': 0.0, 'humidity': 90, 'cloud': 6, 
                    'feelslike_c': 6.7, 'feelslike_f': 44.1, 'windchill_c': 6.7, 
                    'windchill_f': 44.1, 'heatindex_c': 6.7, 'heatindex_f': 44.1, 
                    'dewpoint_c': 6.0, 'dewpoint_f': 42.8, 'will_it_rain': 0, 
                    'chance_of_rain': 0, 'will_it_snow': 0, 'chance_of_snow': 0, 
                    'vis_km': 5.1, 'vis_miles': 3.0, 'gust_mph': 5.7, 'gust_kph': 9.2, 'uv': 0.0}
                    """
                    row = {
                        "date": TARGET_DATE,
                        "timestamp": hour_data.get("time"),
                        "station_name": city_name,
                        "latitude": lat,
                        "longitude": lon,
                        "temp_c": hour_data.get("temp_c"),
                        "humidity_pct": hour_data.get("humidity"),
                        "wind_speed_mph": hour_data.get("wind_mph"),
                        "pressure_mb": hour_data.get("pressure_mb"),
                        "condition_text": hour_data.get("condition", {}).get("text")
                    }
                    all_rows.append(row)
                    #print("------------------------------------------------")
                print(f"Successfully extracted 24 hours of data for: {city_name}")
            else:
                print(f"No hourly blocks returned for city: {city}")
                
        except requests.exceptions.HTTPError as http_err:
            print(f"API Error for {city}: {http_err}")
        except Exception as e:
            print(f"Processing failure for {city}: {e}")

    # 2. Build structured layout out to a flat CSV file
    if all_rows:
        df = pd.DataFrame(all_rows)
        output_filename = output_file_path
        df.to_csv(output_filename, index=False, encoding="utf-8")
        print(f"Success! Output tracking file written to: {output_filename} ({len(df)} rows)")
    else:
        print("\nPipeline Error: No metrics were written to memory.")


# LOCATIONS = [
#     # --- Scotland ---
#     "Glasgow", "Aberdeen", "Inverness", "Dundee", "Lerwick", 
    
#     # --- Northern Ireland ---
#     "Londonderry", "Enniskillen", "Newry",
    
#     # --- Wales ---
#     "Swansea", "Bangor", "Aberystwyth", "Holyhead",
    
#     # --- North England ---
#     "Newcastle", "Leeds", "Liverpool", "Sheffield", "York", "Carlisle",
    
#     # --- Midlands & East England ---
#     "Birmingham", "Nottingham", "Leicester", "Norwich", "Cambridge",
    
#     # --- South England & Channels ---
#     "Bristol", "Southampton", "Plymouth", "Brighton", "Exeter", "Dover",
    
#     # --- Critical Airport Hubs ---
#     "Heathrow", "Gatwick", "Manchester Airport"
# ]

### sample response:
# {
#   "location": {
#     "name": "London",
#     "region": "City of London, Greater London",
#     "country": "United Kingdom",
#     "lat": 51.5171,
#     "lon": -0.1062,
#     "tz_id": "Europe/London",
#     "localtime_epoch": 1794166906,
#     "localtime": "2026-11-08 19:41"
#   },
#   "forecast": {
#     "forecastday": [
#       {
#         "date": "2026-11-07",
#         "date_epoch": 1794009600,
#         "day": {
#           "maxtemp_c": 10.4,
#           "maxtemp_f": 50.7,
#           "mintemp_c": 5.1,
#           "mintemp_f": 41.2,
#           "avgtemp_c": 7.4,
#           "avgtemp_f": 45.2,
#           "maxwind_mph": 2.0,
#           "maxwind_kph": 3.2,
#           "totalprecip_mm": 0.0,
#           "totalprecip_in": 0.0,
#           "totalsnow_cm": 0.0,
#           "avgvis_km": 9.1,
#           "avgvis_miles": 5.0,
#           "avghumidity": 83,
#           "daily_will_it_rain": 0,
#           "daily_chance_of_rain": 0,
#           "daily_will_it_snow": 0,
#           "daily_chance_of_snow": 0,
#           "condition": {
#             "text": "Cloudy",
#             "icon": "//cdn.weatherapi.com/weather/64x64/day/119.png",
#             "code": 1006
#           },
#           "uv": 0.1
#         },
#         "astro": {
#           "sunrise": "07:04 AM",
#           "sunset": "04:23 PM",
#           "moonrise": "04:58 AM",
#           "moonset": "03:07 PM",
#           "moon_phase": "New Moon",
#           "moon_illumination": 2
#         },
#         "hour": [
#           {
#             "time_epoch": 1794009600,
#             "time": "2026-11-07 00:00",
#             "temp_c": 6.7,
#             "temp_f": 44.1,
#             "is_day": 0,
#             "condition": {
#               "text": "Cloudy",
#               "icon": "//cdn.weatherapi.com/weather/64x64/night/119.png",
#               "code": 1006
#             },
#             "wind_mph": 0.2,
#             "wind_kph": 0.4,
#             "wind_degree": 314,
#             "wind_dir": "NW",
#             "pressure_mb": 1024.0,
#             "pressure_in": 30.23,
#             "precip_mm": 0.0,
#             "precip_in": 0.0,
#             "snow_cm": 0.0,
#             "humidity": 96,
#             "cloud": 72,
#             "feelslike_c": 6.7,
#             "feelslike_f": 44.1,
#             "windchill_c": 6.7,
#             "windchill_f": 44.1,
#             "heatindex_c": 6.7,
#             "heatindex_f": 44.1,
#             "dewpoint_c": 6.1,
#             "dewpoint_f": 43.0,
#             "will_it_rain": 0,
#             "chance_of_rain": 0,
#             "will_it_snow": 0,
#             "chance_of_snow": 0,
#             "vis_km": 10.0,
#             "vis_miles": 6.0,
#             "gust_mph": 1.1,
#             "gust_kph": 1.8,
#             "uv": 0.0
#           },
#           {
#             "time_epoch": 1794013200,
#             "time": "2026-11-07 01:00",
#             "temp_c": 6.7,
#             "temp_f": 44.1,
#             "is_day": 0,
#             "condition": {
#               "text": "Clear",
#               "icon": "//cdn.weatherapi.com/weather/64x64/night/113.png",
#               "code": 1000
#             },
#             "wind_mph": 1.6,
#             "wind_kph": 2.5,
#             "wind_degree": 350,
#             "wind_dir": "N",
#             "pressure_mb": 1023.0,
#             "pressure_in": 30.22,
#             "precip_mm": 0.0,
#             "precip_in": 0.0,
#             "snow_cm": 0.0,
#             "humidity": 90,
#             "cloud": 6,
#             "feelslike_c": 6.7,
#             "feelslike_f": 44.1,
#             "windchill_c": 6.7,
#             "windchill_f": 44.1,
#             "heatindex_c": 6.7,
#             "heatindex_f": 44.1,
#             "dewpoint_c": 6.0,
#             "dewpoint_f": 42.8,
#             "will_it_rain": 0,
#             "chance_of_rain": 0,
#             "will_it_snow": 0,
#             "chance_of_snow": 0,
#             "vis_km": 5.1,
#             "vis_miles": 3.0,
#             "gust_mph": 5.7,
#             "gust_kph": 9.2,
#             "uv": 0.0
#           },