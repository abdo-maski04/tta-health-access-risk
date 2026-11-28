import sys
from datetime import date

from src.tta_risk.db.database import (
    convert_risk_df_to_rows,
    get_latest_forecast_date,
    load_risk_rows,
    read_forecast_with_thresholds,
)
from src.tta_risk.scoring.daily import ajouter_score, charger_temps, verifier_temps
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

    # Le score a besoin du temps de trajet de chaque commune (D-015 : 15 / 45 min).
    result = result.merge(charger_temps(), on="commune_code", how="left", validate="many_to_one")
    verifier_temps(result)
    result = ajouter_score(result)

    n = load_risk_rows(convert_risk_df_to_rows(result))

    print(f"{n} lignes écrites dans weather.risk_daily (prévisions du {issued_on})")
    print("danger (0-3) :")
    print(result["danger"].value_counts().sort_index().to_string())
    print("score (0,1,2,3,4,6,9) :")
    print(result["score"].value_counts().sort_index().to_string())
    print("niveau :")
    print(result["niveau"].value_counts().to_string())
    print("raison :")
    print(result["raison"].value_counts().to_string())
    return n


if __name__ == "__main__":
    # python scripts/run_risk_daily.py            -> dernière prévision
    # python scripts/run_risk_daily.py 2026-11-22 -> une date précise
    arg = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else None
    run(arg)
