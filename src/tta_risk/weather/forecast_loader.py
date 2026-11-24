import time

import pandas as pd

from src.tta_risk.db.database import convert_forecast_df_to_rows, load_forecast_rows
from src.tta_risk.weather.forecast_client import fetch_commune_forecast

CSV_PATH = "data/processed/communes_TTA_2024.csv"
PAUSE_SECONDS = 0.3


def load_forecast(issued_on=None, csv_path=CSV_PATH):
    """Récupère les prévisions des communes du CSV et les charge dans weather.forecast_daily.
    Retourne (nombre de lignes écrites, nombre de communes du CSV, liste des communes en échec)."""
    communes = pd.read_csv(
        csv_path,
        usecols=["commune_code", "centroid_lat", "centroid_lon"]
    )

    total = 0
    failed = []
    for commune in communes.itertuples(index=False):
        try:
            df = fetch_commune_forecast(
                commune.commune_code,
                commune.centroid_lat,
                commune.centroid_lon,
                issued_on,
            )
            total += load_forecast_rows(convert_forecast_df_to_rows(df))
        except Exception as e:
            print(f"Échec pour {commune.commune_code} : {e}")
            failed.append(commune.commune_code)
        time.sleep(PAUSE_SECONDS)

    return total, len(communes), failed


if __name__ == "__main__":
    n, n_communes, failed = load_forecast()
    print(f"{n} lignes insérées (attendu : {n_communes} communes x 3 jours = {n_communes * 3})")
    if failed:
        print(f"{len(failed)} communes en échec : {failed}")
