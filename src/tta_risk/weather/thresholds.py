
import pandas as pd

QUANTILES = [0.65, 0.80, 0.90]
RAIN_MIN_MM = 1.0


def compute_thresholds(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["month"] = pd.to_datetime(df["date"]).dt.month

    # Chaleur : tous les jours
    heat = (
        df.groupby(["commune_code", "month"])["temperature_2m_max"]
        .quantile(QUANTILES)
        .unstack()
    )
    heat.columns = ["heat_p65", "heat_p80", "heat_p90"]

    # Pluie : jours pluvieux seulement
    wet = df[df["precipitation_sum"] >= RAIN_MIN_MM]

    grouped = wet.groupby(
        ["commune_code", "month"]
    )["precipitation_sum"]

    rain = grouped.quantile(QUANTILES).unstack()
    rain.columns = ["rain_p65", "rain_p80", "rain_p90"]

    result = heat.join(rain, how="left").reset_index()

    return result[
        [
            "commune_code",
            "month",
            "rain_p65",
            "rain_p80",
            "rain_p90",
            "heat_p65",
            "heat_p80",
            "heat_p90",
        ]
    ]
