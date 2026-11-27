"""Architecture et modélisation des isochrones d'accès hospitalier (15, 30, 45, 60 min).
Permet de modéliser les bassins d'accessibilité et la population exposée
à partir des 146 itinéraires v2 validés, sans consommer de quota ORS supplémentaire.
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
COMMUNES_GEOJSON = ROOT / "data" / "processed" / "communes_TTA.geojson"
COMMUNES_CSV = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
ROUTES_GEOJSON = ROOT / "data" / "processed" / "v2" / "travel_routes_TTA.geojson"
CSV_V2 = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"
HOSPITAL_WHITELIST = ROOT / "config" / "hospital_whitelist.json"
ISOCHRONES_OUT = ROOT / "data" / "processed" / "isochrones_tta_estimated.geojson"
ISOCHRONES_STATS_OUT = ROOT / "data" / "processed" / "isochrones_demographic_stats.json"

THRESHOLDS_MIN = [15, 30, 45, 60]


def load_inputs():
    with open(HOSPITAL_WHITELIST, encoding="utf-8") as f:
        hospitals = json.load(f)
    df_times = pd.read_csv(CSV_V2)
    gdf_com = gpd.read_file(COMMUNES_GEOJSON)
    df_pop = pd.read_csv(COMMUNES_CSV)
    return hospitals, df_times, gdf_com, df_pop


def estimate_empirical_isochrones(df_times, gdf_com, df_pop):
    print("Modélisation empirique des bassins temporels d'accessibilité hospitalière...")

    # Enrichir les communes avec la population 2024 et les métriques de trajet v2
    merged = gdf_com.merge(df_pop[["commune_code", "population_2024"]], on="commune_code", how="left")
    merged = merged.merge(
        df_times[["commune_code", "temps_min", "distance_km", "hospital_name", "classe_trajet"]],
        on="commune_code",
        how="left",
    )
    merged["population_2024"] = merged["population_2024"].fillna(0).astype(int)
    total_regional_pop = int(merged["population_2024"].sum())

    results = []
    for t in THRESHOLDS_MIN:
        subset = merged[merged["temps_min"] <= t]
        pop_accessible = int(subset["population_2024"].sum()) if not subset.empty else 0
        nb_communes = len(subset)

        if not subset.empty:
            combined_geom = subset.union_all()
            smoothed_geom = combined_geom.buffer(0.01).buffer(-0.005)
        else:
            smoothed_geom = Polygon()

        category = (
            "Zone d'urgence vitale immédiate"
            if t == 15
            else "Golden Hour (Heure d'Or chirurgicale)"
            if t == 30
            else "Accessibilité acceptable"
            if t == 45
            else "Seuil critique d'isolement territorial (> 60 min)"
        )

        pct_pop = round((pop_accessible / total_regional_pop * 100), 2) if total_regional_pop > 0 else 0.0

        results.append({
            "isochrone_min": t,
            "label": f"Accessibilité ≤ {t} min",
            "threshold_category": category,
            "nb_communes_couvertes": nb_communes,
            "population_couverte": pop_accessible,
            "pct_population_regionale": pct_pop,
            "geometry": smoothed_geom
        })

    gdf_iso = gpd.GeoDataFrame(results, crs="EPSG:4326")
    gdf_iso.to_file(ISOCHRONES_OUT, driver="GeoJSON")
    print(f"[OK] Isochrones empiriques enregistrés : {ISOCHRONES_OUT}")

    stats = {
        "method": "Empirical Regional Interpolation (146 validated ORS v2 routes)",
        "total_regional_population": total_regional_pop,
        "tiers": [
            {
                "threshold_min": r["isochrone_min"],
                "category": r["threshold_category"],
                "communes": r["nb_communes_couvertes"],
                "population": r["population_couverte"],
                "pct": r["pct_population_regionale"]
            }
            for r in results
        ]
    }
    with open(ISOCHRONES_STATS_OUT, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    print(f"[OK] Statistiques démographiques isochrones enregistrées : {ISOCHRONES_STATS_OUT}")
    return stats


def main():
    hospitals, df_times, gdf_com, df_pop = load_inputs()
    stats = estimate_empirical_isochrones(df_times, gdf_com, df_pop)
    print("\nSynthèse de la couverture isochrone TTA :")
    for tier in stats["tiers"]:
        print(f"  - {tier['category']} (≤ {tier['threshold_min']} min) : {tier['communes']} communes, {tier['population']:,} hab. ({tier['pct']}%)")


if __name__ == "__main__":
    main()
