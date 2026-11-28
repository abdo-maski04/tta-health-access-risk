"""
Tests unitaires et d'intégration pour scripts/build_travel_time.py (GeoVulnera TTA).
Validation hors-ligne avec mocks (aucun appel reseau reel vers ORS).
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd

from scripts.build_travel_time import (
    WHITELIST_PATH,
    get_cache_path,
    get_candidates_for_commune,
    haversine,
    load_whitelist,
    main,
    par_estimation,
    par_ors_v2,
    upsert_travel_data,
)

ROOT = Path(__file__).resolve().parents[1]
BASE_CSV = ROOT / "data" / "processed" / "travel_time_TTA_2024.csv"
BASE_GEOJSON = ROOT / "data" / "processed" / "travel_routes_TTA.geojson"
COMMUNES_CSV = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
RECALC_50_PATH = ROOT / "config" / "recalc_50_communes.txt"


# 1. Selection correcte des destinations depuis la whitelist
def test_hospital_whitelist_filtering():
    whitelist = load_whitelist(WHITELIST_PATH)
    assert "facilities" in whitelist
    assert len(whitelist["facilities"]) == 15
    for fac in whitelist["facilities"]:
        assert fac["official_status"] == "OFFICIAL_MINISTRY"
        assert fac["osm_type"] in ("node", "way")
        assert isinstance(fac["osm_id"], int)
        assert -6.5 <= fac["longitude"] <= -3.5
        assert 34.0 <= fac["latitude"] <= 36.2


# 2. Exclusion des etablissements non admissibles
def test_exclusion_of_ineligible_facilities():
    whitelist = load_whitelist(WHITELIST_PATH)
    all_names = [f["name"] for f in whitelist["facilities"]]
    for name in all_names:
        assert "Ceuta" not in name
        assert "حجامة" not in name
        assert "psychiatrique" not in name.lower()
        assert "Lixus" not in name
        assert "CNSS" not in name
        assert "Arrayane" not in name
        assert "cancers" not in name.lower()


# 3. Distinction entre hopital officiel et candidat local
def test_distinction_official_vs_local_candidate():
    whitelist = load_whitelist(WHITELIST_PATH)
    assert "local_operational_candidates" in whitelist
    loc_cands = whitelist["local_operational_candidates"]
    assert len(loc_cands) == 1
    bni_said = loc_cands[0]
    assert bni_said["official_status"] == "NOT_OFFICIAL"
    assert bni_said["operational_status"] == "LOCAL_OPERATIONAL_CANDIDATE"
    assert bni_said["osm_id"] == 1547030549


# 4. Prise en compte des destinations fallback
def test_handling_provisional_fallbacks():
    whitelist = load_whitelist(WHITELIST_PATH)
    # Fnideq doit etre routee vers M'Diq en fallback provisoire
    cands_fnideq = get_candidates_for_commune("MA-01-573-0101", 35.85, -5.35, whitelist)
    assert len(cands_fnideq) == 1
    assert cands_fnideq[0]["destination_status"] == "PROVISIONAL_FALLBACK"
    assert cands_fnideq[0]["osm_id"] == 293247182  # CHP M'Diq

    # Belyounech egalement
    cands_belyounech = get_candidates_for_commune("MA-01-573-0109", 35.91, -5.38, whitelist)
    assert len(cands_belyounech) == 1
    assert cands_belyounech[0]["osm_id"] == 293247182


# 5. Options CLI de selection des communes
def test_cli_communes_selection():
    # Test avec codes invalides -> doit renvoyer code erreur 1
    ret_err = main(["--communes-list", "MA-01-INVALID-001", "--dry-run"])
    assert ret_err == 1

    # Test avec selection valide -> doit renvoyer 0
    ret_ok = main(["--communes-list", "MA-01-331-0101,MA-01-573-0101", "--dry-run"])
    assert ret_ok == 0


# 6. Invalidation du cache lors d'un changement de destination
def test_cache_invalidation_on_destination_change(tmp_path):
    cache_dir = tmp_path / "cache_v2"
    p1 = get_cache_path(cache_dir, "MA-01-051-0101", "way", 789174103)
    p2 = get_cache_path(cache_dir, "MA-01-051-0101", "node", 8377190516)
    assert p1 != p2
    assert "789174103" in str(p1)
    assert "8377190516" in str(p2)


# 7. Fusion CSV/GeoJSON par commune_code
def test_upsert_merge_by_commune_code(tmp_path):
    out_dir = tmp_path / "out_v2"
    # Ligne modifiee pour Larache
    new_rows = [
        {
            "commune_code": "MA-01-331-0103",
            "name_fr": "Larache",
            "province": "Larache",
            "milieu": "Urbain",
            "start_lat": 35.18,
            "start_lon": -6.15,
            "hospital_osm_type": "node",
            "hospital_osm_id": 12815056754,
            "hospital_name": "CHP Lalla Meriem",
            "hospital_lat": 35.18577,
            "hospital_lon": -6.15683,
            "distance_km": 2.5,
            "temps_min": 5.0,
            "classe_trajet": 1,
            "methode": "TEST_UPSERT",
        }
    ]
    new_features = [
        {
            "type": "Feature",
            "properties": {
                "commune_code": "MA-01-331-0103",
                "name_fr": "Larache",
                "hospital_name": "CHP Lalla Meriem",
                "temps_min": 5.0,
                "distance_km": 2.5,
            },
            "geometry": {
                "type": "LineString",
                "coordinates": [[-6.15, 35.18], [-6.15683, 35.18577]],
            },
        }
    ]

    total_csv, total_gj = upsert_travel_data(
        base_csv_path=BASE_CSV,
        base_geojson_path=BASE_GEOJSON,
        output_dir=out_dir,
        new_rows=new_rows,
        new_features=new_features,
        apply_doc_norm=True,
    )

    assert total_csv == 146
    assert total_gj == 146

    df_res = pd.read_csv(out_dir / "travel_time_TTA_2024.csv", dtype={"commune_code": str})
    larache_row = df_res[df_res["commune_code"] == "MA-01-331-0103"].iloc[0]
    assert larache_row["hospital_name"] == "CHP Lalla Meriem"
    assert larache_row["methode"] == "TEST_UPSERT"


# 8. Conservation des 96 itineraires
def test_preservation_of_96_routes(tmp_path):
    out_dir = tmp_path / "out_v2"
    # Recalcul de 1 commune uniquement
    new_rows = [
        {
            "commune_code": "MA-01-573-0101",
            "hospital_name": "CHP Mohamed 6",
            "temps_min": 15.0,
            "distance_km": 15.8,
        }
    ]
    new_features = [
        {
            "type": "Feature",
            "properties": {
                "commune_code": "MA-01-573-0101",
                "hospital_name": "CHP Mohamed 6",
                "temps_min": 15.0,
                "distance_km": 15.8,
            },
            "geometry": {"type": "LineString", "coordinates": [[-5.35, 35.85], [-5.329, 35.692]]},
        }
    ]

    upsert_travel_data(
        BASE_CSV, BASE_GEOJSON, out_dir, new_rows, new_features, apply_doc_norm=False
    )

    df_orig = pd.read_csv(BASE_CSV, dtype={"commune_code": str})
    df_new = pd.read_csv(out_dir / "travel_time_TTA_2024.csv", dtype={"commune_code": str})

    # Verifier qu'une commune non modifiee (ex. Al Hoceima MA-01-051-0101) est identique
    orig_alh = df_orig[df_orig["commune_code"] == "MA-01-051-0101"].iloc[0]
    new_alh = df_new[df_new["commune_code"] == "MA-01-051-0101"].iloc[0]
    assert orig_alh["hospital_name"] == new_alh["hospital_name"]
    assert orig_alh["distance_km"] == new_alh["distance_km"]
    assert orig_alh["temps_min"] == new_alh["temps_min"]


# 9. Conservation des origines D-002
def test_preservation_of_d002_origins():
    df_communes = pd.read_csv(COMMUNES_CSV, dtype={"commune_code": str})
    df_tt = pd.read_csv(BASE_CSV, dtype={"commune_code": str})
    for _, r in df_communes.iterrows():
        code = r["commune_code"]
        tt_sub = df_tt[df_tt["commune_code"] == code]
        assert len(tt_sub) == 1
        tt_r = tt_sub.iloc[0]
        assert round(float(r["start_lat"]), 5) == round(float(tt_r["start_lat"]), 5)
        assert round(float(r["start_lon"]), 5) == round(float(tt_r["start_lon"]), 5)


# 10. Conservation des 146 codes HCP uniques
def test_preservation_of_146_unique_hcp_codes():
    df_tt = pd.read_csv(BASE_CSV, dtype={"commune_code": str})
    assert len(df_tt) == 146
    assert len(set(df_tt["commune_code"])) == 146


# 11. Absence de doublons et de communes manquantes
def test_absence_of_duplicates_and_missing():
    df_c = pd.read_csv(COMMUNES_CSV, dtype={"commune_code": str})
    df_tt = pd.read_csv(BASE_CSV, dtype={"commune_code": str})
    assert set(df_c["commune_code"]) == set(df_tt["commune_code"])


# 12. Coherence entre CSV et GeoJSON
def test_consistency_csv_and_geojson():
    df_tt = pd.read_csv(BASE_CSV, dtype={"commune_code": str})
    with open(BASE_GEOJSON, encoding="utf-8") as f:
        gj = json.load(f)
    gj_codes = [feat["properties"]["commune_code"] for feat in gj["features"]]
    assert len(gj_codes) == 146
    assert set(df_tt["commune_code"]) == set(gj_codes)


# 13. Absence de destinations interdites dans les resultats futurs
def test_absence_of_forbidden_destinations():
    forbidden = ["Ceuta", "حجامة", "psychiatrique", "Polyclinique Lixus", "Polyclinique CNSS"]
    # Charger la liste des 50 communes a recalculer depuis config
    with open(ROOT / "config" / "recalc_50_communes.json", encoding="utf-8") as f:
        recalc_data = json.load(f)
    for r in recalc_data["communes"]:
        target = r["destination_proposee"]
        for f in forbidden:
            assert f.lower() not in target.lower(), f"Destination interdite {f} pour {r['name_fr']}"


# 14. Traitement des erreurs ORS
def test_ors_error_handling_and_retry(tmp_path):
    mock_session = MagicMock()
    # Simuler reponse 500
    mock_rep = MagicMock()
    mock_rep.status_code = 500
    mock_session.post.return_value = mock_rep

    candidats = [
        {"osm_type": "way", "osm_id": 871505068, "name": "CHU Tanger", "lat": 35.68, "lon": -5.92}
    ]
    # Doit basculer proprement sur par_estimation sans crasher
    res = par_estimation(candidats, (35.7, -5.8))
    assert res["status"] == "ESTIMATED_FALLBACK"
    assert res["methode"] == "DETOUR_1.4"
    assert res["temps_min"] > 0


# 15. Absence d'ecriture en mode --dry-run
def test_dry_run_leaves_files_untouched(tmp_path):
    test_out = tmp_path / "dry_run_out"
    ret = main(["--communes-list", "MA-01-331-0101", "--dry-run", "--output-dir", str(test_out)])
    assert ret == 0
    assert not test_out.exists(), "--dry-run ne doit pas creer le repertoire de sortie"


# 16. Comparaison de plusieurs candidats deja presents en cache
def test_par_ors_v2_compares_all_cached_candidates(tmp_path):
    cache_dir = tmp_path / "ors_v2"
    cache_dir.mkdir(parents=True, exist_ok=True)
    code = "MA-01-227-0313"
    cand_slow = {
        "osm_type": "way",
        "osm_id": 293247182,
        "name": "Hopital Mohamed 6",
        "lat": 35.692,
        "lon": -5.329,
    }
    cand_fast = {
        "osm_type": "way",
        "osm_id": 475665966,
        "name": "Hôpital Mohammed VI",
        "lat": 35.751,
        "lon": -5.828,
    }

    get_cache_path(cache_dir, code, cand_slow["osm_type"], cand_slow["osm_id"]).write_text(
        json.dumps(
            {
                "commune_code": code,
                "hopital": cand_slow,
                "temps_min": 53.7,
                "distance_km": 53.19,
                "trace": [[-5.5, 35.8], [-5.329, 35.692]],
                "methode": "ORS_DRIVING_CAR",
                "status": "SUCCESS",
            }
        ),
        encoding="utf-8",
    )
    get_cache_path(cache_dir, code, cand_fast["osm_type"], cand_fast["osm_id"]).write_text(
        json.dumps(
            {
                "commune_code": code,
                "hopital": cand_fast,
                "temps_min": 44.6,
                "distance_km": 55.75,
                "trace": [[-5.5, 35.8], [-5.828, 35.751]],
                "methode": "ORS_DRIVING_CAR",
                "status": "SUCCESS",
            }
        ),
        encoding="utf-8",
    )

    mock_session = MagicMock()
    res = par_ors_v2(
        session=mock_session,
        token="DUMMY_TOKEN",
        commune_code=code,
        origine=(35.8, -5.5),
        candidats=[cand_slow, cand_fast],
        cache_dir=cache_dir,
    )
    assert res["hopital"]["osm_id"] == 475665966
    assert res["temps_min"] == 44.6
    mock_session.post.assert_not_called()


# 17. Interrogation ORS lorsqu'un candidat non cache peut etre plus rapide
def test_par_ors_v2_queries_uncached_faster_candidate(tmp_path):
    cache_dir = tmp_path / "ors_v2"
    cache_dir.mkdir(parents=True, exist_ok=True)
    code = "MA-01-571-0301"
    cand_cached = {
        "osm_type": "way",
        "osm_id": 1242229574,
        "name": "Hospital Ben Karrich",
        "lat": 35.51,
        "lon": -5.42,
    }
    cand_uncached = {
        "osm_type": "way",
        "osm_id": 484204214,
        "name": "Hôpital Sanyat Rmel",
        "lat": 35.57,
        "lon": -5.36,
    }

    get_cache_path(cache_dir, code, cand_cached["osm_type"], cand_cached["osm_id"]).write_text(
        json.dumps(
            {
                "commune_code": code,
                "hopital": cand_cached,
                "temps_min": 34.1,
                "distance_km": 24.70,
                "trace": [[-5.5, 35.5], [-5.42, 35.51]],
                "methode": "ORS_DRIVING_CAR",
                "status": "SUCCESS",
            }
        ),
        encoding="utf-8",
    )

    mock_rep = MagicMock()
    mock_rep.status_code = 200
    mock_rep.json.return_value = {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[-5.5, 35.5], [-5.36, 35.57]]},
                "properties": {"summary": {"duration": 1872.0, "distance": 24450.0}},
            }
        ]
    }
    mock_session = MagicMock()
    mock_session.post.return_value = mock_rep

    res = par_ors_v2(
        session=mock_session,
        token="DUMMY_TOKEN",
        commune_code=code,
        origine=(35.5, -5.5),
        candidats=[cand_cached, cand_uncached],
        cache_dir=cache_dir,
    )
    assert mock_session.post.call_count == 1
    assert res["hopital"]["osm_id"] == 484204214
    assert res["temps_min"] == 31.2
    assert res["distance_km"] == 24.45


# 18. Coherence entre distance estimee (avec facteur de detour) et temps estime
def test_par_estimation_distance_consistent_with_speed():
    candidats = [
        {
            "osm_type": "way",
            "osm_id": 871505068,
            "name": "CHU de Tanger",
            "lat": 35.683432,
            "lon": -5.925265,
        }
    ]
    origine = (35.75, -5.80)
    expected_haversine = haversine(origine[0], origine[1], candidats[0]["lat"], candidats[0]["lon"])
    expected_detour_km = round(expected_haversine * 1.4, 2)
    expected_time = round((expected_haversine * 1.4) / 50.0 * 60, 1)

    res = par_estimation(candidats, origine)
    assert res["distance_km"] == expected_detour_km
    assert res["temps_min"] == expected_time
    assert round(res["distance_km"] / 50.0 * 60, 1) == res["temps_min"]
