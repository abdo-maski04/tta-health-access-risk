from src.tta_risk.db.database import read_weather_daily, replace_thresholds
from src.tta_risk.weather.thresholds import compute_thresholds


def main():
    weather = read_weather_daily()
    print(f"{weather['commune_code'].nunique()} communes, {len(weather)} lignes lues")

    thresholds = compute_thresholds(weather)
    print(f"{len(thresholds)} lignes de seuils calculées (attendu : 146 x 12 = 1752)")
    print(f"Mois sans seuil de pluie fiable : {thresholds['rain_p90'].isna().sum()}")

    n = replace_thresholds(thresholds)
    print(f"{n} lignes écrites dans weather.thresholds.")


if __name__ == "__main__":
    main()
