"""Audit scientifique exhaustif des données administratives et géographiques de TTA.
Vérifie les 146 communes, la géométrie, la topologie, le CRS, les provinces et la cohérence inter-fichiers.
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
COMMUNES_GEOJSON = ROOT / "data" / "processed" / "communes_TTA.geojson"
COMMUNES_CSV = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
MINISTERE_BY_COMMUNE = ROOT / "data" / "processed" / "official_public_health_by_commune_2025.csv"
TRAVEL_TIME_V2 = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"
TRAVEL_TIME_HAKIMA = ROOT / "data" / "processed" / "travel_time_TTA_2024.csv"


def main():
    print("=== AUDIT DES DONNÉES ADMINISTRATIVES ET LIMITES GÉOGRAPHIQUES ===")
    report = {}

    # 1. Chargement communes_TTA.geojson
    gdf_gj = gpd.read_file(COMMUNES_GEOJSON)
    print(f"1. communes_TTA.geojson : {len(gdf_gj)} entités chargées, CRS = {gdf_gj.crs}")
    report["count_geojson"] = len(gdf_gj)
    report["crs_geojson"] = str(gdf_gj.crs)

    # Vérification validité géométrique
    invalid_geoms = gdf_gj[~gdf_gj.is_valid]
    empty_geoms = gdf_gj[gdf_gj.is_empty]
    print(f"   - Géométries invalides : {len(invalid_geoms)}")
    print(f"   - Géométries vides : {len(empty_geoms)}")
    report["invalid_geometries_count"] = len(invalid_geoms)
    report["empty_geometries_count"] = len(empty_geoms)

    # Vérification de l'emprise
    minx, miny, maxx, maxy = gdf_gj.total_bounds
    print(f"   - Emprise totale : Lon [{minx:.4f}, {maxx:.4f}], Lat [{miny:.4f}, {maxy:.4f}]")
    coord_order_ok = (-6.5 <= minx <= -3.5) and (34.5 <= miny <= 36.2)
    print(f"   - Ordre des coordonnées (Lon/Lat WGS84) : {'CONFORME' if coord_order_ok else 'ANOMALIE'}")
    report["coord_order_ok"] = coord_order_ok
    report["bounds"] = [float(minx), float(miny), float(maxx), float(maxy)]

    # 2. Vérification des provinces
    provinces = gdf_gj["province"].value_counts().to_dict()
    print("\n2. Répartition par Province / Préfecture (communes_TTA.geojson) :")
    for prov, cnt in provinces.items():
        print(f"   - {prov:<25} : {cnt} communes")
    report["provinces_breakdown"] = provinces

    # 3. Chargement communes_TTA_2024.csv
    df_csv = pd.read_csv(COMMUNES_CSV)
    print(f"\n3. communes_TTA_2024.csv : {len(df_csv)} lignes")
    report["count_communes_csv"] = len(df_csv)

    # Comparaison des codes HCP
    codes_gj = set(gdf_gj["commune_code"].astype(str).str.strip())
    codes_csv = set(df_csv["commune_code"].astype(str).str.strip())

    diff_gj_csv = codes_gj.symmetric_difference(codes_csv)
    print(f"   - Différence de codes entre GeoJSON et CSV : {len(diff_gj_csv)} (Attendu: 0)")
    report["diff_codes_gj_csv"] = list(diff_gj_csv)

    # Comparaison avec Ministère Santé
    df_ms = pd.read_csv(MINISTERE_BY_COMMUNE)
    print(f"\n4. official_public_health_by_commune_2025.csv : {len(df_ms)} communes")
    codes_ms = set(df_ms["commune_code"].astype(str).str.strip())
    diff_gj_ms = codes_gj.symmetric_difference(codes_ms)
    print(f"   - Différence avec Référentiel Ministère Santé : {len(diff_gj_ms)} (Attendu: 0)")
    report["diff_codes_gj_ms"] = list(diff_gj_ms)

    # Comparaison avec travel_time v2 et Hakima
    df_v2 = pd.read_csv(TRAVEL_TIME_V2)
    df_hakima = pd.read_csv(TRAVEL_TIME_HAKIMA)
    codes_v2 = set(df_v2["commune_code"].astype(str).str.strip())
    codes_hakima = set(df_hakima["commune_code"].astype(str).str.strip())

    print(f"\n5. travel_time_TTA_2024.csv v2 : {len(df_v2)} lignes, codes uniques = {len(codes_v2)}")
    print(f"   travel_time_TTA_2024.csv Hakima : {len(df_hakima)} lignes, codes uniques = {len(codes_hakima)}")
    print(f"   - Différence v2 vs GeoJSON : {len(codes_v2.symmetric_difference(codes_gj))}")
    print(f"   - Différence Hakima vs GeoJSON : {len(codes_hakima.symmetric_difference(codes_gj))}")

    # 4. Calcul de superficie et comparaison avec area_km2 déclaré
    # Reprojection en Lambert Conforme Conique Maroc Zone 1 (EPSG:26191)
    gdf_proj = gdf_gj.to_crs("EPSG:26191")
    calculated_area_km2 = gdf_proj.geometry.area / 1e6
    declared_area_km2 = gdf_gj["area_km2"]

    area_ratio = calculated_area_km2 / declared_area_km2
    print("\n6. Contrôle des superficies (calculées sur EPSG:26191 vs déclarées) :")
    print(f"   - Superficie régionale totale calculée : {calculated_area_km2.sum():.1f} km²")
    print(f"   - Superficie régionale totale déclarée : {declared_area_km2.sum():.1f} km²")
    print(f"   - Écart moyen relatif : {abs(area_ratio - 1.0).mean() * 100:.2f} %")
    report["total_area_calc_km2"] = round(float(calculated_area_km2.sum()), 1)
    report["total_area_decl_km2"] = round(float(declared_area_km2.sum()), 1)

    # 5. Topologie et chevauchements
    print("\n7. Contrôle topologique des chevauchements (intersections de polygones) :")
    overlaps = []
    # Test d'intersection par paire
    sindex = gdf_proj.sindex
    for idx, row in gdf_proj.iterrows():
        possible_matches_index = list(sindex.intersection(row.geometry.bounds))
        possible_matches = gdf_proj.iloc[possible_matches_index]
        for match_idx, match_row in possible_matches.iterrows():
            if idx < match_idx:
                inter = row.geometry.intersection(match_row.geometry)
                if inter.area > 1e4:  # plus de 0.01 km² de chevauchement surfacique
                    overlaps.append({
                        "com1": row["name_fr"],
                        "com2": match_row["name_fr"],
                        "overlap_area_km2": round(inter.area / 1e6, 3)
                    })
    print(f"   - Nombre de chevauchements surfaciques anormaux (> 0.01 km²) : {len(overlaps)}")
    report["overlaps_count"] = len(overlaps)
    report["overlaps"] = overlaps[:5]

    # Sauvegarde du rapport JSON
    out_json = ROOT / "data" / "metadata" / "audit_admin_geography_results.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nRapport d'audit administratif enregistré dans : {out_json}")


if __name__ == "__main__":
    main()
