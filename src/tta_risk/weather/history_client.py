import time

import pandas as pd
import requests as req

# constants
URL_API = "https://archive-api.open-meteo.com/v1/archive"
DAILY = "precipitation_sum,temperature_2m_max"
TIMEZONE = "Africa/Casablanca"
MAX_ATTEMPTS = 5


class RateLimitError(Exception):
    """Limite horaire ou journalière atteinte : inutile de réessayer maintenant."""


def _reason(response):
    """Message d'Open-Meteo pour un 429 (indique quelle limite est atteinte)."""
    try:
        return response.json().get("reason", response.text)
    except ValueError:
        return response.text


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
        except (req.exceptions.Timeout, req.exceptions.ConnectionError):
            if att == MAX_ATTEMPTS - 1:
                raise
            time.sleep(5 * (att + 1))
            continue

        if response.status_code == 429:
            reason = _reason(response)
            # Limite par minute : une courte pause suffit. Sinon (heure, jour) : on arrête.
            if "minute" in reason.lower() and att < MAX_ATTEMPTS - 1:
                print(f"  429 (minute) : pause de 65 s, tentative {att + 1}/{MAX_ATTEMPTS}")
                time.sleep(65)
                continue
            raise RateLimitError(reason)

        if response.status_code in (500, 502, 503, 504) and att < MAX_ATTEMPTS - 1:
            print(f"  http status {response.status_code}, tentative {att + 1}/{MAX_ATTEMPTS}")
            time.sleep(5 * (att + 1))
            continue

        break

    response.raise_for_status()

    df = pd.DataFrame(response.json()["daily"])
    df.rename(columns={"time": "date"}, inplace=True)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["commune_code"] = commune_code
    return df[["commune_code", "date", "precipitation_sum", "temperature_2m_max"]]
