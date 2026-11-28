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
        "population_2014",
        "population_2024",
        "menages_2014",
        "menages_2024",
        "population_urbaine_2024",
        "population_rurale_2024",
        "osm_relation_id",
        "annee_reference",
    }
    float_fields = {
        "croissance_annuelle_pct",
        "part_60plus_2014_pct",
        "part_rurale_pct",
        "area_km2",
        "densite_hab_km2",
        "centroid_lon",
        "centroid_lat",
        "start_lon",
        "start_lat",
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
        raise ValueError(
            f"Exactement {COMMUNE_COUNT} communes sont attendues; obtenu {len(communes)}"
        )

    commune_codes = [str(row["commune_code"]).strip() for row in communes]
    if len(set(commune_codes)) != COMMUNE_COUNT:
        raise ValueError("Les 146 commune_code doivent être uniques")

    required = {
        "commune_code",
        "name_fr",
        "province",
        "milieu",
        "population_2024",
        "centroid_lon",
        "centroid_lat",
        "start_lon",
        "start_lat",
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

    geo_codes = {str(feature["properties"]["commune_code"]).strip() for feature in features}
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
            (str(row["osm_type"]).strip(), str(row["osm_id"]).strip()) for row in facilities
        ]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Les identifiants OSM des établissements doivent être uniques")

        for row in facilities:
            lat = row["lat"]
            lon = row["lon"]
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError(f"Coordonnées invalides pour l'établissement OSM {row['osm_id']}")


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
        searchable = " ".join(
            (
                str(row.get("name_fr", "")),
                str(row.get("name_ar", "")),
                str(row.get("commune_code", "")),
            )
        ).casefold()
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
        "population_2024",
        "pub_csu",
        "pub_csr",
        "pub_csr2_maternite",
        "pub_dr",
        "pub_primary_total",
        "pub_hospitals",
        "pub_specialized",
        "pub_total_official",
        "osm_pharmacies_mapped",
        "osm_clinics_candidates",
        "osm_doctors_mapped",
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
            row[field] = (
                str(val).strip().lower() in ("true", "1", "yes") if val is not None else False
            )
    return rows


@_cache
def load_health_facilities_master(path: str | Path | None = None) -> list[dict]:
    """Charge le master individuel des établissements de santé du RSC-TTA (1 215 structures)."""
    source = Path(path) if path is not None else HEALTH_FACILITIES_MASTER_CSV
    if not source.is_file():
        raise FileNotFoundError(
            f"Fichier master des infrastructures sanitaires introuvable: {source}"
        )

    with source.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    for row in rows:
        row["facility_id"] = str(row.get("facility_id", "")).strip()
        commune_code_raw = row.get("commune_code")
        row["commune_code"] = (
            str(commune_code_raw).strip()
            if commune_code_raw and str(commune_code_raw).strip()
            else None
        )

        has_gps_raw = str(row.get("has_gps", "")).strip().lower()
        row["has_gps"] = has_gps_raw in ("true", "1", "yes")

        lat_raw = str(row.get("lat", "")).strip()
        lon_raw = str(row.get("lon", "")).strip()
        if (
            row["has_gps"]
            and lat_raw
            and lon_raw
            and lat_raw.lower() not in ("none", "nan", "null")
            and lon_raw.lower() not in ("none", "nan", "null")
        ):
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
                "centroid_lat",
                "centroid_lon",
                "start_lat",
                "start_lon",
                "area_km2",
                "densite_hab_km2",
                "name_ar",
                "population_2014",
                "osm_relation_id",
            ):
                if geo_key in bc and geo_key not in row:
                    row[geo_key] = bc[geo_key]
        enriched_communes.append(row)

    geojson = load_communes_geojson(g_path)
    commune_geojson = join_commune_properties(enriched_communes, geojson)
    master_facilities = load_health_facilities_master(m_path)

    return enriched_communes, commune_geojson, master_facilities


V2_ROUTES_CSV = ROOT / "data" / "processed" / "v2" / "travel_time_TTA_2024.csv"
V2_ROUTES_GEOJSON = ROOT / "data" / "processed" / "v2" / "travel_routes_TTA.geojson"
HOSPITAL_WHITELIST_JSON = ROOT / "config" / "hospital_whitelist.json"
RECALC_50_TXT = ROOT / "config" / "recalc_50_communes.txt"
PROTECTED_96_JSON = ROOT / "config" / "protected_96_communes.json"


@_cache
def load_v2_routes_consolidated():
    """Charge et prépare l'ensemble des données v2 pour la carte des 146 itinéraires.

    Retourne:
        routes_df (pd.DataFrame): 146 lignes enrichies avec coordonnées de tracés et statuts.
        hospitals_df (pd.DataFrame): Hôpitaux uniques de destination avec géolocalisation et statuts.
        communes_geojson (dict): Polygones des 146 communes avec propriétés jointes.
    """
    import geopandas as gpd
    import pandas as pd

    # 1. Charger les sources v2
    df_tt = pd.read_csv(V2_ROUTES_CSV, dtype={"commune_code": str})
    gdf_routes = gpd.read_file(V2_ROUTES_GEOJSON)
    gdf_communes = gpd.read_file(COMMUNES_GEOJSON)

    # 2. Charger les listes de partition et whitelist
    recalc_50 = set()
    if RECALC_50_TXT.exists():
        with RECALC_50_TXT.open("r", encoding="utf-8") as f:
            recalc_50 = {line.strip() for line in f if line.strip() and not line.startswith("#")}

    wl_facilities = {}
    if HOSPITAL_WHITELIST_JSON.exists():
        with HOSPITAL_WHITELIST_JSON.open("r", encoding="utf-8") as f:
            wl_data = json.load(f)
            for fac in wl_data.get("facilities", []):
                wl_facilities[int(fac["osm_id"])] = fac

    # 3. Extraire les coordonnées des géométries routières
    route_paths = {}
    for _, feat in gdf_routes.iterrows():
        code = str(feat["commune_code"])
        coords = [[round(x, 5), round(y, 5)] for x, y in feat.geometry.coords]
        route_paths[code] = coords

    # Dictionnaire des métadonnées communales arabes et surfaciques
    com_meta = {}
    for _, c in gdf_communes.iterrows():
        com_meta[str(c["commune_code"])] = {
            "name_ar": c.get("name_ar", ""),
            "area_km2": c.get("area_km2", 0.0),
        }

    # Charger la population 2024 depuis COMMUNES_CSV
    pop_2024_map = {}
    if COMMUNES_CSV.exists():
        with COMMUNES_CSV.open("r", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                code = str(r.get("commune_code", "")).strip()
                pop_str = r.get("population_2024", "0")
                try:
                    pop_2024_map[code] = int(pop_str) if pop_str else 0
                except ValueError:
                    pop_2024_map[code] = 0

    # 4. Construire le DataFrame enrichi
    records = []
    provisional_codes = {"MA-01-573-0101", "MA-01-573-0109", "MA-01-227-0305"}

    for _, row in df_tt.iterrows():
        code = str(row["commune_code"])
        is_recalc = code in recalc_50
        is_prov = code in provisional_codes

        statut_calc = "Recalculé ORS v2" if is_recalc else "Protégé v1"
        if is_prov:
            statut_dest = "Destination provisoire"
            badge = "⚠️ Provisoire"
            color_rgb = [245, 158, 11, 230]  # Amber/Orange
            color_hex = "#F59E0B"
        elif is_recalc:
            statut_dest = "Hôpital public officiel"
            badge = "🔄 Recalculé v2"
            color_rgb = [16, 185, 129, 230]  # Emerald Green
            color_hex = "#10B981"
        else:
            statut_dest = "Hôpital public officiel"
            badge = "🛡️ Protégé v1"
            color_rgb = [59, 130, 246, 210]  # Royal Blue
            color_hex = "#3B82F6"

        osm_id_int = int(row["hospital_osm_id"]) if pd.notna(row["hospital_osm_id"]) else None
        wl_info = wl_facilities.get(osm_id_int, {})
        canonical_name = wl_info.get(
            "canonical_name", wl_info.get("name", str(row["hospital_name"]))
        )

        records.append(
            {
                "commune_code": code,
                "name_fr": str(row["name_fr"]),
                "name_ar": com_meta.get(code, {}).get("name_ar", ""),
                "province": str(row["province"]),
                "milieu": str(row["milieu"]),
                "start_lat": float(row["start_lat"]),
                "start_lon": float(row["start_lon"]),
                "hospital_osm_type": str(row["hospital_osm_type"]),
                "hospital_osm_id": osm_id_int,
                "hospital_name": str(row["hospital_name"]),
                "hospital_canonical": canonical_name,
                "hospital_lat": float(row["hospital_lat"]),
                "hospital_lon": float(row["hospital_lon"]),
                "distance_km": float(row["distance_km"]),
                "temps_min": float(row["temps_min"]),
                "classe_trajet": int(row["classe_trajet"]),
                "methode": str(row["methode"]),
                "is_recalculated": is_recalc,
                "is_provisional": is_prov,
                "statut_calcul": statut_calc,
                "statut_dest": statut_dest,
                "badge": badge,
                "population_2024": pop_2024_map.get(code, 0),
                "access_tier": (
                    "≤ 30 min (Urgence & Soins Immédiats)"
                    if float(row["temps_min"]) <= 30.0
                    else "30 - 60 min (Délai d'accès modéré)"
                    if float(row["temps_min"]) <= 60.0
                    else "> 60 min (Isolement sanitaire critique)"
                ),
                "color_rgb": color_rgb,
                "color_hex": color_hex,
                "path": route_paths.get(code, []),
            }
        )

    routes_df = pd.DataFrame(records)

    # 5. Préparer les hôpitaux : inclure systématiquement les 15 hôpitaux publics officiels de la whitelist
    # plus les candidats locaux ou établissements réels utilisés comme destinations
    dest_counts = (
        routes_df.groupby("hospital_osm_id")
        .agg(
            communes_count=("commune_code", "count"),
            communes_list=(
                "name_fr",
                lambda s: ", ".join(sorted(s)[:5]) + ("..." if len(s) > 5 else ""),
            ),
        )
        .to_dict(orient="index")
    )

    hosp_records = []
    seen_osm_ids = set()

    # D'abord injecter tous les 15 hôpitaux officiels de la whitelist
    if HOSPITAL_WHITELIST_JSON.exists():
        with HOSPITAL_WHITELIST_JSON.open("r", encoding="utf-8") as f:
            wl_data = json.load(f)
            for fac in wl_data.get("facilities", []):
                osm_id = int(fac["osm_id"])
                seen_osm_ids.add(osm_id)
                cnt_info = dest_counts.get(
                    osm_id, {"communes_count": 0, "communes_list": "Aucune commune rattachée"}
                )
                hosp_records.append(
                    {
                        "osm_id": osm_id,
                        "osm_type": fac["osm_type"],
                        "name": fac.get("canonical_name", fac.get("name")),
                        "lat": float(fac["latitude"]),
                        "lon": float(fac["longitude"]),
                        "communes_count": int(cnt_info["communes_count"]),
                        "communes_list": cnt_info["communes_list"],
                        "is_official": True,
                        "h_type": "Hôpital Public Officiel (Ministère)",
                        "color": [220, 38, 38, 240],  # Rouge vif
                        "radius": 1400,
                    }
                )

    # Ensuite ajouter les autres établissements de destination utilisés (ex: Bni Saïd, Imzouren...)
    for _, row in routes_df.drop_duplicates(subset=["hospital_osm_id"]).iterrows():
        osm_id = row["hospital_osm_id"]
        if pd.isna(osm_id):
            continue
        osm_id = int(osm_id)
        if osm_id not in seen_osm_ids:
            seen_osm_ids.add(osm_id)
            cnt_info = dest_counts.get(osm_id, {"communes_count": 0, "communes_list": ""})
            if osm_id == 1547030549:
                color = [147, 51, 234, 240]  # Violet Bni Said
                h_type = "Candidat Local Opérationnel (Bni Saïd)"
            elif osm_id == 10920276384:
                color = [234, 88, 12, 240]  # Orange Imzouren
                h_type = "Hôpital de Proximité (Imzouren)"
            else:
                color = [79, 70, 229, 240]  # Indigo
                h_type = "Établissement Hospitalier Validé"

            hosp_records.append(
                {
                    "osm_id": osm_id,
                    "osm_type": row["hospital_osm_type"],
                    "name": row["hospital_canonical"],
                    "lat": float(row["hospital_lat"]),
                    "lon": float(row["hospital_lon"]),
                    "communes_count": int(cnt_info["communes_count"]),
                    "communes_list": cnt_info["communes_list"],
                    "is_official": False,
                    "h_type": h_type,
                    "color": color,
                    "radius": 1100,
                }
            )

    hospitals_df = pd.DataFrame(hosp_records)

    # 6. Préparer le GeoJSON des communes avec jointures
    routes_lookup = {r["commune_code"]: r for r in records}
    communes_geojson = json.loads(gdf_communes.to_json())
    for feat in communes_geojson["features"]:
        code = str(feat["properties"].get("commune_code", ""))
        if code in routes_lookup:
            r = routes_lookup[code]
            feat["properties"]["hospital_name"] = r["hospital_canonical"]
            feat["properties"]["temps_min"] = r["temps_min"]
            feat["properties"]["distance_km"] = r["distance_km"]
            feat["properties"]["population_2024"] = r["population_2024"]
            feat["properties"]["access_tier"] = r["access_tier"]
            feat["properties"]["statut_calcul"] = r["statut_calcul"]
            feat["properties"]["badge"] = r["badge"]
            feat["properties"]["is_provisional"] = r["is_provisional"]
            feat["properties"]["is_recalculated"] = r["is_recalculated"]
            # Fill color translucide pour PyDeck GeoJsonLayer
            feat["properties"]["fill_color"] = [
                r["color_rgb"][0],
                r["color_rgb"][1],
                r["color_rgb"][2],
                40,
            ]
            feat["properties"]["line_color"] = [
                r["color_rgb"][0],
                r["color_rgb"][1],
                r["color_rgb"][2],
                160,
            ]

    return routes_df, hospitals_df, communes_geojson
