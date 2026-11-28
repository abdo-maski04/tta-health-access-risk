import os

import pandas as pd
import psycopg
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=int(os.getenv("POSTGRES_PORT")),
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        connect_timeout=10,
    )


# ---------------------------------------------------------------------------
# Historique météo (weather.weather_daily)
# ---------------------------------------------------------------------------

upsert_query = """
INSERT INTO weather.weather_daily
    (commune_code, date, precipitation_sum, temperature_2m_max)
VALUES (%s, %s, %s, %s)
ON CONFLICT (commune_code, date) DO UPDATE
SET precipitation_sum  = EXCLUDED.precipitation_sum,
    temperature_2m_max = EXCLUDED.temperature_2m_max,
    ingested_at        = now(); """


def convert_df_to_rows(df):
    rows = list(
        df[["commune_code", "date", "precipitation_sum", "temperature_2m_max"]].itertuples(
            index=False, name=None
        )
    )
    return rows


def load_weather_rows(rows):
    with get_connection() as conn:
        with conn.cursor() as cursor:
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


# ---------------------------------------------------------------------------
# Seuils (weather.thresholds)
# ---------------------------------------------------------------------------

replace_thresholds_query = """
INSERT INTO weather.thresholds
    (commune_code, month,
     rain_p65, rain_p80, rain_p90,
     heat_p65, heat_p80, heat_p90)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
"""


def replace_thresholds(df):
    """Remplace tout le contenu de la table dans une seule transaction."""
    # Garde : un DataFrame vide viderait la table sans rien réinsérer
    if df is None or df.empty:
        raise ValueError(
            "replace_thresholds : DataFrame vide, weather.thresholds n'est pas modifiée."
        )

    # NaN pandas -> None (sinon Postgres stocke 'NaN' au lieu de NULL)
    clean = df.astype(object).where(df.notna(), None)
    rows = list(clean.itertuples(index=False, name=None))

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM weather.thresholds")
            cursor.executemany(replace_thresholds_query, rows)
        conn.commit()
    return len(rows)


# ---------------------------------------------------------------------------
# Prévisions (weather.forecast_daily)
# ---------------------------------------------------------------------------


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
        clean[
            ["commune_code", "forecast_issued_on", "target_date", "precip_mm", "tmax_c"]
        ].itertuples(index=False, name=None)
    )


def load_forecast_rows(rows):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_forecast_query, rows)
        conn.commit()
    return len(rows)


def get_latest_forecast_date():
    """Dernière date d'émission des prévisions présente en base (ou None)."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT max(forecast_issued_on) FROM weather.forecast_daily")
            return cursor.fetchone()[0]


read_forecast_with_thresholds_query = """
SELECT f.commune_code, f.forecast_issued_on, f.target_date,
       f.precip_mm, f.tmax_c,
       t.rain_p65, t.rain_p80, t.rain_p90,
       t.heat_p65, t.heat_p80, t.heat_p90
FROM weather.forecast_daily f
LEFT JOIN weather.thresholds t
       ON t.commune_code = f.commune_code
      AND t.month = EXTRACT(MONTH FROM f.target_date)::smallint
WHERE f.forecast_issued_on = %s
ORDER BY f.commune_code, f.target_date;
"""


def read_forecast_with_thresholds(issued_on):
    """Prévisions d'une date d'émission, jointes aux seuils du mois cible."""
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(read_forecast_with_thresholds_query, (issued_on,))
            columns = [col.name for col in cursor.description]
            data = cursor.fetchall()
    return pd.DataFrame(data, columns=columns)


# ---------------------------------------------------------------------------
# Danger quotidien (weather.risk_daily)
# ---------------------------------------------------------------------------

COLONNES_RISK = (
    "commune_code",
    "forecast_issued_on",
    "target_date",
    "precip_mm",
    "tmax_c",
    "rain_level",
    "heat_level",
    "danger",
    "dominant",
    "classe_trajet",
    "score",
    "niveau",
    "raison",
)

upsert_risk_query = """
INSERT INTO weather.risk_daily
    (commune_code, forecast_issued_on, target_date, precip_mm, tmax_c,
     rain_level, heat_level, danger, dominant,
     classe_trajet, score, niveau, raison)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (commune_code, forecast_issued_on, target_date) DO UPDATE
SET precip_mm     = EXCLUDED.precip_mm,
    tmax_c        = EXCLUDED.tmax_c,
    rain_level    = EXCLUDED.rain_level,
    heat_level    = EXCLUDED.heat_level,
    danger        = EXCLUDED.danger,
    dominant      = EXCLUDED.dominant,
    classe_trajet = EXCLUDED.classe_trajet,
    score         = EXCLUDED.score,
    niveau        = EXCLUDED.niveau,
    raison        = EXCLUDED.raison,
    computed_at   = now();
"""


def convert_risk_df_to_rows(df):
    # NaN pandas -> None, et types numpy -> types Python (psycopg)
    # Les colonnes absentes du DataFrame (anciens tests) sont remplies a None :
    # le nombre de valeurs reste 13, donc l'ordre de l'INSERT est respecte.
    complet = df.copy()
    for colonne in COLONNES_RISK:
        if colonne not in complet.columns:
            complet[colonne] = None
    clean = complet.astype(object).where(complet.notna(), None)
    return list(clean[list(COLONNES_RISK)].itertuples(index=False, name=None))


def load_risk_rows(rows):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_risk_query, rows)
        conn.commit()
    return len(rows)
