import time

import pandas as pd
import requests as req

# constants
URL_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY = "precipitation_sum,temperature_2m_max"
TIMEZONE = "Africa/Casablanca"
MAX_ATTEMPTS = 5


def fetch_commune_weather(commune_code, latitude, longitude, start_date, end_date):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": DAILY,
        "timezone": TIMEZONE,
    }
    for att in range(MAX_ATTEMPTS):
        try:
            response = req.get(URL_API, params=params, timeout=60)
            if response.status_code not in (429, 500, 502, 503, 504):
                break
            print(f"  http status {response.status_code}, attempt {att + 1}/{MAX_ATTEMPTS}")
        except (req.exceptions.Timeout, req.exceptions.ConnectionError):
            if att == MAX_ATTEMPTS - 1:
                raise  # re-raise on the last attempt
        if att < MAX_ATTEMPTS - 1:
            time.sleep(30 * (att + 1))  # wait 30s, 60s, 90s... before retrying

    print("http status", response.status_code)
    response.raise_for_status()  # raise an exception for HTTP errors

    df = pd.DataFrame(response.json()["daily"])
    df.rename(columns={"time": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["commune_code"] = commune_code
    return df[["commune_code", "date", "precipitation_sum", "temperature_2m_max"]]

