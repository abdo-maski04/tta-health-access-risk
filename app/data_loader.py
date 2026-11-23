"""Chargement et validation des données statiques de la carte TTA."""

from __future__ import annotations

import csv
import json
from collections.abc import Iterable
from pathlib import Path

try:
    import streamlit as st
except ImportError:
    st = None


ROOT = Path(__file__).resolve().parents[1]
COMMUNES_CSV = ROOT / "data" / "processed" / "communes_TTA_2024.csv"
COMMUNES_GEOJSON = ROOT / "data" / "processed" / "communes_TTA.geojson"
FACILITIES_CSV = ROOT / "data" / "processed" / "health_facilities_TTA.csv"
HEALTH_PROFILE_CSV = ROOT / "data" / "interim" / "communes_health_profile_TTA.csv"
HEALTH_FACILITIES_MASTER_CSV = ROOT / "data" / "interim" / "health_facilities_master_TTA.csv"
COMMUNE_COUNT = 146
FACILITY_COUNT = 892
HEALTH_COMMUNES_COUNT = 146
HEALTH_FACILITIES_MASTER_COUNT = 1215


def _cache(func):
    if st is not None and hasattr(st, "cache_data"):
        return st.cache_data(show_spinner=False)(func)
    return func


@_cache
def load_communes(path: str | Path | None = None) -> list[dict]:
    """Charge les communes en conservant les identifiants comme chaînes."""
    source = Path(path) if path is not None else COMMUNES_CSV
    with source.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    integer_fields = {
        "population_2014", "population_2024", "menages_2014", "menages_2024",
        "population_urbaine_2024", "population_rurale_2024",
        "osm_relation_id", "annee_reference",
    }
    float_fields = {
        "croissance_annuelle_pct", "part_60plus_2014_pct", "part_rurale_pct",
        "area_km2", "densite_hab_km2", "centroid_lon", "centroid_lat",
        "start_lon", "start_lat",
    }

    for row in rows:
        row["commune_code"] = str(row["commune_code"]).strip()
        for field in integer_fields:
            row[field] = int(row[field]) if row[field].strip() else None
        for field in float_fields:
            row[field] = float(row[field]) if row[field].strip() else None
    return rows


@_cache
def load_communes_geojson(path: str | Path | None = None) -> dict:
    source = Path(path) if path is not None else COMMUNES_GEOJSON
    with source.open("r", encoding="utf-8") as file:
        geojson = json.load(file)
    if geojson.get("type") != "FeatureCollection":
        raise ValueError("communes_TTA.geojson doit être une FeatureCollection")
    return geojson


@_cache
def load_facilities(path: str | Path | None = None) -> list[dict]:
    source = Path(path) if path is not None else FACILITIES_CSV
    with source.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        row["osm_id"] = str(row["osm_id"]).strip()
        row["lat"] = float(row["lat"])
        row["lon"] = float(row["lon"])
    return rows


def validate_commune_datasets(
    communes: Iterable[dict] | None = None,
    geojson: dict | None = None,
    facilities: Iterable[dict] | None = None,
) -> None:
    """Valide les ensembles requis sans modifier les fichiers source."""
    communes = list(communes if communes is not None else load_communes())
    geojson = geojson if geojson is not None else load_communes_geojson()

    if len(communes) != COMMUNE_COUNT:
        raise ValueError(f"Exactement {COMMUNE_COUNT} communes sont attendues; obtenu {len(communes)}")

    commune_codes = [str(row["commune_code"]).strip() for row in communes]
    if len(set(commune_codes)) != COMMUNE_COUNT:
        raise ValueError("Les 146 commune_code doivent être uniques")

    required = {
        "commune_code", "name_fr", "province", "milieu", "population_2024",
        "centroid_lon", "centroid_lat", "start_lon", "start_lat",
    }
    for row in communes:
        missing = required - set(row)
        empty = [field for field in required if row.get(field) in (None, "")]
        if missing or empty:
            raise ValueError(
                f"Données communales invalides pour {row.get('commune_code', 'code inconnu')}: "
                f"champs absents={sorted(missing)}, champs vides={sorted(empty)}"
            )

    features = geojson.get("features", [])
    if len(features) != COMMUNE_COUNT:
        raise ValueError(
            f"Exactement {COMMUNE_COUNT} entités GeoJSON sont attendues; obtenu {len(features)}"
        )

    geo_codes = {
        str(feature["properties"]["commune_code"]).strip()
        for feature in features
    }
    if len(geo_codes) != COMMUNE_COUNT:
        raise ValueError("Les commune_code du GeoJSON doivent être uniques")
    if set(commune_codes) != geo_codes:
        raise ValueError("Les codes communaux du CSV et du GeoJSON ne correspondent pas")

    for feature in features:
        geometry = feature.get("geometry") or {}
        if geometry.get("type") not in {"Polygon", "MultiPolygon"}:
            raise ValueError(f"Géométrie communale invalide: {geometry.get('type')}")

    if facilities is not None:
        facilities = list(facilities)
        if len(facilities) != FACILITY_COUNT:
            raise ValueError(
                f"Exactement {FACILITY_COUNT} établissements sont attendus; obtenu {len(facilities)}"
            )
        identifiers = [
            (str(row["osm_type"]).strip(), str(row["osm_id"]).strip())
            for row in facilities
        ]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Les identifiants OSM des établissements doivent être uniques")

        for row in facilities:
            lat = row["lat"]
            lon = row["lon"]
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError(
                    f"Coordonnées invalides pour l'établissement OSM {row['osm_id']}"
                )


def join_commune_properties(communes: Iterable[dict], geojson: dict) -> dict:
    """Joint les propriétés communales dans une copie indépendante du GeoJSON."""
    commune_rows = {str(row["commune_code"]).strip(): row for row in communes}
    enriched = json.loads(json.dumps(geojson))

    for feature in enriched["features"]:
        code = str(feature["properties"]["commune_code"]).strip()
        if code not in commune_rows:
            raise ValueError(f"Aucune propriété communale pour {code}")
        feature["properties"].update(commune_rows[code])
    return enriched


def filter_communes(
    communes: Iterable[dict],
    provinces: Iterable[str] | None = None,
    milieux: Iterable[str] | None = None,
    search: str = "",
) -> list[dict]:
    province_set = set(provinces or [])
    milieu_set = set(milieux or [])
    needle = search.strip().casefold()
    result = []
    for row in communes:
        if province_set and row["province"] not in province_set:
            continue
        if milieu_set and row["milieu"] not in milieu_set:
            continue
        searchable = " ".join((
            str(row.get("name_fr", "")),
            str(row.get("name_ar", "")),
            str(row.get("commune_code", "")),
        )).casefold()
        if needle and needle not in searchable:
            continue
        result.append(row)
    return result


def filter_facilities(
    facilities: Iterable[dict],
    facility_types: Iterable[str] | None = None,
) -> list[dict]:
    type_set = set(facility_types or [])
    if not type_set:
        return list(facilities)
    return [row for row in facilities if row["facility_type"] in type_set]


def assign_facility_communes(facilities: Iterable[dict], geojson: dict) -> list[dict]:
    """Attribue une commune à chaque point contenu dans un polygone TTA."""
    geometries = [
        (
            str(feature["properties"]["commune_code"]).strip(),
            feature["geometry"],
        )
        for feature in geojson["features"]
    ]
    assigned = []
    for facility in facilities:
        row = dict(facility)
        row["commune_code"] = None
        for code, geometry in geometries:
            if _point_in_geometry(row["lon"], row["lat"], geometry):
                row["commune_code"] = code
                break
        assigned.append(row)
    return assigned


def _point_in_ring(lon: float, lat: float, ring: Iterable[Iterable[float]]) -> bool:
    inside = False
    points = list(ring)
    if len(points) < 3:
        return False
    for index in range(len(points)):
        x1, y1 = points[index]
        x2, y2 = points[(index + 1) % len(points)]
        if (y1 > lat) != (y2 > lat):
            crossing_x = x1 + (lat - y1) * (x2 - x1) / (y2 - y1)
            if lon < crossing_x:
                inside = not inside
    return inside


def _point_in_geometry(lon: float, lat: float, geometry: dict) -> bool:
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        return False

    for polygon in polygons:
        if not polygon:
            continue
        if _point_in_ring(lon, lat, polygon[0]):
            in_hole = any(_point_in_ring(lon, lat, hole) for hole in polygon[1:])
            if not in_hole:
                return True
    return False


def _file_signature(path: Path) -> tuple[str, float, int]:
    """Retourne la signature (nom, mtime, taille) pour invalider le cache si le fichier change."""
    try:
        stat = path.stat()
        return (path.name, stat.st_mtime, stat.st_size)
    except OSError:
        return (path.name, 0.0, 0)


@_cache
def get_prepared_data(
    communes_path: str | Path | None = None,
    geojson_path: str | Path | None = None,
    facilities_path: str | Path | None = None,
    _cache_token: tuple | None = None,
) -> tuple[list[dict], dict, list[dict]]:
    """Charge, valide et associe les données spatiales de manière centralisée et mise en cache."""
    c_path = Path(communes_path) if communes_path is not None else COMMUNES_CSV
    g_path = Path(geojson_path) if geojson_path is not None else COMMUNES_GEOJSON
    f_path = Path(facilities_path) if facilities_path is not None else FACILITIES_CSV

    if _cache_token is None:
        _cache_token = (
            _file_signature(c_path),
            _file_signature(g_path),
            _file_signature(f_path),
        )

    communes = load_communes(c_path)
    geojson = load_communes_geojson(g_path)
    facilities = load_facilities(f_path)
    validate_commune_datasets(communes, geojson, facilities)
    commune_geojson = join_commune_properties(communes, geojson)
    assigned_facilities = assign_facility_communes(facilities, commune_geojson)
    return communes, commune_geojson, assigned_facilities


@_cache
def load_communes_health_profile(path: str | Path | None = None) -> list[dict]:
    """Charge le profil sanitaire communal consolidé (146 communes) du RSC-TTA."""
    source = Path(path) if path is not None else HEALTH_PROFILE_CSV
    if not source.is_file():
        raise FileNotFoundError(f"Fichier de profil sanitaire introuvable: {source}")

    with source.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    integer_fields = {
        "population_2024", "pub_csu", "pub_csr", "pub_csr2_maternite", "pub_dr",
        "pub_primary_total", "pub_hospitals", "pub_specialized", "pub_total_official",
        "osm_pharmacies_mapped", "osm_clinics_candidates", "osm_doctors_mapped",
        "osm_health_points_total",
    }
    float_fields = {"part_rurale_pct", "primary_care_per_10k", "pharmacy_per_10k"}
    bool_fields = {"is_public_healthcare_absent"}

    for row in rows:
        row["commune_code"] = str(row["commune_code"]).strip()
        for field in integer_fields:
            val = row.get(field)
            row[field] = int(val.strip()) if val is not None and val.strip() else 0
        for field in float_fields:
            val = row.get(field)
            row[field] = float(val.strip()) if val is not None and val.strip() else 0.0
        for field in bool_fields:
            val = row.get(field)
            row[field] = str(val).strip().lower() in ("true", "1", "yes") if val is not None else False
    return rows


@_cache
def load_health_facilities_master(path: str | Path | None = None) -> list[dict]:
    """Charge le master individuel des établissements de santé du RSC-TTA (1 215 structures)."""
    source = Path(path) if path is not None else HEALTH_FACILITIES_MASTER_CSV
    if not source.is_file():
        raise FileNotFoundError(f"Fichier master des infrastructures sanitaires introuvable: {source}")

    with source.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        row["facility_id"] = str(row.get("facility_id", "")).strip()
        commune_code_raw = row.get("commune_code")
        row["commune_code"] = str(commune_code_raw).strip() if commune_code_raw and str(commune_code_raw).strip() else None

        has_gps_raw = str(row.get("has_gps", "")).strip().lower()
        row["has_gps"] = has_gps_raw in ("true", "1", "yes")

        lat_raw = str(row.get("lat", "")).strip()
        lon_raw = str(row.get("lon", "")).strip()
        if row["has_gps"] and lat_raw and lon_raw and lat_raw.lower() not in ("none", "nan", "null") and lon_raw.lower() not in ("none", "nan", "null"):
            try:
                row["lat"] = float(lat_raw)
                row["lon"] = float(lon_raw)
            except ValueError:
                row["lat"] = None
                row["lon"] = None
                row["has_gps"] = False
        else:
            row["lat"] = None
            row["lon"] = None
            row["has_gps"] = False

        if row.get("source_year") and str(row["source_year"]).strip().isdigit():
            row["source_year"] = int(str(row["source_year"]).strip())
        else:
            row["source_year"] = None
    return rows


@_cache
def get_sanitary_prepared_data(
    profile_path: str | Path | None = None,
    geojson_path: str | Path | None = None,
    master_path: str | Path | None = None,
    _cache_token: tuple | None = None,
) -> tuple[list[dict], dict, list[dict]]:
    """Charge et consolide les données sanitaires RSC-TTA pour les cartes et analyses.

    Retourne:
        - communes_enriched: liste de 146 communes avec profil sanitaire, démographique et géométrie.
        - commune_geojson: FeatureCollection enrichie avec les données de profil sanitaire.
        - facilities_master: liste de 1 215 structures individuelles avec typologie et statut de validation.
    """
    p_path = Path(profile_path) if profile_path is not None else HEALTH_PROFILE_CSV
    g_path = Path(geojson_path) if geojson_path is not None else COMMUNES_GEOJSON
    m_path = Path(master_path) if master_path is not None else HEALTH_FACILITIES_MASTER_CSV

    if _cache_token is None:
        _cache_token = (
            _file_signature(p_path),
            _file_signature(g_path),
            _file_signature(m_path),
        )

    health_profiles = load_communes_health_profile(p_path)
    base_communes = {row["commune_code"]: row for row in load_communes()}

    enriched_communes = []
    for hp in health_profiles:
        code = hp["commune_code"]
        row = dict(hp)
        if code in base_communes:
            bc = base_communes[code]
            for geo_key in (
                "centroid_lat", "centroid_lon", "start_lat", "start_lon",
                "area_km2", "densite_hab_km2", "name_ar", "population_2014",
                "osm_relation_id",
            ):
                if geo_key in bc and geo_key not in row:
                    row[geo_key] = bc[geo_key]
        enriched_communes.append(row)

    geojson = load_communes_geojson(g_path)
    commune_geojson = join_commune_properties(enriched_communes, geojson)
    master_facilities = load_health_facilities_master(m_path)

    return enriched_communes, commune_geojson, master_facilities


