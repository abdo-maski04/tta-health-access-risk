import requests

r = requests.get("https://api.open-meteo.com/v1/forecast", params={
    "latitude": "33.5883",     # remplace par 3 de tes communes
    "longitude": "-7.6114",
    "daily": "precipitation_sum,temperature_2m_max",
    "timezone": "Africa/Casablanca",
    "forecast_days": 3,
})
print(r.status_code)
data = r.json()
print(data)
