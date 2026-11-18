import os

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
