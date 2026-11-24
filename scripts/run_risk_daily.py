import sys
from datetime import date

from src.tta_risk.db.database import (
    convert_risk_df_to_rows,
    get_latest_forecast_date,
    load_risk_rows,
    read_forecast_with_thresholds,
)
from src.tta_risk.scoring.danger import compute_danger


def run(issued_on=None):
    issued_on = issued_on or get_latest_forecast_date()
    if issued_on is None:
        raise RuntimeError("Aucune prévision en base : lance d'abord le script des prévisions.")

    df = read_forecast_with_thresholds(issued_on)
    if df.empty:
        raise RuntimeError(f"Aucune prévision pour forecast_issued_on = {issued_on}")

    missing = df["rain_p65"].isna().sum()
    if missing:
        print(f"Attention : {missing} lignes sans seuils (niveaux mis à 0)")

    result = compute_danger(df)
    n = load_risk_rows(convert_risk_df_to_rows(result))

    print(f"{n} lignes écrites dans weather.risk_daily (prévisions du {issued_on})")
    print(result["danger"].value_counts().sort_index().to_string())
    return n


if __name__ == "__main__":
    # python scripts/run_risk_daily.py            -> dernière prévision
    # python scripts/run_risk_daily.py 2026-11-22 -> une date précise
    arg = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(arg)
