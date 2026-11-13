"""Test d'intégration : les API Open-Meteo répondent avec les bonnes données."""
import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Tanger (coordonnées approximatives, juste pour le test)
LAT, LON = 35.7595, -5.8340

PARAMS = {
    "latitude": LAT,
    "longitude": LON,
    "daily": "precipitation_sum,temperature_2m_max",
    "timezone": "Africa/Casablanca",
}


def test_forecast_returns_7_days():
    resp = requests.get(FORECAST_URL, params={**PARAMS, "forecast_days": 7}, timeout=30)
    assert resp.status_code == 200

    daily = resp.json()["daily"]
    assert len(daily["time"]) == 7
    assert len(daily["precipitation_sum"]) == 7
    assert len(daily["temperature_2m_max"]) == 7
    assert None not in daily["temperature_2m_max"]


def test_archive_returns_full_year():
    params = {**PARAMS, "start_date": "2024-01-01", "end_date": "2024-12-31"}
    resp = requests.get(ARCHIVE_URL, params=params, timeout=30)
    assert resp.status_code == 200

    daily = resp.json()["daily"]
    assert len(daily["time"]) == 366  # 2024 est bissextile
    assert None not in daily["temperature_2m_max"]
