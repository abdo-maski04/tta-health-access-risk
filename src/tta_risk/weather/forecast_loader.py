import time

import pandas as pd

from src.tta_risk.db.database import convert_forecast_df_to_rows, load_forecast_rows
from src.tta_risk.weather.forecast_client import fetch_commune_forecast

CSV_PATH = "data/processed/communes_TTA_2024.csv"
PAUSE_SECONDS = 0.3


def load_forecast(issued_on=None, csv_path=CSV_PATH):
    """Récupère les prévisions des 146 communes et les charge dans weather.forecast_daily.
    Retourne le nombre de lignes écrites."""
    communes = pd.read_csv(
        csv_path,
        usecols=["commune_code", "centroid_lat", "centroid_lon"]
    )

    total = 0
    for commune in communes.itertuples(index=False):
        df = fetch_commune_forecast(
            commune.commune_code,
            commune.centroid_lat,
            commune.centroid_lon,
            issued_on,
        )
        total += load_forecast_rows(convert_forecast_df_to_rows(df))
        time.sleep(PAUSE_SECONDS)
        return total


if __name__ == "__main__":
    n = load_forecast()
    print(f"{n} lignes insérées (attendu : 438)")
