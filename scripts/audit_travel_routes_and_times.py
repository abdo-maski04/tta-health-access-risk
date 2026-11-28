"""Audit scientifique exhaustif des itinéraires routiers et matrices de temps de parcours.
Compare Hakima original vs v2 consolidé, contrôle la géométrie des tracés,
les vitesses moyennes, la cohérence spatiale départ/arrivée et la conformité physique.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
HAKIMA_CSV = ROOT / "data" / "processed" / "travel_time_TTA_2024.csv"
HAKIMA_GEOJSON = ROOT / "data" / "processed" / "travel_routes_TTA.geojson"
V2_CSV = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"
V2_GEOJSON = ROOT / "data" / "processed" / "v2" / "travel_routes_TTA.geojson"
PROTECTED_96_JSON = ROOT / "config" / "protected_96_communes.json"
RECALC_50_TXT = ROOT / "config" / "recalc_50_communes.txt"


def main():
    print("=== AUDIT SCIENTIFIQUE DES ITINÉRAIRES ET DONNÉES ROUTIÈRES ===")
    df_h = pd.read_csv(HAKIMA_CSV)
    gdf_h = gpd.read_file(HAKIMA_GEOJSON)
    df_v2 = pd.read_csv(V2_CSV)
    gdf_v2 = gpd.read_file(V2_GEOJSON)

    print(f"1. Fichiers Hakima originaux : CSV={len(df_h)} lignes, GeoJSON={len(gdf_h)} features")
    print(f"2. Fichiers v2 consolidés    : CSV={len(df_v2)} lignes, GeoJSON={len(gdf_v2)} features")

    with open(RECALC_50_TXT, encoding="utf-8") as f:
        recalc_50_codes = {line.strip() for line in f if line.strip() and not line.startswith("#")}
    print(f"   - Partition validée : 50 recalculés, {146 - len(recalc_50_codes)} protégés")

    # 1. Vérification bit-à-bit des 96 protégés
    prot_h = (
        df_h[~df_h["commune_code"].isin(recalc_50_codes)]
        .sort_values("commune_code")
        .reset_index(drop=True)
    )
    prot_v2 = (
        df_v2[~df_v2["commune_code"].isin(recalc_50_codes)]
        .sort_values("commune_code")
        .reset_index(drop=True)
    )

    print("\n3. Contrôle des 96 communes protégées :")
    print(f"   - Nombre protégé Hakima : {len(prot_h)}, Nombre protégé v2 : {len(prot_v2)}")

    cols_to_check = [
        "commune_code",
        "name_fr",
        "start_lat",
        "start_lon",
        "hospital_osm_id",
        "hospital_name",
        "distance_km",
        "temps_min",
    ]
    diffs = 0
    for col in cols_to_check:
        if not (prot_h[col] == prot_v2[col]).all():
            mismatch = prot_h[prot_h[col] != prot_v2[col]]
            print(f"   [ALERTE] Incohérence sur la colonne {col} pour {len(mismatch)} communes !")
            diffs += 1

    if diffs == 0:
        print("   [CONFORME] Les 96 communes protégées sont strictement identiques bit-à-bit !")

    # 2. Analyse des vitesses moyennes
    df_v2["speed_kmh"] = df_v2["distance_km"] / (df_v2["temps_min"] / 60.0)

    print("\n4. Distribution des vitesses moyennes de déplacement (v2) :")
    print(f"   - Vitesse min : {df_v2['speed_kmh'].min():.1f} km/h")
    print(f"   - Vitesse max : {df_v2['speed_kmh'].max():.1f} km/h")
    print(f"   - Vitesse médiane : {df_v2['speed_kmh'].median():.1f} km/h")
    print(f"   - Vitesse moyenne : {df_v2['speed_kmh'].mean():.1f} km/h")

    # Détection d'anomalies de vitesse
    aberrant_high = df_v2[df_v2["speed_kmh"] > 115.0]
    aberrant_low = df_v2[df_v2["speed_kmh"] < 15.0]
    print(f"   - Vitesses suspectes très élevées (> 115 km/h) : {len(aberrant_high)}")
    if not aberrant_high.empty:
        for _, r in aberrant_high.iterrows():
            print(
                f"     -> {r['commune_code']} ({r['name_fr']}) : {r['speed_kmh']:.1f} km/h (Dist: {r['distance_km']} km, Temps: {r['temps_min']} min)"
            )
    print(f"   - Vitesses suspectes très faibles (< 15 km/h) : {len(aberrant_low)}")
    if not aberrant_low.empty:
        for _, r in aberrant_low.iterrows():
            print(
                f"     -> {r['commune_code']} ({r['name_fr']}) : {r['speed_kmh']:.1f} km/h (Dist: {r['distance_km']} km, Temps: {r['temps_min']} min)"
            )

    # 3. Contrôle de cohérence entre longueur du tracé géométrique et distance_km déclarée
    print(
        "\n5. Contrôle géométrique (longueur calculée de la LineString vs distance_km déclarée) :"
    )
    # Reprojeter les LineStrings en EPSG:26191 (mètres)
    gdf_v2_proj = gdf_v2.to_crs("EPSG:26191")
    gdf_v2["geom_len_km"] = gdf_v2_proj.geometry.length / 1000.0

    merged = df_v2.merge(gdf_v2[["commune_code", "geom_len_km"]], on="commune_code")
    merged["len_ratio"] = merged["geom_len_km"] / merged["distance_km"]

    print(f"   - Ratio moyen Longueur Tracé / Distance déclarée : {merged['len_ratio'].mean():.3f}")
    print(
        f"   - Ratio min : {merged['len_ratio'].min():.3f}, max : {merged['len_ratio'].max():.3f}"
    )
    large_discrepancy = merged[abs(merged["len_ratio"] - 1.0) > 0.05]
    print(f"   - Itinéraires avec écart géométrique > 5% : {len(large_discrepancy)}")
    if not large_discrepancy.empty:
        for _, r in large_discrepancy.head(5).iterrows():
            print(
                f"     -> {r['commune_code']} ({r['name_fr']}) : Geom={r['geom_len_km']:.2f} km vs Déclaré={r['distance_km']:.2f} km (Ratio={r['len_ratio']:.2f})"
            )

    # 4. Contrôle de proximité des extrémités : point de départ vs chef-lieu, point d'arrivée vs hôpital
    print("\n6. Contrôle de proximité spatiale départ/arrivée :")
    endpoint_errors = []
    for _, row in gdf_v2.iterrows():
        code = row["commune_code"]
        coords = list(row.geometry.coords)
        start_pt = coords[0]
        end_pt = coords[-1]

        # Match in df_v2
        m_row = df_v2[df_v2["commune_code"] == code].iloc[0]
        d_start = (
            np.hypot(start_pt[0] - m_row["start_lon"], start_pt[1] - m_row["start_lat"]) * 111.0
        )  # km approx
        d_end = (
            np.hypot(end_pt[0] - m_row["hospital_lon"], end_pt[1] - m_row["hospital_lat"]) * 111.0
        )

        if d_start > 0.5 or d_end > 0.5:
            endpoint_errors.append(
                {
                    "commune_code": code,
                    "name": m_row["name_fr"],
                    "d_start_km": round(d_start, 3),
                    "d_end_km": round(d_end, 3),
                }
            )

    print(f"   - Écarts départ/arrivée > 500m : {len(endpoint_errors)}")
    if endpoint_errors:
        for err in endpoint_errors[:5]:
            print(
                f"     -> {err['commune_code']} ({err['name']}) : écart départ={err['d_start_km']} km, arrivée={err['d_end_km']} km"
            )


if __name__ == "__main__":
    main()
