import pandas as pd

QUANTILES = [0.65, 0.80, 0.90]
RAIN_MIN_MM = 1.0      # un "jour pluvieux" = au moins 1 mm
MIN_RAIN_DAYS = 20     # en dessous, les percentiles de pluie sont jugés peu fiables


def compute_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    """Entrée : commune_code, date, precipitation_sum, temperature_2m_max.
    Sortie : une ligne par (commune_code, month), colonnes = celles de weather.thresholds."""
    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.month

    # Chaleur : tous les jours
    heat = df.groupby(["commune_code", "month"])["temperature_2m_max"].quantile(QUANTILES).unstack()
    heat.columns = ["heat_p65", "heat_p80", "heat_p90"]

    # Pluie : jours pluvieux seulement
    wet = df[df["precipitation_sum"] >= RAIN_MIN_MM]
    grouped = wet.groupby(["commune_code", "month"])["precipitation_sum"]
    rain = grouped.quantile(QUANTILES).unstack()
    rain.columns = ["rain_p65", "rain_p80", "rain_p90"]
    n_rain_days = grouped.size()
    rain.loc[n_rain_days.reindex(rain.index) < MIN_RAIN_DAYS] = float("nan")

    result = heat.join(rain, how="left").reset_index()
    return result[["commune_code", "month",
                   "rain_p65", "rain_p80", "rain_p90",
                   "heat_p65", "heat_p80", "heat_p90"]]
