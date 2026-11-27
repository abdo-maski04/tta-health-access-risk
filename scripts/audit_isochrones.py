"""Audit scientifique détaillé des isochrones interpolés."""

from pathlib import Path

import geopandas as gpd

ROOT = Path(__file__).resolve().parents[1]
ISO_PATH = ROOT / "data" / "processed" / "isochrones_tta_estimated.geojson"
STATS_PATH = ROOT / "data" / "processed" / "isochrones_demographic_stats.json"


def main():
    print("=== AUDIT SCIENTIFIQUE DES ISOCHRONES ESTIMÉS ===")
    gdf = gpd.read_file(ISO_PATH)
    print(f"Nombre de seuils générés : {len(gdf)}")
    for _, r in gdf.iterrows():
        p = r["properties"] if "properties" in r else r
        print(f"Seuil ≤ {p['isochrone_min']} min :")
        print(f"   - Catégorie : {p['threshold_category']}")
        print(f"   - Communes couvertes : {p['nb_communes_couvertes']} / 146")
        print(f"   - Population couverte : {p['population_couverte']:,} hab. ({p['pct_population_regionale']}%)")
        print(f"   - Géométrie : {r.geometry.geom_type}, aire (degrés²) = {r.geometry.area:.4f}")

    print("\nANALYSE SCIENTIFIQUE DE LA MÉTHODE :")
    print("1. Formule utilisée : Agrégation des polygones des communes dont le chef-lieu a temps_min <= seuil, suivie d'un lissage morphologique buffer(+0.01°).buffer(-0.005°).")
    print("2. Données d'entrée : Temps de parcours réels v2 des 146 communes vers leurs hôpitaux respectifs + polygones communaux + population RGPH 2024.")
    print("3. Limites scientifiques identifiées :")
    print("   - Ce ne sont PAS des isochrones de graphe routier continu calculés à partir du point source hospitalier (qui forment des étoiles/arborescences le long des axes).")
    print("   - L'accessibilité est attribuée à l'ensemble du polygone communal sur la base de son chef-lieu (effet de masquage intra-communal).")
    print("   - Verdict scientifique : Catégorie B (Modélisation empirique macro-territoriale, exploitable pour l'aide à la décision régionale avec avertissement).")


if __name__ == "__main__":
    main()
