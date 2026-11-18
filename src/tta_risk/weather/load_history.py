
import time

import pandas as pd

from src.tta_risk.db.database import convert_df_to_rows, load_weather_rows
from src.tta_risk.weather.history_client import fetch_commune_weather

# Constants
START_DATE = "2016-01-01"
END_DATE = "2025-12-31"
CSV_PATH = "data/processed/communes_TTA_2024.csv"

# Read communes CSV
communes = pd.read_csv(
    CSV_PATH,
    usecols=["commune_code", "centroid_lat", "centroid_lon"]
)

# Loop through communes
for commune in communes.itertuples(index=False):

    code = commune.commune_code
    lat = commune.centroid_lat
    lon = commune.centroid_lon

    print(f"Processing commune: {code}")

    # 1. Fetch weather data
    df = fetch_commune_weather(
        code,
        lat,
        lon,
        START_DATE,
        END_DATE
    )

    # 2. Convert DataFrame into rows
    rows = convert_df_to_rows(df)

    # 3. Load data into PostgreSQL
    n = load_weather_rows(rows)

    print(f"{n} rows loaded for {code}")

    # Avoid sending requests too quickly
    time.sleep(2)

print("Historical weather ingestion completed!")
