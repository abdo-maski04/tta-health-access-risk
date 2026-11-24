import numpy as np
import pandas as pd

RAIN_MIN_MM = 1.0  # en dessous, ce n'est pas un jour pluvieux

THRESHOLD_COLS = ["rain_p65", "rain_p80", "rain_p90",
                  "heat_p65", "heat_p80", "heat_p90"]


def _level(values, p65, p80, p90):
    """0 à 3 selon les seuils. Un NaN (valeur ou seuil manquant) donne 0."""
    return np.select(
        [values >= p90, values >= p80, values >= p65],
        [3, 2, 1],
        default=0,
    )


def compute_danger(df: pd.DataFrame) -> pd.DataFrame:
    """
    df : prévisions jointes aux seuils, avec les colonnes
         precip_mm, tmax_c, rain_p65/80/90, heat_p65/80/90.
    Ajoute : rain_level, heat_level, danger, dominant.
    """
    out = df.copy()
    for col in ["precip_mm", "tmax_c"] + THRESHOLD_COLS:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    rain = _level(out["precip_mm"], out["rain_p65"], out["rain_p80"], out["rain_p90"])
    rain = np.where(out["precip_mm"] < RAIN_MIN_MM, 0, rain)
    heat = _level(out["tmax_c"], out["heat_p65"], out["heat_p80"], out["heat_p90"])

    out["rain_level"] = rain.astype(int)
    out["heat_level"] = heat.astype(int)
    out["danger"] = np.maximum(out["rain_level"], out["heat_level"])

    # L'ordre compte : danger == 0 d'abord, sinon 0 et 0 donnerait "both"
    out["dominant"] = np.select(
        [out["danger"] == 0,
         out["rain_level"] > out["heat_level"],
         out["heat_level"] > out["rain_level"]],
        ["none", "rain", "heat"],
        default="both",   # niveaux égaux et > 0
    )
    return out
