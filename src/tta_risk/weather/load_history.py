import time

import pandas as pd

from src.tta_risk.db.database import (
    convert_df_to_rows,
    get_connection,
    load_weather_rows,
)
from src.tta_risk.weather.history_client import RateLimitError, fetch_commune_weather

# Constants
START_DATE = "2016-01-01"
END_DATE = "2025-12-31"
EXPECTED_DAYS = 3653  # 2016-01-01 -> 2025-12-31
CSV_PATH = "data/processed/communes_TTA_2024.csv"
MAX_PER_RUN = 90  # ~52 appels pondérés chacun : reste sous la limite horaire (5000)


def already_loaded():
    """Communes dont l'historique est complet en base (donc à ne pas retélécharger)."""
    query = """
        SELECT commune_code
        FROM weather.weather_daily
        GROUP BY commune_code
        HAVING count(*) = %s
    """
    with get_connection() as conn, conn.cursor() as cursor:
        cursor.execute(query, (EXPECTED_DAYS,))
        return {row[0] for row in cursor.fetchall()}


def main():
    communes = pd.read_csv(
        CSV_PATH,
        usecols=["commune_code", "centroid_lat", "centroid_lon"],
    )

    done = already_loaded()
    todo = communes[~communes["commune_code"].isin(done)]
    print(
        f"{len(done)} communes déjà complètes, {len(todo)} à charger "
        f"(maximum {MAX_PER_RUN} pour cette exécution)"
    )

    fetched = 0
    for commune in todo.itertuples(index=False):
        if fetched >= MAX_PER_RUN:
            print(f"Budget atteint ({fetched} communes). Relance dans 1 h.")
            break

        code = commune.commune_code
        print(f"Processing commune: {code}")

        try:
            df = fetch_commune_weather(
                code,
                commune.centroid_lat,
                commune.centroid_lon,
                START_DATE,
                END_DATE,
            )
        except RateLimitError as e:
            print(f"Limite atteinte sur {code} : {e}")
            print(f"{fetched} communes chargées pendant cette exécution. Relance plus tard.")
            break

        n = load_weather_rows(convert_df_to_rows(df))
        fetched += 1
        print(f"{n} rows loaded for {code}")

        time.sleep(2)  # évite d'envoyer les requêtes trop vite

    remaining = len(todo) - fetched
    if remaining == 0:
        print("Historical weather ingestion completed!")
    else:
        print(f"Il reste {remaining} communes à charger : relance le script plus tard.")


if __name__ == "__main__":
    main()
