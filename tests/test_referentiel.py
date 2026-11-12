"""
Tests de validation du référentiel territorial des 146 communes (TTA).
Ce module est conçu pour s'exécuter dès que le jeu de données de Hakima est présent.
Si le fichier n'est pas encore fusionné sur la branche courante, les tests sont ignorés (skipped).
"""

import csv
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
GEOJSON_PATH = ROOT / "data" / "processed" / "communes_TTA.geojson"


@pytest.mark.territory
@pytest.mark.skipif(not CSV_PATH.exists(), reason="communes_TTA_2024.csv non présent sur cette branche")
def test_communes_count_and_uniqueness():
    """Vérifie que le CSV contient exactement 146 communes avec des codes uniques."""
    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 146, f"Attendu 146 communes, obtenu {len(rows)}."

    codes = [r["commune_code"] for r in rows]
    assert len(set(codes)) == 146, "Des doublons existent dans commune_code."
    for c in codes:
        assert c.startswith("MA-01-"), f"Code commune invalide : {c} (doit commencer par 'MA-01-')"


@pytest.mark.territory
@pytest.mark.skipif(not CSV_PATH.exists(), reason="communes_TTA_2024.csv non présent sur cette branche")
def test_communes_required_fields_and_types():
    """Vérifie la non-vacuité des colonnes clés et la validité numérique."""
    with CSV_PATH.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            code = row["commune_code"]
            assert row["name_fr"].strip(), f"Nom français manquant pour {code}"
            assert row["province"].strip(), f"Province manquante pour {code}"
            assert row["milieu"] in {"Urbain", "Rural", "Mixte"}, f"Milieu invalide pour {code}"

            pop = int(row["population_2024"])
            assert pop > 0, f"Population <= 0 pour {code}"

            s_lon = float(row["start_lon"])
            s_lat = float(row["start_lat"])
            # Bounding box approximative de la région TTA : Lon [-6.5, -3.5], Lat [34.0, 36.2]
            assert -6.5 <= s_lon <= -3.5, f"start_lon hors région pour {code}: {s_lon}"
            assert 34.0 <= s_lat <= 36.2, f"start_lat hors région pour {code}: {s_lat}"


@pytest.mark.territory
@pytest.mark.skipif(not GEOJSON_PATH.exists(), reason="communes_TTA.geojson non présent sur cette branche")
def test_geojson_concordance_with_csv():
    """Vérifie la concordance entre le GeoJSON et le CSV des communes."""
    with GEOJSON_PATH.open(encoding="utf-8") as f:
        gj = json.load(f)

    features = gj.get("features", [])
    assert len(features) == 146, f"Attendu 146 entités dans le GeoJSON, obtenu {len(features)}."

    geo_codes = {f["properties"]["commune_code"] for f in features}
    assert len(geo_codes) == 146, "Des doublons de code existent dans le GeoJSON."

    if CSV_PATH.exists():
        with CSV_PATH.open(encoding="utf-8") as f:
            csv_codes = {r["commune_code"] for r in csv.DictReader(f)}
        assert geo_codes == csv_codes, "Désaccord entre les codes du CSV et ceux du GeoJSON."
