import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()

upsert_query = """
INSERT INTO weather.weather_daily
    (commune_code, date, precipitation_sum, temperature_2m_max)
VALUES (%s, %s, %s, %s)
ON CONFLICT (commune_code, date) DO UPDATE
SET precipitation_sum  = EXCLUDED.precipitation_sum,
    temperature_2m_max = EXCLUDED.temperature_2m_max,
    ingested_at        = now(); """

def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        connect_timeout=10,
    )

def convert_df_to_rows(df):
    rows = list(
        df[
            [
                "commune_code",
                "date",
                "precipitation_sum",
                "temperature_2m_max"
            ]
        ].itertuples(index=False, name=None)
    )
    return rows

def load_weather_rows(rows):
    with get_connection() as conn:
        with conn.cursor() as cursor: # sert à
            cursor.executemany(upsert_query, rows)
            conn.commit()
    return len(rows)


def read_weather_daily():
    query = """
        SELECT commune_code, date, precipitation_sum, temperature_2m_max
        FROM weather.weather_daily
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(query)
            columns = [col.name for col in cursor.description]
            data = cursor.fetchall()
    return pd.DataFrame(data, columns=columns)


replace_thresholds_query = """
INSERT INTO weather.thresholds
    (commune_code, month,
     rain_p65, rain_p80, rain_p90,
     heat_p65, heat_p80, heat_p90)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
"""

def replace_thresholds(df):
    """Remplace tout le contenu de la table dans une seule transaction."""
    # NaN pandas -> None (sinon Postgres stocke 'NaN' au lieu de NULL)
    clean = df.astype(object).where(df.notna(), None)
    rows = list(clean.itertuples(index=False, name=None))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM weather.thresholds")
            cursor.executemany(replace_thresholds_query, rows)
        conn.commit()
    return len(rows)


upsert_forecast_query = """
INSERT INTO weather.forecast_daily
    (commune_code, forecast_issued_on, target_date, precip_mm, tmax_c)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (commune_code, forecast_issued_on, target_date) DO UPDATE
SET precip_mm   = EXCLUDED.precip_mm,
    tmax_c      = EXCLUDED.tmax_c,
    ingested_at = now();
"""

def convert_forecast_df_to_rows(df):
    # NaN pandas -> None, sinon Postgres stocke 'NaN' au lieu de NULL
    clean = df.astype(object).where(df.notna(), None)
    return list(
        clean[["commune_code", "forecast_issued_on", "target_date",
               "precip_mm", "tmax_c"]].itertuples(index=False, name=None)
    )

def load_forecast_rows(rows):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_forecast_query, rows)
        conn.commit()
    return len(rows)
