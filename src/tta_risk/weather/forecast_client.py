import time
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests as req

URL_API = "https://api.open-meteo.com/v1/forecast"
DAILY = "precipitation_sum,temperature_2m_max"
TIMEZONE = "Africa/Casablanca"
FORECAST_DAYS = 3
MAX_ATTEMPTS = 5


def fetch_commune_forecast(commune_code, latitude, longitude, issued_on=None):
    issued_on = issued_on or datetime.now(ZoneInfo(TIMEZONE)).date()
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": DAILY,
        "timezone": TIMEZONE,
        "forecast_days": FORECAST_DAYS,
    }
    for att in range(MAX_ATTEMPTS):
        try:
            response = req.get(URL_API, params=params, timeout=60)
            if response.status_code not in (429, 500, 502, 503, 504):
                break
            print(f"  http status {response.status_code}, attempt {att + 1}/{MAX_ATTEMPTS}")
        except (req.exceptions.Timeout, req.exceptions.ConnectionError):
            if att == MAX_ATTEMPTS - 1:
                raise
        if att < MAX_ATTEMPTS - 1:
            time.sleep(10 * (att + 1))   # 10 s, 20 s... (plus court que pour l'historique)

    response.raise_for_status()

    df = pd.DataFrame(response.json()["daily"])
    df.rename(columns={"time": "target_date",
                       "precipitation_sum": "precip_mm",
                       "temperature_2m_max": "tmax_c"}, inplace=True)
    df["target_date"] = pd.to_datetime(df["target_date"]).dt.date
    df["commune_code"] = commune_code
    df["forecast_issued_on"] = issued_on
    return df[["commune_code", "forecast_issued_on", "target_date", "precip_mm", "tmax_c"]]
