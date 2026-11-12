"""
TTA Health Access Risk — Membre A
Étape 4 : assemblage du jeu de données livrable (dataset final du Membre A).

Fusionne le référentiel territorial et les données démographiques en UNE seule table
propre, au niveau des 146 communes, prête à être utilisée par B (carte) et C (scoring).

Entrées : data/reference/communes_TTA_146.csv
          data/reference/demographics.csv
Sortie  : data/processed/communes_TTA_2024_livrable.csv   (+ .geojson allégé)
          data/processed/README.md
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "data" / "reference" / "communes_TTA_146.csv"
DEMO = ROOT / "data" / "reference" / "demographics.csv"
OUT = ROOT / "data" / "processed"

COLONNES = [
    "commune_code",
    "name_fr",
    "name_ar",
    "province",
    "province_code",
    "start_point_lon",
    "start_point_lat",
    "area_km2",
    "population_2024",
    "population_urbaine_2024",
    "population_rurale_2024",
    "menages_2024",
    "part_rurale_pct",
    "milieu",
    "densite_hab_km2",
    "annee_reference",
    "source",
    "statut_valeur",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    ref = {r["commune_code"]: r for r in csv.DictReader(REF.open(encoding="utf-8"))}
    demo = {r["commune_code"]: r for r in csv.DictReader(DEMO.open(encoding="utf-8"))}

    rows = []
    for code, r in ref.items():
        d = demo[code]
        sup = float(r["area_km2"])
        pop = int(d["population_2024"])
        rows.append(
            {
                "commune_code": code,
                "name_fr": r["name_fr"],
                "name_ar": r["name_ar"],
                "province": r["province"],
                "province_code": r["province_code"],
                "start_point_lon": r["start_point_lon"],
                "start_point_lat": r["start_point_lat"],
                "area_km2": r["area_km2"],
                "population_2024": pop,
                "population_urbaine_2024": int(d["population_urbaine_2024"]),
                "population_rurale_2024": int(d["population_rurale_2024"]),
                "menages_2024": int(d["menages_2024"]),
                "part_rurale_pct": d["part_rurale_pct"],
                "milieu": d["milieu"],
                "densite_hab_km2": round(pop / sup, 1) if sup > 0 else "",
                "annee_reference": 2024,
                "source": "HCP — RGPH 2024 (population légale + douars) ; limites RGPH 2024",
                "statut_valeur": "OFFICIEL",
            }
        )

    rows.sort(key=lambda r: (r["province_code"], r["name_fr"]))

    with (OUT / "communes_TTA_2024_livrable.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLONNES)
        w.writeheader()
        w.writerows(rows)

    # GeoJSON allégé : centroïdes seulement (pas de polygone) -> léger pour l'app
    pts = {
        "type": "FeatureCollection",
        "name": "communes_TTA_2024_points",
        "crs": "EPSG:4326",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(r["start_point_lon"]), float(r["start_point_lat"])]},
                "properties": {
                    k: r[k]
                    for k in ("commune_code", "name_fr", "province", "population_2024", "milieu", "part_rurale_pct")
                },
            }
            for r in rows
        ],
    }
    (OUT / "communes_TTA_2024_points.geojson").write_text(
        json.dumps(pts, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    # --- contrôles finaux sur le livrable ---
    tot = sum(r["population_2024"] for r in rows)
    men = sum(r["menages_2024"] for r in rows)
    codes = [r["commune_code"] for r in rows]
    print(f"Lignes livrées       : {len(rows)}")
    print(f"Population totale    : {tot:,}".replace(",", " "))
    print(f"Ménages totaux       : {men:,}".replace(",", " "))
    print(f"Clé unique           : {len(set(codes)) == len(codes)}")
    print(f"Aucune valeur vide   : {all(all(str(r[c]).strip() for c in COLONNES) for r in rows)}")
    print(f"Population conforme  : {tot == 4_030_222}")
    print(f"Export : {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
