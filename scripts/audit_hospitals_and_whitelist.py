"""Audit approfondi des hôpitaux et établissements de santé de GeoVulnera TTA.
Vérifie la whitelist des 15 hôpitaux, les identifiants officiels PUB/FINESS,
les catégories hospitalières, Bni Saïd, Imzouren, Fnideq, Belyounech et Anjra.
"""

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
WHITELIST_PATH = ROOT / "config" / "hospital_whitelist.json"
MASTER_PATH = ROOT / "data" / "interim" / "health_facilities_master_TTA.csv"
MATCHING_AUDIT_PATH = ROOT / "data" / "interim" / "health_facility_matching_audit_TTA.csv"
V2_ROUTES_PATH = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"


def main():
    print("=== AUDIT SCIENTIFIQUE DES HÔPITAUX ET STRUCTURES DE SANTÉ ===")

    # 1. Charger la whitelist
    with open(WHITELIST_PATH, encoding="utf-8") as f:
        wl_data = json.load(f)
    facilities = wl_data.get("facilities", [])
    print(f"1. config/hospital_whitelist.json : {len(facilities)} structures répertoriées")

    df_master = pd.read_csv(MASTER_PATH)
    print(f"2. health_facilities_master_TTA.csv : {len(df_master)} structures officielles")

    # Vérification des 15 hôpitaux
    audit_results = []
    for fac in facilities:
        osm_id = int(fac["osm_id"])
        osm_type = fac.get("osm_type", "way")
        canonical_name = fac.get("canonical_name", fac.get("name"))
        cat = fac.get("category", "")
        prov = fac.get("province", "")
        lat = fac.get("latitude")
        lon = fac.get("longitude")

        # Recherche dans le master par nom ou code
        matches = df_master[
            df_master["name"].str.contains(canonical_name[:8], case=False, na=False)
            | df_master["facility_name"].str.contains(canonical_name[:8], case=False, na=False)
            if "facility_name" in df_master.columns
            else df_master["name"].str.contains(canonical_name[:8], case=False, na=False)
        ]

        found_master_id = (
            matches.iloc[0]["facility_id"] if not matches.empty else "NON_TROUVÉ_PAR_NOM"
        )

        audit_results.append(
            {
                "osm_id": osm_id,
                "osm_type": osm_type,
                "name_whitelist": canonical_name,
                "category": cat,
                "province": prov,
                "coords": f"({lat:.5f}, {lon:.5f})",
                "coords_valid": (34.5 <= lat <= 36.2) and (-6.5 <= lon <= -3.5),
                "master_match_count": len(matches),
                "sample_master_id": found_master_id,
            }
        )

    df_audit_wl = pd.DataFrame(audit_results)
    print("\nTableau d'audit des 15 hôpitaux de la Whitelist :")
    for _, r in df_audit_wl.iterrows():
        print(
            f"[{r['category']:<5}] {r['name_whitelist']:<42} | OSM: {r['osm_type']}/{r['osm_id']:<11} | Coords OK: {r['coords_valid']} | Prov: {r['province']}"
        )

    # 2. Cas spécifique : BNI SAÏD
    print("\n--- CAS SPÉCIFIQUE : BNI SAÏD ---")
    bni_said_osm_id = 1547030549
    bni_master = df_master[df_master["name"].str.contains("Bni Sa", case=False, na=False)]
    print(
        f"Structures nommées 'Bni Saïd / Bni Said' dans le registre officiel master ({len(bni_master)}) :"
    )
    for _, r in bni_master.iterrows():
        print(
            f"   - {r['facility_id']} | {r['name']} | Cat: {r['facility_category_label']} | Prov: {r['province']}"
        )

    # Vérifier l'usage de Bni Saïd dans les routes v2
    df_v2 = pd.read_csv(V2_ROUTES_PATH)
    bni_routes = df_v2[df_v2["hospital_osm_id"] == bni_said_osm_id]
    print(
        f"Nombre de communes rattachées à Bni Saïd (way/{bni_said_osm_id}) dans v2 : {len(bni_routes)}"
    )
    if not bni_routes.empty:
        for _, r in bni_routes.iterrows():
            print(
                f"   -> {r['commune_code']} ({r['name_fr']}, {r['province']}) : {r['temps_min']} min, {r['distance_km']} km"
            )

    # 3. Cas spécifique : IMZOUREN
    print("\n--- CAS SPÉCIFIQUE : IMZOUREN ---")
    imz_master = df_master[df_master["name"].str.contains("Imzouren", case=False, na=False)]
    print(f"Structures nommées 'Imzouren' dans le registre officiel master ({len(imz_master)}) :")
    for _, r in imz_master.iterrows():
        print(
            f"   - {r['facility_id']} | {r['name']} | Cat: {r['facility_category_label']} | Tier: {r['facility_tier']}"
        )

    # Vérification des deux identifiants signalés
    id_43 = df_master[df_master["facility_id"] == "PUB-TTA-MA-01-051-043"]
    id_10 = df_master[df_master["facility_id"] == "PUB-TTA-MA-01-051-010"]
    print("\nComparaison des deux identifiants :")
    if not id_43.empty:
        print(
            f"   PUB-TTA-MA-01-051-043 : Nom = {id_43.iloc[0]['name']}, Cat = {id_43.iloc[0]['facility_category_label']}, Tier = {id_43.iloc[0]['facility_tier']}"
        )
    else:
        print("   PUB-TTA-MA-01-051-043 : INTROUVABLE dans master")
    if not id_10.empty:
        print(
            f"   PUB-TTA-MA-01-051-010 : Nom = {id_10.iloc[0]['name']}, Cat = {id_10.iloc[0]['facility_category_label']}, Tier = {id_10.iloc[0]['facility_tier']}"
        )
    else:
        print("   PUB-TTA-MA-01-051-010 : INTROUVABLE dans master")

    # 4. Affectations provisoires : Fnideq, Belyounech, Anjra
    print("\n--- AFFECTATIONS PROVISOIRES / ARBITRAGES ---")
    prov_codes = ["MA-01-573-0101", "MA-01-573-0109", "MA-01-227-0305"]
    df_prov = df_v2[df_v2["commune_code"].isin(prov_codes)]
    for _, r in df_prov.iterrows():
        print(
            f"   - {r['commune_code']} ({r['name_fr']}) -> {r['hospital_name']} (OSM {r['hospital_osm_type']}/{r['hospital_osm_id']}) : {r['temps_min']} min, {r['distance_km']} km"
        )


if __name__ == "__main__":
    main()
