"""
Script de construction du Référentiel Sanitaire Consolidé (RSC-TTA) — Version Finalisée
Génère de manière déterministe, traçable et reproductible depuis le dépôt :
1. data/interim/communes_health_profile_TTA.csv
2. data/interim/health_facilities_master_TTA.csv
3. data/interim/health_facility_matching_audit_TTA.csv
"""

import csv
import json
import os
from collections import defaultdict
from difflib import SequenceMatcher

# 1. Chemins des sources (relativement à la racine du dépôt)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMMUNES_CSV = os.path.join(BASE_DIR, "data", "processed", "communes_TTA_2024.csv")
COMMUNES_GEOJSON = os.path.join(BASE_DIR, "data", "processed", "communes_TTA.geojson")
OSM_FACILITIES_CSV = os.path.join(BASE_DIR, "data", "processed", "health_facilities_TTA.csv")

# Emplacement pérennisé des sources ministérielles dans le dépôt
DIR_MINISTERE = os.path.join(BASE_DIR, "data", "raw", "ministere_sante")
FILE_NATIONAL_PRIVATE = os.path.join(DIR_MINISTERE, "private_infrastructures_national_2025.csv")
FILE_COMMUNES_PUBLIC = os.path.join(DIR_MINISTERE, "official_public_health_by_commune_2025.csv")
FILE_FACILITIES_PUBLIC = os.path.join(DIR_MINISTERE, "official_public_health_tta_2025.csv")

# Contrôle strict de l'existence des fichiers d'entrée
for required_path in [
    COMMUNES_CSV,
    COMMUNES_GEOJSON,
    OSM_FACILITIES_CSV,
    FILE_COMMUNES_PUBLIC,
    FILE_FACILITIES_PUBLIC,
]:
    if not os.path.exists(required_path):
        raise FileNotFoundError(
            f"[ERREUR CRITIQUE] Fichier source indispensable manquant : {required_path}"
        )

# Chemins des sorties
OUT_DIR = os.path.join(BASE_DIR, "data", "interim")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_COMMUNES_PROFILE = os.path.join(OUT_DIR, "communes_health_profile_TTA.csv")
OUT_FACILITIES_MASTER = os.path.join(OUT_DIR, "health_facilities_master_TTA.csv")
OUT_MATCHING_AUDIT = os.path.join(OUT_DIR, "health_facility_matching_audit_TTA.csv")

# 2. Dictionnaire des 4 alias de communes officiellement documentés
COMMUNE_ALIASES = {
    "bni abdallah": "Bni Abdellah",
    "bou jedyane": "Boujedyane",
    "moqrisset": "Moqrissat",
    "ounnana": "Ouannana",
}


def normalize_commune_name(raw_name: str) -> str:
    cleaned = raw_name.strip().lower()
    return COMMUNE_ALIASES.get(cleaned, raw_name.strip())


# 3. Chargement des référentiels communaux et géométries
print("[1/6] Chargement des communes et géométries...")
with open(COMMUNES_CSV, encoding="utf-8") as f:
    communes_raw = list(csv.DictReader(f))

communes_by_code = {c["commune_code"]: c for c in communes_raw}
communes_by_name = {c["name_fr"].strip().lower(): c for c in communes_raw}

with open(COMMUNES_GEOJSON, encoding="utf-8") as f:
    geojson_data = json.load(f)

# Index spatial optimisé avec Bounding Box
geometries = []
for feature in geojson_data["features"]:
    code = feature["properties"]["commune_code"]
    geom = feature["geometry"]
    all_coords = []
    if geom["type"] == "Polygon":
        all_coords = [pt for ring in geom["coordinates"] for pt in ring]
    elif geom["type"] == "MultiPolygon":
        all_coords = [pt for poly in geom["coordinates"] for ring in poly for pt in ring]
    min_x = min(pt[0] for pt in all_coords)
    max_x = max(pt[0] for pt in all_coords)
    min_y = min(pt[1] for pt in all_coords)
    max_y = max(pt[1] for pt in all_coords)
    geometries.append((code, geom, (min_x, min_y, max_x, max_y)))


def _point_in_ring(lon, lat, ring):
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


def _point_in_geometry(lon, lat, geom, bbox):
    min_x, min_y, max_x, max_y = bbox
    if not (min_x <= lon <= max_x and min_y <= lat <= max_y):
        return False
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        return False
    for poly in polys:
        if not poly:
            continue
        if _point_in_ring(lon, lat, poly[0]):
            in_hole = any(_point_in_ring(lon, lat, hole) for hole in poly[1:])
            if not in_hole:
                return True
    return False


# 4. Chargement des données sanitaires
print("[2/6] Chargement des sources sanitaires...")
with open(FILE_COMMUNES_PUBLIC, encoding="utf-8") as f:
    pub_communes_raw = list(csv.DictReader(f))

with open(FILE_FACILITIES_PUBLIC, encoding="utf-8") as f:
    pub_facilities_raw = list(csv.DictReader(f))

with open(OSM_FACILITIES_CSV, encoding="utf-8") as f:
    osm_facilities_raw = list(csv.DictReader(f))

# Attribution spatiale stricte des établissements OSM aux communes
print("[3/6] Jointure spatiale des points OSM sur les 146 polygones communaux...")
osm_by_commune = defaultdict(list)
osm_outside = []

for fac in osm_facilities_raw:
    lon = float(fac["lon"])
    lat = float(fac["lat"])
    matched_code = None
    for c, g, b in geometries:
        if _point_in_geometry(lon, lat, g, b):
            matched_code = c
            break
    fac["commune_code"] = matched_code
    if matched_code:
        osm_by_commune[matched_code].append(fac)
    else:
        osm_outside.append(fac)

print(
    f"       OSM assignés dans TTA: {sum(len(v) for v in osm_by_commune.values())} | Hors limites territoriales: {len(osm_outside)}"
)

# 5. Rapprochement et audit des 24 Hôpitaux Publics avec OSM
print("[4/6] Audit et rapprochement des 24 hôpitaux publics avec OSM...")

# Attribution déterministe des codes communaux et identifiants uniques aux 323 structures ministérielles
for idx, r in enumerate(pub_facilities_raw):
    raw_name = r.get("commune_name_matched", "").strip().lower()
    if not raw_name:
        raw_name = r.get("commune_name_official", "").strip().lower()
    norm_name = normalize_commune_name(raw_name)
    c = communes_by_name[norm_name.lower()]
    r["commune_code"] = c["commune_code"]
    r["province"] = c["province"]
    r["milieu"] = c["milieu"]
    # Identifiant unique pérenne
    r["facility_id"] = f"PUB-TTA-{c['province_code']}-{idx + 1:03d}"

# Dictionnaire corrigé et vérifié des correspondances hospitalières
# Chaque association est vérifiée dans les données sources OSM
VERIFIED_MATCHES = {
    # Al Hoceima (5 hôpitaux)
    "PUB-TTA-MA-01-051-008": (
        "8377190516",
        "MATCH_MANUAL_VERIFIED",
        "Exact name & location match",
        "Centre Hospitalier Provincial Mohammed VI à Ait Youssef Ou Ali",
    ),
    "PUB-TTA-MA-01-051-016": (
        "12846726229",
        "MATCH_MANUAL_VERIFIED",
        "Exact name & location match",
        "C. d'oncologie d'Al Hoceima",
    ),
    "PUB-TTA-MA-01-051-019": (
        "789174103",
        "MATCH_MANUAL_VERIFIED",
        "Exact name & location match",
        "Hôpital Mohamed V Al Hoceima",
    ),
    "PUB-TTA-MA-01-051-043": (
        "10920276384",
        "MATCH_CANDIDATE",
        "Candidate name similarity",
        "Health Center Imzouren - Nécessite confirmation terrain HPr vs CSU",
    ),
    "PUB-TTA-MA-01-051-065": (
        "789267614",
        "MATCH_MANUAL_VERIFIED",
        "Bilingual toponymic verification",
        "مستشفى حمان الفطواكي ايت عزة - Nom officiel de l'Hôpital de Proximité de Targuist",
    ),
    # Chefchaouen (1 hôpital)
    "PUB-TTA-MA-01-151-100": (
        "305583432",
        "MATCH_MANUAL_VERIFIED",
        "Exact name match",
        "Hôpital Mohamed V Chefchaouen (nœud principal, doublons 297605167/3195514325 tracés)",
    ),
    # Larache (2 hôpitaux)
    "PUB-TTA-MA-01-331-143": (
        "789778445",
        "MATCH_MANUAL_VERIFIED",
        "Exact name match",
        "Hopital Provincial de Ksar El Kébir",
    ),
    "PUB-TTA-MA-01-331-156": (
        "12815056754",
        "MATCH_MANUAL_VERIFIED",
        "Official title match",
        "Hôpital Princesse Lalla Meriem à Larache",
    ),
    # M'diq-Fnideq (2 hôpitaux)
    "PUB-TTA-MA-01-573-178": (
        None,
        "NO_MATCH",
        "Spatial vacancy",
        "Hôpital Hassan II Fnideq - Aucun hôpital OSM recensé sur Fnideq",
    ),
    "PUB-TTA-MA-01-573-182": (
        "293247182",
        "MATCH_MANUAL_VERIFIED",
        "Name & commune match",
        "Hopital Mohamed 6 à M'Diq",
    ),
    # Ouezzane (1 hôpital)
    "PUB-TTA-MA-01-405-206": (
        "12815486724",
        "MATCH_MANUAL_VERIFIED",
        "Official project match",
        "Projet Centre Hospitalier Provincial d'Ouezzane (Abou Kacem Zahraoui)",
    ),
    # Tanger-Assilah (10 hôpitaux)
    "PUB-TTA-MA-01-511-230": (
        "12815618481",
        "MATCH_MANUAL_VERIFIED",
        "Single municipal hospital match",
        "Hôpital d'Assilah (nœud OSM 12815618481)",
    ),
    "PUB-TTA-MA-01-511-235": (
        "871505068",
        "MATCH_MANUAL_VERIFIED",
        "Campus level match",
        "Pôle hospitalier CHU Mohammed VI Tanger (spécialités, way OSM 871505068)",
    ),
    "PUB-TTA-MA-01-511-236": (
        None,
        "MATCH_CANDIDATE",
        "Campus level cluster",
        "Hôpital mère-enfant Mohammed VI Tanger - inclus dans l'emprise CHU",
    ),
    "PUB-TTA-MA-01-511-237": (
        None,
        "MATCH_CANDIDATE",
        "Campus level cluster",
        "Hôpital psychiatrique Mohammed VI Tanger - inclus dans l'emprise CHU",
    ),
    "PUB-TTA-MA-01-511-246": (
        "358688501",
        "MATCH_MANUAL_VERIFIED",
        "Exact name match",
        "Hôpital Al Kortobi Tanger",
    ),
    "PUB-TTA-MA-01-511-248": (
        "13770363904",
        "MATCH_CANDIDATE",
        "Ambiguous toponymic match",
        "HPsyR Arrazi Mghogha - مصحة الرازي nécessite confirmation de statut public vs privé",
    ),
    "PUB-TTA-MA-01-511-257": (
        "587335799",
        "MATCH_CANDIDATE",
        "Name variation match",
        "Centre d'oncologie de Tanger (way 587335799 Centre Ahmad Bin Zayed Al Nahyan)",
    ),
    "PUB-TTA-MA-01-511-260": (
        "564951388",
        "MATCH_CANDIDATE",
        "Historical toponymic match",
        "Hôpital Duc de Tovar / Hôpital Espagnol - Nécessite confirmation cadastrale",
    ),
    "PUB-TTA-MA-01-511-270": (
        "122398955",
        "MATCH_MANUAL_VERIFIED",
        "Exact name match",
        "Hôpital Mohammed V Tanger",
    ),
    "PUB-TTA-MA-01-511-271": (
        "475665966",
        "MATCH_MANUAL_VERIFIED",
        "Exact name & arrondissement match",
        "Hôpital Mohammed VI Bni Makada",
    ),
    # Tétouan (3 hôpitaux)
    "PUB-TTA-MA-01-571-290": (
        "1242229574",
        "MATCH_MANUAL_VERIFIED",
        "Exact name match",
        "Hospital Ben Karrich",
    ),
    "PUB-TTA-MA-01-571-306": (
        None,
        "NO_MATCH",
        "Absence in OSM",
        "Hôpital psychiatrique Errazi Tétouan - Non répertorié dans OSM",
    ),
    "PUB-TTA-MA-01-571-307": (
        "484204214",
        "MATCH_MANUAL_VERIFIED",
        "Universal local toponymy",
        "Hôpital Sanyat Rmel (Hôpital Civil Provincial de Tétouan)",
    ),
}

osm_by_id = {o["osm_id"]: o for o in osm_facilities_raw}

audit_rows = []
matched_osm_ids = set()

hospitals_ministry = [r for r in pub_facilities_raw if r["facility_group"] == "Hôpitaux"]
for h in hospitals_ministry:
    fid = h["facility_id"]
    match_info = VERIFIED_MATCHES.get(fid, (None, "NO_MATCH", "No candidate", "Non traité"))
    osm_id, status, method, comment = match_info

    osm_name = ""
    sim_score = 0.0
    if osm_id and osm_id in osm_by_id:
        osm_entry = osm_by_id[osm_id]
        osm_name = osm_entry.get("name", "")
        sim_score = round(
            SequenceMatcher(None, h["facility_name"].lower(), osm_name.lower()).ratio(), 2
        )
        if status == "MATCH_MANUAL_VERIFIED":
            matched_osm_ids.add(osm_id)
            # Transmission des coordonnées GPS exactes à la structure publique ministérielle
            h["has_gps"] = True
            h["lat"] = osm_entry["lat"]
            h["lon"] = osm_entry["lon"]
            h["geocode_precision"] = "EXACT_OSM_RECONCILED"
            h["source_ids"] = f"MINISTRY_2025;OSM:{osm_id}"
        else:
            h["has_gps"] = False
            h["lat"] = ""
            h["lon"] = ""
            h["geocode_precision"] = "UNLOCATED"
            h["source_ids"] = "MINISTRY_2025"
    else:
        h["has_gps"] = False
        h["lat"] = ""
        h["lon"] = ""
        h["geocode_precision"] = "UNLOCATED"
        h["source_ids"] = "MINISTRY_2025"

    audit_rows.append(
        {
            "ministry_facility_id": fid,
            "ministry_facility_name": h["facility_name"],
            "commune_code": h["commune_code"],
            "osm_id": osm_id if osm_id else "",
            "osm_name": osm_name,
            "similarity_score": sim_score if osm_id else "",
            "matching_status": status,
            "validation_method": method,
            "validation_comment": comment,
        }
    )

print(f"       Hôpitaux vérifiés avec GPS : {len(matched_osm_ids)} sur {len(hospitals_ministry)}")
print(f"       Écriture du journal d'audit : {OUT_MATCHING_AUDIT}...")
with open(OUT_MATCHING_AUDIT, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "ministry_facility_id",
            "ministry_facility_name",
            "commune_code",
            "osm_id",
            "osm_name",
            "similarity_score",
            "matching_status",
            "validation_method",
            "validation_comment",
        ],
    )
    writer.writeheader()
    writer.writerows(audit_rows)

# 6. Construction du Référentiel Communal Consolidé (146 communes)
print("[5/6] Construction de communes_health_profile_TTA.csv...")
f2_by_code = {}
for r in pub_communes_raw:
    norm_name = normalize_commune_name(r["commune_name"])
    c = communes_by_name[norm_name.lower()]
    f2_by_code[c["commune_code"]] = r

# Agréger le Fichier 3 pour pub_csr2_maternite
csr2_by_code = defaultdict(int)
for r in pub_facilities_raw:
    if r["category_code"] == "CSR-2":
        csr2_by_code[r["commune_code"]] += 1

communes_profile_rows = []
for c in communes_raw:
    code = c["commune_code"]
    pop = int(c["population_2024"]) if c.get("population_2024") else 0
    f2 = f2_by_code[code]

    pub_csu = int(f2["CSU"])
    pub_csr = int(f2["CSR"])
    pub_csr2 = csr2_by_code[code]
    pub_dr = int(f2["DR"])
    pub_primary = pub_csu + pub_csr + pub_dr
    pub_hospitals = int(f2["Hospitals"])
    pub_spec = int(f2["Specialized"])
    pub_total = int(f2["Total_Public_Official"])

    # Indicateurs OSM dans le polygone communal
    osm_list = osm_by_commune[code]
    osm_pharmacies = sum(1 for o in osm_list if o["facility_type"] == "pharmacy")
    osm_clinics = sum(1 for o in osm_list if o["facility_type"] == "clinic")
    osm_doctors = sum(1 for o in osm_list if o["facility_type"] == "doctors")
    osm_total_points = len(osm_list)

    # Ratios sanitaires
    primary_care_per_10k = round((pub_primary / pop) * 10000, 4) if pop > 0 else ""
    pharmacy_per_10k = round((osm_pharmacies / pop) * 10000, 4) if pop > 0 else ""
    is_public_healthcare_absent = pub_total == 0

    row = {
        "commune_code": code,
        "name_fr": c["name_fr"],
        "province": c["province"],
        "milieu": c["milieu"],
        "population_2024": pop,
        "part_rurale_pct": c.get("part_rurale_pct", ""),
        "pub_csu": pub_csu,
        "pub_csr": pub_csr,
        "pub_csr2_maternite": pub_csr2,
        "pub_dr": pub_dr,
        "pub_primary_total": pub_primary,
        "pub_hospitals": pub_hospitals,
        "pub_specialized": pub_spec,
        "pub_total_official": pub_total,
        "osm_pharmacies_mapped": osm_pharmacies,
        "osm_clinics_candidates": osm_clinics,
        "osm_doctors_mapped": osm_doctors,
        "osm_health_points_total": osm_total_points,
        "primary_care_per_10k": primary_care_per_10k,
        "pharmacy_per_10k": pharmacy_per_10k,
        "is_public_healthcare_absent": is_public_healthcare_absent,
    }
    communes_profile_rows.append(row)

with open(OUT_COMMUNES_PROFILE, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "commune_code",
            "name_fr",
            "province",
            "milieu",
            "population_2024",
            "part_rurale_pct",
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
            "primary_care_per_10k",
            "pharmacy_per_10k",
            "is_public_healthcare_absent",
        ],
    )
    writer.writeheader()
    writer.writerows(communes_profile_rows)

print(
    f"       Écriture réussie : {len(communes_profile_rows)} communes dans {OUT_COMMUNES_PROFILE}"
)

# 7. Construction du Référentiel Établissements Master (1 215 structures)
print("[6/6] Construction de health_facilities_master_TTA.csv...")
master_rows = []

# A. 323 Établissements publics ministériels
for r in pub_facilities_raw:
    if "source_ids" not in r:
        r["has_gps"] = False
        r["lat"] = ""
        r["lon"] = ""
        r["geocode_precision"] = "UNLOCATED"
        r["source_ids"] = "MINISTRY_2025"

    row = {
        "facility_id": r["facility_id"],
        "name": r["facility_name"],
        "commune_code": r["commune_code"],
        "commune_name_official": r["commune_name_official"],
        "province": r["province"],
        "category_code": r["category_code"],
        "facility_category_label": r["facility_category_label"],
        "facility_group": r["facility_group"],
        "milieu": r["milieu"],
        "sector": "Public",
        "facility_tier": "PUBLIC_CORE",
        "validation_status": "OFFICIAL_MINISTRY",
        "source_primary": "Ministere_Sante_2025",
        "source_ids": r["source_ids"],
        "source_year": 2025,
        "has_gps": r["has_gps"],
        "lat": r["lat"],
        "lon": r["lon"],
        "geocode_precision": r["geocode_precision"],
    }
    master_rows.append(row)

# B. Établissements OSM (avec qualification rigoureuse et neutralisation des doublons)
for fac in osm_facilities_raw:
    osm_id = fac["osm_id"]
    ftype = fac["facility_type"]
    fname = fac.get("name", "").strip()
    c_code = fac.get("commune_code")
    lat = fac["lat"]
    lon = fac["lon"]

    c_name = communes_by_code[c_code]["name_fr"] if c_code and c_code in communes_by_code else ""
    c_prov = communes_by_code[c_code]["province"] if c_code and c_code in communes_by_code else ""
    c_mil = communes_by_code[c_code]["milieu"] if c_code and c_code in communes_by_code else ""

    fid = f"OSM-TTA-{fac['osm_type'].upper()[:1]}-{osm_id}"

    # 1. Hôpital public réconcilié (neutralisation du doublon)
    if osm_id in matched_osm_ids:
        tier = "PUBLIC_CORE"
        v_status = "RECONCILED_PUBLIC_DUPLICATE"
        sector = "Public"
        cat_code = "HOSP_RECONCILED"
        cat_label = "Hôpital public réconcilié (doublon OSM neutralisé)"
        grp = "Hôpitaux"
        precision = "EXACT_OSM_RECONCILED"
    # 2. Hors limites territoriales régionales (Ceuta, Driouch, Kénitra)
    elif not c_code:
        tier = "UNVERIFIED"
        v_status = "OUTSIDE_REGION_TERRITORY"
        sector = "Inconnu"
        cat_code = ftype.upper()
        cat_label = f"Entité hors région TTA ({ftype})"
        grp = "Hors Périmètre"
        precision = "EXACT_GPS_OUTSIDE"
    # 3. Pharmacies (731 dans TTA : 722 nommées + 9 anonymes)
    elif ftype == "pharmacy":
        if fname:
            tier = "PRIVATE_VALID"
            v_status = "OSM_MAPPED_ACTIVE"
            sector = "Privé"
            cat_code = "PHARMACY"
            cat_label = "Officine de pharmacie"
            grp = "Pharmacies"
            precision = "EXACT_GPS"
        else:
            tier = "UNVERIFIED"
            v_status = "ANONYMOUS_UNVERIFIED"
            sector = "Inconnu"
            cat_code = "PHARMACY"
            cat_label = "Officine de pharmacie anonyme (sans nom)"
            grp = "Pharmacies"
            precision = "EXACT_GPS"
    # 4. Cliniques et cabinets médicaux
    elif ftype == "clinic":
        tier = "PRIVATE_VALID" if fname else "UNVERIFIED"
        v_status = "OSM_MAPPED_ACTIVE" if fname else "ANONYMOUS_UNVERIFIED"
        sector = "Privé" if fname else "Inconnu"
        cat_code = "CLINIC"
        cat_label = "Clinique privée / Cabinet de soins" if fname else "Clinique anonyme"
        grp = "Cliniques et Cabinets"
        precision = "EXACT_GPS"
    elif ftype == "doctors":
        tier = "PRIVATE_VALID" if fname else "UNVERIFIED"
        v_status = "OSM_MAPPED_ACTIVE" if fname else "ANONYMOUS_UNVERIFIED"
        sector = "Privé" if fname else "Inconnu"
        cat_code = "DOCTOR"
        cat_label = "Cabinet médical libéral" if fname else "Cabinet médical anonyme"
        grp = "Cliniques et Cabinets"
        precision = "EXACT_GPS"
    elif ftype == "laboratory":
        tier = "PRIVATE_VALID" if fname else "UNVERIFIED"
        v_status = "OSM_MAPPED_ACTIVE" if fname else "ANONYMOUS_UNVERIFIED"
        sector = "Privé" if fname else "Inconnu"
        cat_code = "LABORATORY"
        cat_label = "Laboratoire d'analyses médicales"
        grp = "Centres Spécialisés et Laboratoires"
        precision = "EXACT_GPS"
    # 5. Hôpitaux OSM non réconciliés
    elif ftype == "hospital":
        if not fname:
            tier = "UNVERIFIED"
            v_status = "ANONYMOUS_UNVERIFIED"
            sector = "Inconnu"
            cat_code = "HOSP_ANON"
            cat_label = "Hôpital anonyme (sans nom)"
            grp = "Inconnu"
            precision = "EXACT_GPS"
        else:
            tier = (
                "PRIVATE_VALID"
                if (
                    "privé" in fname.lower()
                    or "clinique" in fname.lower()
                    or "akdital" in fname.lower()
                )
                else "UNVERIFIED"
            )
            v_status = "OSM_HOSPITAL_UNRECONCILED"
            sector = "Privé" if tier == "PRIVATE_VALID" else "Indéterminé"
            cat_code = "HOSP_OSM_OTHER"
            cat_label = "Établissement déclaré hôpital dans OSM (privé ou non homologué)"
            grp = "Hôpitaux et Cliniques OSM"
            precision = "EXACT_GPS"
    # 6. Autres entités OSM
    else:
        tier = "UNVERIFIED"
        v_status = "HEALTHCARE_OTHER" if fname else "ANONYMOUS_UNVERIFIED"
        sector = "Indéterminé"
        cat_code = ftype.upper()
        cat_label = f"Structure sanitaire OSM non standard ({ftype})"
        grp = "Autres"
        precision = "EXACT_GPS"

    row = {
        "facility_id": fid,
        "name": fname if fname else "Non renseigné",
        "commune_code": c_code if c_code else "",
        "commune_name_official": c_name,
        "province": c_prov,
        "category_code": cat_code,
        "facility_category_label": cat_label,
        "facility_group": grp,
        "milieu": c_mil,
        "sector": sector,
        "facility_tier": tier,
        "validation_status": v_status,
        "source_primary": "OpenStreetMap",
        "source_ids": f"OSM:{osm_id}",
        "source_year": 2024,
        "has_gps": True,
        "lat": lat,
        "lon": lon,
        "geocode_precision": precision,
    }
    master_rows.append(row)

master_fields = [
    "facility_id",
    "name",
    "commune_code",
    "commune_name_official",
    "province",
    "category_code",
    "facility_category_label",
    "facility_group",
    "milieu",
    "sector",
    "facility_tier",
    "validation_status",
    "source_primary",
    "source_ids",
    "source_year",
    "has_gps",
    "lat",
    "lon",
    "geocode_precision",
]

with open(OUT_FACILITIES_MASTER, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=master_fields)
    writer.writeheader()
    writer.writerows(master_rows)

print(f"       Écriture réussie : {len(master_rows)} structures dans {OUT_FACILITIES_MASTER}")
print("[SUCCÈS] Toutes les données consolidées ont été générées avec succès.")
