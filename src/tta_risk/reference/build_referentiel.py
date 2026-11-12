"""
TTA Health Access Risk — Membre A
Étape 1 : construction du référentiel territorial communal (région TTA).

Entrée  : data/raw_downloads/communes_rgph2024_MAR.geojson  (source nationale, non modifiée)
Sorties : data/reference/communes_TTA.geojson      150 entités = géométries de référence (la plus fine)
          data/reference/communes_TTA.csv          150 lignes
          data/reference/communes_TTA_146.csv     146 lignes = niveau communal officiel HCP
          data/reference/population_TEMPLATE.csv   squelette à remplir depuis le HCP
          data/reference/qc_referentiel.json      rapport de contrôle qualité

Règles du projet appliquées :
- commune_code est la clé, en TEXTE (zéros initiaux conservés).
- Coordonnées WGS84 / EPSG:4326, ordre (longitude, latitude).
- Aucune valeur inventée : ce qui manque reste vide et est signalé.
- Toute transformation est codée et journalisée (pas d'édition manuelle du fichier).
"""

from __future__ import annotations

import csv
import json
import math
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw_downloads" / "communes_rgph2024_MAR.geojson"
OUT_DIR = ROOT / "data" / "reference"

REGION_CODE = "MA-01"
REGION_NAME = "Tanger-Tétouan-Al Hoceima"

# Code province/préfecture -> nom officiel (découpage 2015) et nombre de communes attendu (HCP)
PROVINCES = {
    "MA-01-051": ("Al Hoceima", 36),
    "MA-01-151": ("Chefchaouen", 28),
    "MA-01-227": ("Fahs-Anjra", 7),
    "MA-01-331": ("Larache", 19),
    "MA-01-405": ("Ouezzane", 17),
    "MA-01-511": ("Tanger-Assilah", 12),
    "MA-01-571": ("Tétouan", 22),
    "MA-01-573": ("M'diq-Fnideq", 5),
}

# Nombre officiel de communes de la région (HCP, découpage 2015) : 2 préfectures + 6 provinces
EXPECTED_COMMUNES = 146

# --- Écarts connus entre le fichier de géométries et le niveau communal officiel HCP ---
# 1) Ceuta : polygone présent dans le jeu national, hors souveraineté marocaine -> exclu du périmètre.
HORS_PERIMETRE = {"MA-01-573-0100": "Sebta (Ceuta) — territoire hors souveraineté marocaine, exclu du périmètre"}
# 2) Tanger : le HCP dénombre la commune de Tanger (4 arrondissements agrégés) comme 1 commune.
#    Le fichier de géométries livre les 4 arrondissements séparément -> agrégés sous une clé unique.
# Commune de Tanger : code officiel HCP '01.511.01.0' -> MA-01-511-0100 (série 0 = commune entière).
# ATTENTION : dans le fichier de géométries, MA-01-511-0103 est l'ARRONDISSEMENT de Bni Makada,
# pas la commune de Tanger. Ne pas confondre.
TANGER_CODE = "MA-01-511-0100"
AGREGATION_HCP = {
    "MA-01-511-0103": TANGER_CODE,
    "MA-01-511-0105": TANGER_CODE,
    "MA-01-511-0106": TANGER_CODE,
    "MA-01-511-0107": TANGER_CODE,
}

R_EARTH = 6371008.8  # m


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm_name(s: str) -> str:
    s = strip_accents(s).lower()
    for a, b in (("-", " "), ("'", " "), ("  ", " ")):
        s = s.replace(a, b)
    return " ".join(s.split())


def area_km2(geom) -> float:
    """Aire approchée en km² par projection équirectangulaire locale (erreur < 0,5 %)."""
    lat0 = math.radians(geom.centroid.y)
    xs, ys = [], []
    polys = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
    for poly in polys:
        ext = list(poly.exterior.coords)
        xs += [math.radians(x) * R_EARTH * math.cos(lat0) for x, _ in ext]
        ys += [math.radians(y) * R_EARTH for _, y in ext]
    # shoelace
    a = 0.0
    n = len(xs)
    for i in range(n - 1):
        a += xs[i] * ys[i + 1] - xs[i + 1] * ys[i]
    return abs(a) / 2 / 1e6


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = json.loads(RAW.read_text(encoding="utf-8"))
    features = [f for f in raw["features"] if str(f["properties"].get("code", "")).startswith(REGION_CODE)]

    rows: list[dict] = []
    problems: list[dict] = []
    excluded: list[dict] = []

    for f in features:
        props = f.get("properties", {})
        code = str(props.get("code", "")).strip()
        name_fr = (props.get("name_fr") or "").strip()
        name_ar = (props.get("name_ar") or "").strip()
        geom_obj = f.get("geometry")

        if not code:
            problems.append({"commune_code": None, "type": "code_manquant", "detail": name_fr})
            continue
        if not geom_obj:
            problems.append({"commune_code": code, "type": "geometrie_absente", "detail": name_fr})
            continue

        if code in HORS_PERIMETRE:
            excluded.append({"commune_code": code, "name_fr": name_fr, "raison": HORS_PERIMETRE[code]})
            continue

        geom = shape(geom_obj)
        valid = geom.is_valid
        if not valid:
            problems.append({"commune_code": code, "type": "geometrie_invalide", "detail": name_fr})
        geom = geom.buffer(0) if not valid else geom

        # Point de départ provisoire = point représentatif intérieur au polygone.
        # Décision à figer en équipe : centroïde vs centre habité (cf. docs/decisions.md).
        pt = geom.representative_point()

        prov_code = code[:9]
        prov_name, _ = PROVINCES.get(prov_code, ("INCONNUE", None))

        rows.append(
            {
                "commune_code": code,
                "commune_code_hcp": AGREGATION_HCP.get(code, code),
                "est_arrondissement": code in AGREGATION_HCP,
                "province_code": prov_code,
                "province": prov_name,
                "name_fr": name_fr,
                "name_ar": name_ar,
                "name_norm": norm_name(name_fr),
                "start_point_lon": round(pt.x, 6),
                "start_point_lat": round(pt.y, 6),
                "centroid_lon": round(geom.centroid.x, 6),
                "centroid_lat": round(geom.centroid.y, 6),
                "area_km2": round(area_km2(geom), 2),
                "geom_type": geom_obj.get("type"),
                "geometry": geom_obj,
                "source": "RGPH 2024 — limites communales (rgphapps.ma via Morocco-Geospatial-Visualisations)",
                "source_retrieved": datetime.now(UTC).strftime("%Y-%m-%d"),
            }
        )

    rows.sort(key=lambda r: (r["province_code"], r["name_norm"]))

    # ---- Contrôles qualité -------------------------------------------------
    codes = [r["commune_code"] for r in rows]
    hcp_codes = [r["commune_code_hcp"] for r in rows]
    dup = sorted({c for c in codes if codes.count(c) > 1})
    missing_names = [r["commune_code"] for r in rows if not r["name_fr"]]
    unknown_prov = sorted({r["province"] for r in rows if r["province"] == "INCONNUE"})
    out_of_extent = [
        r["commune_code"]
        for r in rows
        if not (34.4 <= r["start_point_lat"] <= 36.0 and -6.4 <= r["start_point_lon"] <= -3.6)
    ]

    per_prov, expected_prov = {}, {}
    for r in rows:
        per_prov[r["province"]] = per_prov.get(r["province"], 0) + 1
    for prov_code, (prov_name, expected) in PROVINCES.items():
        got_hcp = len({r["commune_code_hcp"] for r in rows if r["province_code"] == prov_code})
        expected_prov[prov_name] = {"hcp_attendu": expected, "geometries": per_prov.get(prov_name, 0), "niveau_hcp": got_hcp}

    total_area = round(sum(r["area_km2"] for r in rows), 1)
    n_hcp = len(set(hcp_codes))

    qc = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "region": REGION_NAME,
        "source_file": str(RAW.relative_to(ROOT)),
        "niveau_geometries": len(rows),
        "niveau_communal_hcp": n_hcp,
        "communes_expected_hcp": EXPECTED_COMMUNES,
        "ecart_vs_hcp": n_hcp - EXPECTED_COMMUNES,
        "exclusions": excluded,
        "agregations": {
            TANGER_CODE: sorted([c for c, v in AGREGATION_HCP.items() if v == TANGER_CODE]),
        },
        "par_province": expected_prov,
        "surface_totale_km2": total_area,
        "surface_reference_km2": "≈ 15 000 – 16 000 (monographies HCP région TTA) — écart à commenter",
        "duplicates": dup,
        "missing_name_fr": missing_names,
        "unknown_province_codes": unknown_prov,
        "points_hors_emprise_region": out_of_extent,
        "problems": problems,
        "checks": {
            "cle_unique_geometries": len(dup) == 0,
            "cle_unique_niveau_hcp": len(set(hcp_codes)) == n_hcp,  # unicité des 146 clés après agrégation
            "noms_presents": len(missing_names) == 0,
            "provinces_reconnues": len(unknown_prov) == 0,
            "coordonnees_dans_emprise": len(out_of_extent) == 0,
            "nombre_conforme_hcp": n_hcp == EXPECTED_COMMUNES,
        },
    }

    # ---- Écriture des géométries ------------------------------------------
    geojson = {
        "type": "FeatureCollection",
        "name": f"communes_{REGION_CODE}_referentiel",
        "crs": "EPSG:4326",
        "generated_at": qc["generated_at"],
        "features": [
            {
                "type": "Feature",
                "geometry": r["geometry"],
                "properties": {k: v for k, v in r.items() if k != "geometry"},
            }
            for r in rows
        ],
    }
    (OUT_DIR / "communes_TTA.geojson").write_text(
        json.dumps(geojson, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    cols = [
        "commune_code", "commune_code_hcp", "est_arrondissement", "province_code", "province",
        "name_fr", "name_ar", "name_norm", "start_point_lon", "start_point_lat",
        "centroid_lon", "centroid_lat", "area_km2", "geom_type", "source", "source_retrieved",
    ]
    with (OUT_DIR / "communes_TTA.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in cols})

    # ---- Vue agrégée au niveau communal officiel (146) ---------------------
    agg: dict[str, dict] = {}
    for r in rows:
        k = r["commune_code_hcp"]
        if k not in agg:
            agg[k] = {
                "commune_code": k,
                "province_code": r["province_code"],
                "province": r["province"],
                "name_fr": "Tanger" if k == TANGER_CODE else r["name_fr"],
                "name_ar": "طنجة" if k == TANGER_CODE else r["name_ar"],
                "name_norm": "tanger" if k == TANGER_CODE else r["name_norm"],
                "start_point_lon": r["start_point_lon"],
                "start_point_lat": r["start_point_lat"],
                "area_km2": 0.0,
                "nb_entites_geometriques": 0,
                "codes_geometries": [],
            }
        agg[k]["area_km2"] = round(agg[k]["area_km2"] + r["area_km2"], 2)
        agg[k]["nb_entites_geometriques"] += 1
        agg[k]["codes_geometries"].append(r["commune_code"])

    agg_rows = sorted(agg.values(), key=lambda r: (r["province_code"], r["name_norm"]))
    cols2 = [
        "commune_code", "province_code", "province", "name_fr", "name_ar", "name_norm",
        "start_point_lon", "start_point_lat", "area_km2", "nb_entites_geometriques", "codes_geometries",
    ]
    with (OUT_DIR / "communes_TTA_146.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols2)
        w.writeheader()
        for r in agg_rows:
            row = dict(r)
            row["codes_geometries"] = "|".join(r["codes_geometries"])
            w.writerow(row)

    # ---- Squelette de jointure démographique (à remplir depuis le HCP) -----
    with (OUT_DIR / "population_TEMPLATE.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow([
            "commune_code", "name_fr", "province",
            "population_2024", "population_2014", "menages_2024",
            "milieu", "annee_reference", "source", "statut_valeur",
        ])
        for r in agg_rows:
            w.writerow([r["commune_code"], r["name_fr"], r["province"], "", "", "", "", "2024", "HCP RGPH 2024", "A_REMPLIR"])

    (OUT_DIR / "qc_referentiel.json").write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(qc["checks"], ensure_ascii=False, indent=2))
    print(f"\nGéométries : {len(rows)}   |   Niveau officiel HCP : {n_hcp} (attendu {EXPECTED_COMMUNES}, écart {qc['ecart_vs_hcp']:+d})")
    print(f"Surface totale : {total_area} km²")
    print(f"Exclus : {[(e['commune_code'], e['name_fr']) for e in excluded]}")
    print("\nPar province (HCP / géométries) :")
    for p, d in expected_prov.items():
        flag = "OK " if d["niveau_hcp"] == d["hcp_attendu"] else "ECART"
        print(f"  {flag} {p:16s} HCP={d['hcp_attendu']:3d}  niveau_hcp={d['niveau_hcp']:3d}  geometries={d['geometries']:3d}")


if __name__ == "__main__":
    main()
