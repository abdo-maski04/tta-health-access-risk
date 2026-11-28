"""
Tests de validation du jeu de données des établissements de santé (TTA).

Fichier testé : data/processed/health_facilities_TTA.csv (892 lignes × 13 colonnes).
Source : OpenStreetMap, extrait Geofabrik Maroc, licence ODbL.

Ces tests échouent volontairement si le fichier est présent mais incohérent ;
ils sont ignorés (skipped) si le fichier est absent de la branche courante.
"""

import csv
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "health_facilities_TTA.csv"

# BBox de la région TTA élargie de 50 km (marge pour les hôpitaux hors région
# qui peuvent être plus proches qu'un hôpital intra-régional).
LON_MIN, LON_MAX = -6.60, -3.30
LAT_MIN, LAT_MAX = 34.80, 36.10

EXPECTED_COLUMNS = [
    "osm_type",
    "osm_id",
    "name",
    "facility_type",
    "healthcare",
    "lat",
    "lon",
    "operator",
    "opening_hours",
    "phone",
    "addr_city",
    "source",
    "licence",
]

ALLOWED_TYPES = {
    "hospital",
    "clinic",
    "doctors",
    "pharmacy",
    "laboratory",
    "healthcare_unspecified",
    "physiotherapist",
}


def _rows():
    with CSV_PATH.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_columns_match_dictionary():
    """Les 13 colonnes du fichier sont exactement celles du dictionnaire."""
    with CSV_PATH.open(encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == EXPECTED_COLUMNS, f"Colonnes inattendues : {header}"


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_minimum_usable_facilities():
    """Il y a assez d'établissements de soins pour calculer une accessibilité.

    On exclut les pharmacies : elles ne constituent pas un point de recours
    pour une urgence. Seuil volontairement bas, ce test détecte une extraction vide.
    """
    rows = _rows()
    care = [
        r for r in rows if r["facility_type"] in {"hospital", "clinic", "doctors", "laboratory"}
    ]
    assert len(care) >= 50, f"Seulement {len(care)} établissements de soins — extraction suspecte."
    hospitals = [r for r in rows if r["facility_type"] == "hospital"]
    assert len(hospitals) >= 20, f"Seulement {len(hospitals)} hôpitaux — extraction suspecte."


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_coordinates_valid_and_inside_bbox():
    """Chaque point a une latitude/longitude valide et située dans l'emprise TTA + 50 km."""
    for row in _rows():
        lat = float(row["lat"])
        lon = float(row["lon"])
        assert -90 <= lat <= 90, f"latitude invalide : {lat} ({row['osm_id']})"
        assert -180 <= lon <= 180, f"longitude invalide : {lon} ({row['osm_id']})"
        assert LAT_MIN <= lat <= LAT_MAX, f"latitude hors emprise : {lat} ({row['osm_id']})"
        assert LON_MIN <= lon <= LON_MAX, f"longitude hors emprise : {lon} ({row['osm_id']})"


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_identifiers_unique_and_typed():
    """Les identifiants OSM sont uniques et de type node/way."""
    rows = _rows()
    keys = [f"{r['osm_type']}/{r['osm_id']}" for r in rows]
    assert len(set(keys)) == len(keys), "Doublons dans la paire (osm_type, osm_id)."
    for r in rows:
        assert r["osm_type"] in {"node", "way"}, f"osm_type inattendu : {r['osm_type']}"
        assert r["facility_type"] in ALLOWED_TYPES, f"facility_type inconnu : {r['facility_type']}"


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_all_provinces_covered():
    """Chacune des 8 provinces de la région possède au moins un établissement de soins.

    On ne peut pas joindre sur le nom (piège documenté) : on vérifie donc la
    couverture géographique par une bbox par province approximative.
    """
    # Centroïdes approximatifs des 8 provinces / préfectures de la région TTA.
    provinces = {
        "Tanger-Assilah": (-5.80, 35.77),
        "Fahs-Anjra": (-5.60, 35.72),
        "M'diq-Fnideq": (-5.35, 35.80),
        "Tétouan": (-5.37, 35.57),
        "Chefchaouen": (-5.27, 35.17),
        "Larache": (-6.13, 35.18),
        "Ouezzane": (-5.58, 34.80),
        "Al Hoceima": (-3.94, 35.24),
    }
    care = [
        r for r in _rows() if r["facility_type"] in {"hospital", "clinic", "doctors", "laboratory"}
    ]
    missing = []
    for name, (plon, plat) in provinces.items():
        # un établissement de soins à moins de 0.6° (~60 km) du centroïde
        found = any(
            abs(float(r["lon"]) - plon) < 0.6 and abs(float(r["lat"]) - plat) < 0.6 for r in care
        )
        if not found:
            missing.append(name)
    assert not missing, f"Aucun établissement de soins trouvé près de : {missing}"


@pytest.mark.health
@pytest.mark.skipif(
    not CSV_PATH.exists(), reason="health_facilities_TTA.csv non présent sur cette branche"
)
def test_licence_is_odbl():
    """La licence ODbL est mentionnée sur chaque ligne — obligation de citation OSM."""
    for row in _rows():
        assert row["licence"] == "ODbL", f"Licence manquante pour {row['osm_id']}"
        assert "OpenStreetMap" in row["source"], f"Source OSM non citée pour {row['osm_id']}"
